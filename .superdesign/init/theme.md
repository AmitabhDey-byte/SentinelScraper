# Theme

## Token summary

| Token | Value | Use |
| --- | --- | --- |
| `--night` | `#090807` | global dark surface |
| `--forest` | `#17120d` | opaque header |
| `--forest-light` | `#2a2015` | dark elevated control |
| `--ink` | `#20160f` | dark text on paper cards |
| `--paper` | `#e9dfcc` | principal parchment |
| `--paper-light` | `#f4ecdc` | high-contrast text/surface |
| `--paper-dark` | `#c6b89e` | secondary text |
| `--moss` | `#8d7a5b` | subdued status text |
| `--brass` | `#d2a15a` | primary gold accent |
| `--brass-dark` | `#8d622d` | line/border accent |
| `--rust` | `#a95743` | destructive/incident accent |

Typography: Cormorant Garamond (headlines, serif navigation, prices), DM Sans (body), DM Mono (labels, timestamps, controls). Content width is `min(1400px, 90vw)` with mobile `88vw`. No visual gradients. Corners are square or nearly square; borders are brass/ink rules. Motion uses Framer Motion: soft fade/translate page entrances and subtle row/card displacement.

## Source token block

```css
:root { --night: #090807; --forest: #17120d; --forest-light: #2a2015; --ink: #20160f; --paper: #e9dfcc; --paper-light: #f4ecdc; --paper-dark: #c6b89e; --moss: #8d7a5b; --brass: #d2a15a; --brass-dark: #8d622d; --rust: #a95743; --line: rgba(233, 223, 204, 0.25); font-family: "DM Sans", sans-serif; }
```

Raw source: `frontend/src/styles.css` (1,653 lines). It defines the responsive breakpoints at `1120px`, `760px`, and lower narrow-screen refinements.
