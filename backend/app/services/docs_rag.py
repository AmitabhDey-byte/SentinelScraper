"""Sitemap-to-RAG pipeline using Bright Data content and Gemini embeddings."""

from dataclasses import asdict, dataclass
import hashlib
import html
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree

from pydantic import BaseModel, Field

from app.config import settings
from app.orchestration.brightdata import BrightDataCLI


class Citation(BaseModel):
    url: str
    title: str


class GroundedAnswer(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[Citation]


@dataclass
class RagChunk:
    url: str
    title: str
    text: str
    vector: list[float]


def _stable_vector(text: str, dimensions: int = 128) -> list[float]:
    """Small offline fallback so indexing remains inspectable without Gemini."""

    vector = [0.0] * dimensions
    for token in re.findall(r"[a-z0-9]{2,}", text.casefold()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0 if digest[4] % 2 else -1.0
    norm = sum(value * value for value in vector) ** 0.5 or 1.0
    return [value / norm for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    return sum(left[index] * right[index] for index in range(size))


def _strip_markup(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def sitemap_locations(xml_text: str) -> list[str]:
    """Extract locations from sitemap XML, with a regex fallback for wrapped output."""

    try:
        root = ElementTree.fromstring(xml_text)
        locations = [element.text.strip() for element in root.iter() if element.tag.endswith("loc") and element.text]
        if locations:
            return locations
    except ElementTree.ParseError:
        pass
    return [html.unescape(value) for value in re.findall(r"<loc[^>]*>\s*(.*?)\s*</loc>", xml_text, flags=re.I | re.S)]


def chunks(text: str, *, size: int = 1200, overlap: int = 150) -> list[str]:
    words = text.split()
    result: list[str] = []
    cursor = 0
    while cursor < len(words):
        current: list[str] = []
        length = 0
        while cursor + len(current) < len(words) and length + len(words[cursor + len(current)]) + 1 <= size:
            word = words[cursor + len(current)]
            current.append(word)
            length += len(word) + 1
        if not current:
            current = [words[cursor][:size]]
        result.append(" ".join(current))
        consumed = len(current)
        overlap_words = max(0, min(consumed - 1, overlap // 6))
        cursor += max(1, consumed - overlap_words)
    return result


class GeminiEmbedder:
    model = "gemini-embedding-001"

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not settings.gemini_api_key:
            return [_stable_vector(text) for text in texts]
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.gemini_api_key)
            result = client.models.embed_content(
                model=self.model,
                contents=texts,
                config=types.EmbedContentConfig(output_dimensionality=768),
            )
            return [list(embedding.values) for embedding in result.embeddings]
        except Exception:
            return [_stable_vector(text) for text in texts]


class SitemapRag:
    def __init__(self, cli: BrightDataCLI | None = None, embedder: GeminiEmbedder | None = None) -> None:
        self.cli = cli or BrightDataCLI()
        self.embedder = embedder or GeminiEmbedder()

    def ingest(self, sitemap_url: str, output_path: Path, *, max_pages: int = 20) -> dict[str, Any]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        scratch = output_path.parent / ".rag-scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        sitemap_path = scratch / "sitemap.xml"
        self.cli.scrape(sitemap_url, sitemap_path, format="html")
        locations = sitemap_locations(sitemap_path.read_text(encoding="utf-8"))
        page_urls = [url for url in locations if urlparse(url).scheme in {"http", "https"}][:max_pages]

        documents: list[dict[str, str]] = []
        for index, url in enumerate(page_urls):
            page_path = scratch / f"page-{index}.md"
            self.cli.scrape(url, page_path, format="markdown")
            text = _strip_markup(page_path.read_text(encoding="utf-8"))
            if text:
                title = text[:100].split("\n", 1)[0].strip("# ") or url
                documents.append({"url": url, "title": title, "text": text})

        raw_chunks = [
            {"url": document["url"], "title": document["title"], "text": chunk}
            for document in documents
            for chunk in chunks(document["text"])
        ]
        vectors = self.embedder.embed([item["text"] for item in raw_chunks])
        payload = {
            "sitemap_url": sitemap_url,
            "chunks": [
                asdict(RagChunk(**item, vector=vectors[index]))
                for index, item in enumerate(raw_chunks)
            ],
        }
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"sitemap_url": sitemap_url, "pages": len(documents), "chunks": len(raw_chunks), "output": str(output_path)}

    def retrieve(self, index_path: Path, question: str, *, top_k: int = 5) -> list[RagChunk]:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        query_vector = self.embedder.embed([question])[0]
        ranked = sorted(
            (RagChunk(**item) for item in payload.get("chunks", [])),
            key=lambda chunk: _cosine(query_vector, chunk.vector),
            reverse=True,
        )
        return ranked[:top_k]

    def answer(self, index_path: Path, question: str, *, top_k: int = 5) -> GroundedAnswer:
        retrieved = self.retrieve(index_path, question, top_k=top_k)
        citations = [Citation(url=chunk.url, title=chunk.title) for chunk in retrieved]
        if not retrieved:
            return GroundedAnswer(answer="No indexed documentation matched that question.", citations=[])

        context = "\n\n".join(f"SOURCE: {chunk.url}\n{chunk.text}" for chunk in retrieved)
        if not settings.gemini_api_key:
            return GroundedAnswer(
                answer=f"The closest indexed passages are from {retrieved[0].title}. Review the cited source for the exact answer.",
                citations=citations,
            )
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.gemini_api_key)
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=(
                    "Answer only from the supplied documentation context. Return concise JSON with an answer "
                    "and citations selected from the supplied URLs.\n\nQUESTION: " + question + "\n\n" + context
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GroundedAnswer,
                ),
            )
            payload = getattr(response, "parsed", None) or json.loads(response.text)
            answer = GroundedAnswer.model_validate(payload)
            allowed = {citation.url for citation in citations}
            if not all(citation.url in allowed for citation in answer.citations):
                raise ValueError("Gemini returned a citation outside the retrieved context")
            return answer
        except Exception:
            return GroundedAnswer(
                answer=f"The closest indexed passages are from {retrieved[0].title}. Review the cited source for the exact answer.",
                citations=citations,
            )
