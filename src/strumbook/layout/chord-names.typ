// Chord names as outlined glyphs, one SVG page per name, so they never reach the
// PDF's text layer. Each page runs exactly from cap height to baseline.
#let names = json(bytes(sys.inputs.names))
#let style = sys.inputs.style // "inline" (in the lyrics) or "label" (on diagrams)
#set page(width: auto, height: auto, margin: 0pt, fill: none)
#set text(
  font: "Atkinson Hyperlegible",
  weight: "bold",
  size: if style == "inline" { 9.5pt } else { 9pt },
  fill: if style == "inline" { rgb("#b3261e") } else { rgb("#202124") },
  top-edge: "cap-height",
  bottom-edge: "baseline",
)
#for (i, name) in names.enumerate() {
  if i > 0 { pagebreak() }
  name
}
