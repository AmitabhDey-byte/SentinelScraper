import { motion, useReducedMotion } from "framer-motion";
import { useState, type ReactNode } from "react";

/** A compact, accessible React Bits-inspired pixel reveal for one key insight. */
export function PixelSwap({
  firstContent,
  secondContent,
}: {
  firstContent: ReactNode;
  secondContent: ReactNode;
}) {
  const [revealed, setRevealed] = useState(false);
  const reducedMotion = useReducedMotion();
  return (
    <button
      className="pixel-swap"
      type="button"
      aria-pressed={revealed}
      onClick={() => setRevealed((value) => !value)}
    >
      <span className="pixel-swap-label">{revealed ? "Hide intelligence" : "Reveal intelligence"}</span>
      <motion.span
        className="pixel-swap-content"
        initial={false}
        animate={{ opacity: 1 }}
        transition={{ duration: reducedMotion ? 0 : 0.22 }}
      >
        {revealed ? secondContent : firstContent}
      </motion.span>
      {!reducedMotion && (
        <motion.span
          aria-hidden="true"
          className="pixel-swap-dust"
          initial={false}
          animate={{ opacity: revealed ? [0.8, 0, 0.5] : [0.5, 0, 0.8], scale: [1, 1.05, 1] }}
          transition={{ duration: 0.42 }}
        />
      )}
    </button>
  );
}
