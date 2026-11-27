// StrumBook's FTR layout. A song library: title page, index, songs with chord diagrams,
// Reference (chord shapes, notes in each chord), credits. A set list: title page,
// running order, then each set's break page and songs; the index, Reference and
// credits are optional.
// All content arrives as JSON in sys.inputs.data, from strumbook/render.py.
// In "measure" mode it lays out the index and each song with and without diagrams,
// and reports their page spans as <pages> metadata for render.py to read back.
#let data = json(bytes(sys.inputs.data))
#let measuring = sys.inputs.at("mode", default: "book") == "measure"

#let red = rgb("#b3261e")
#let ink = rgb("#202124")
#let muted = rgb("#6b7280")
#let faint = rgb("#c9ccd1")
#let rule = rgb("#e3e5e8")

#let body-size = 13pt
#let page-w = 210mm
#let side = 16mm
#let top-m = 30mm
#let bottom-m = 26mm
#let strip-h = 11mm

#set document(title: data.title)
#set page(paper: "a4")
#let float-mid = data.mid_word == "above"
// Atkinson Hyperlegible has no sharp or flat signs (♯ ♭), so they come from Libertinus
// Serif, which Typst bundles.
#set text(
  font: ("Atkinson Hyperlegible", "Libertinus Serif"), size: body-size, fill: ink, lang: "en",
)
#set par(leading: 0.65em, spacing: if float-mid { 1.15em } else { 0.65em })
// Headings exist for bookmarks and link targets; titles are drawn by hand.
#show heading: none

// The small red capitals above each section's big heading.
#let kicker(t) = text(9pt, weight: "bold", fill: red, tracking: 0.12em, t)

// Chord names are outlined SVGs, so they never enter the text layer. Python
// supplies each one's size, which saves Typst measuring them. A shared diagram's
// label ("Am · Am/C · Am/E") shrinks to fit the diagram's width.
#let diagram-w = 15mm
#let images(style, max-w) = data.chords.at(style).pairs().map(((name, f)) => (
  name,
  image(bytes(f.svg), format: "svg", width: calc.min(f.w * 1pt, max-w)),
)).to-dict()
#let inline-images = images("inline", page-w)
#let label-images = images("label", diagram-w)
// Inline SVGs run from cap height to baseline at 9.5pt, so their height gives the
// font's cap-height ratio; the lyric's capitals are that ratio of the body size.
#let lyric-cap = if data.chords.inline.len() > 0 {
  body-size * data.chords.inline.values().first().h / 9.5
} else { 0pt }

// ---------- song text ----------

// Chord tops line up with the lyric's capitals. A chord inside a word
// ("a[D]wakes") sits inline like the rest, which splits the word for search, or
// with --mid-word-chords above floats over the join, so the word stays whole.
#let inline-chord(name, mid) = {
  let f = data.chords.inline.at(name)
  let img = inline-images.at(name)
  if mid and float-mid {
    box(width: 0pt, place(bottom + center, dy: -lyric-cap - 1.5pt, img))
  } else {
    box(baseline: -(lyric-cap - f.h * 1pt), img)
    h(0.18em)
  }
}

#let lyric-line(segments) = par(hanging-indent: 1.2em, {
  for s in segments {
    if s.chord != "" { inline-chord(s.chord, s.mid) }
    s.text
  }
})

#let block-gap = if float-mid { 2em } else { 1.2em }
// A verse or chorus stays on one page, unless it's too long to fit on one.
#let max-unbroken-lines = 16
#let verse(b) = {
  let body = b.lines.map(lyric-line).join()
  let breakable = b.lines.len() > max-unbroken-lines
  block(breakable: breakable, above: block-gap, below: block-gap, if b.chorus {
    block(stroke: (left: 2pt + rule), inset: (left: 10pt, y: 2pt), {
      block(below: 0.5em, text(10pt, style: "italic", fill: muted)[Chorus])
      body
    })
  } else { body })
}

// ---------- chord diagrams ----------

#let diagram(frets) = {
  let sx = 3.6mm
  let fy = 3.6mm
  let rows = 5
  let r = 1.3mm
  box(width: 3 * sx, height: rows * fy, {
    for i in range(4) {
      place(line(start: (i * sx, 0pt), end: (i * sx, rows * fy), stroke: 0.6pt + muted))
    }
    for j in range(1, rows + 1) {
      place(line(start: (0pt, j * fy), end: (3 * sx, j * fy), stroke: 0.6pt + muted))
    }
    place(line(start: (0pt, 0pt), end: (3 * sx, 0pt), stroke: 2.2pt + ink))
    for (i, f) in frets.enumerate() {
      if f > 0 {
        place(dx: i * sx - r, dy: (f - 0.5) * fy - r, circle(radius: r, fill: ink))
      }
    }
  })
}

#let chord-box(d) = box(width: diagram-w, align(center, stack(
  spacing: 2mm,
  label-images.at(d.label),
  diagram(d.frets),
)))

#let diagram-column(song, cols) = stack(
  spacing: 3mm,
  align(center, text(7.5pt, fill: muted, tracking: 0.12em, data.tuning.letters)),
  grid(columns: cols, column-gutter: 2mm, row-gutter: 4.5mm, ..song.diagrams.map(chord-box)),
)

// ---------- link strip ----------

#let index-icon = stack(spacing: 1.1mm, ..range(3).map(_ => line(length: 4.2mm, stroke: 1.2pt + ink)))
#let ref-icon = grid(columns: (1.3mm,) * 3, rows: (1.3mm,) * 3, stroke: 0.8pt + ink)

// Cells come from render.py: index (or running order), letters or set names, and
// reference. Every cell is the same size. Empty letters are grey and jump onwards.
#let strip(current) = {
  let w = (page-w - 2 * side) / data.strip.len()
  let cell(body, active) = box(width: w, height: strip-h, {
    // A long set name wraps; past two lines it's cut off, not spilt out of the strip.
    let inner = box(width: w - 2mm, align(center, body))
    place(center + horizon, context {
      let room = strip-h - 3mm
      if measure(inner).height <= room { inner } else {
        box(height: room, clip: true, align(top, inner))
      }
    })
    if active { place(bottom + center, rect(width: 75%, height: 2pt, fill: red)) }
  })
  grid(
    columns: (w,) * data.strip.len(),
    ..data.strip.map(c => {
      let active = current == c.key
      let icon = c.at("icon", default: none)
      let body = if icon == "index" { index-icon } else if icon == "ref" { ref-icon } else {
        let colour = if active { ink } else if c.at("dim", default: false) { faint } else { muted }
        let size = if c.text.len() == 1 { 10.5pt } else { 9pt }
        text(size, weight: if active { "bold" } else { "regular" }, fill: colour, c.text)
      }
      link(label(c.target), cell(body, active))
    }),
  )
}

// The page number, top right, links back to the song's index or running order entry
// (`back`).
#let page-furniture(current, back: none) = {
  let number = text(15pt, weight: "bold", fill: red, context counter(page).display())
  if back != none and not measuring { number = link(back, number) }
  place(top + right, dx: -side, dy: 13mm, number)
  if data.strip.len() > 0 and not measuring {
    place(bottom + left, dx: side, dy: -5mm, strip(current))
  }
}

// Plain-text notes: paragraphs of lines.
#let notes-block(notes) = if notes.len() > 0 {
  v(10mm)
  set par(spacing: 1em)
  for lines in notes { par(text(12pt, lines.join(linebreak()))) }
}

// Reports a page span to render.py in measure mode.
#let report(id, variant, start) = if measuring {
  context [#metadata((
    id: id,
    variant: variant,
    first: locate(start).page(),
    last: here().page(),
  )) <pages>]
}

// ---------- song page ----------

#let song-page(song, show-diagrams, variant) = {
  let key = song.id + variant
  let start = label("song-" + key)
  let end = label("end-" + key)
  let back = if data.type == "set-list" { <running-order> } else if data.index_page {
    label("index-" + song.id)
  }
  let cols = song.diagram_columns
  let dw = if show-diagrams and cols > 0 { cols * diagram-w + (cols - 1) * 2mm + 7mm } else { 0mm }
  page(
    margin: (left: side, right: side + dw, top: top-m, bottom: bottom-m),
    header: context {
      let first = here().page() == locate(start).page()
      let title = text(24pt, weight: "bold", song.title)
      block(width: page-w - 2 * side - 16mm, {
        if measuring or back == none { title } else { link(back, title) }
        if not first { text(14pt, fill: muted)[ (continued)] }
      })
    },
    footer: context {
      if here().page() < locate(end).page() {
        text(11pt, weight: "bold", fill: red)[Continues on page #(here().page() + 1) →]
      }
    },
    foreground: page-furniture(song.key, back: back),
    // Drawn as the background, so the diagrams repeat on continuation pages.
    background: if dw > 0mm {
      place(top + right, dx: -side, dy: top-m + 1mm, box(
        width: dw - 3mm,
        stroke: (left: 0.5pt + rule),
        inset: (left: 4mm),
        diagram-column(song, cols),
      ))
    },
  )[
    #heading(level: 1, bookmarked: not measuring, song.title) #start
    #text(10pt, fill: muted, song.artist)
    #if song.credit != "" {
      // Links to the song's entry in Credits.
      let credit = text(9pt, fill: muted, song.credit)
      if data.credits and not measuring { credit = link(label("credit-" + song.id), credit) }
      block(above: 0.4em, credit)
    }
    #for b in song.blocks { verse(b) }
    #metadata(none) #end
    #report(song.id, variant, start)
  ]
}

// ---------- index ----------

#let index-number(target) = text(fill: muted, if measuring { "000" } else {
  context counter(page).at(target).first()
})

// The whole row, padding included, is the tap target.
#let index-row(body, number, target, pad: 2.6mm) = {
  let row = block(
    width: 100%,
    inset: (y: pad),
    stroke: (bottom: 0.5pt + rule),
    grid(columns: (1fr, auto), column-gutter: 3mm, body, number),
  )
  if measuring { row } else { link(target, row) }
}

#let group-head(t) = block(above: 5mm, below: 0mm, text(10pt, weight: "bold", fill: red, t))

#let index-page() = page(
  margin: (x: side, top: 16mm, bottom: bottom-m),
  foreground: page-furniture("index"),
)[
  #heading(level: 1, bookmarked: not measuring)[Index] <index>
  #kicker[INDEX] \
  #text(26pt, weight: "bold", data.title) \
  #text(10pt, fill: muted, data.count)
  #v(4mm)
  #columns(if measuring { 1 } else { data.index_columns }, gutter: 8mm, {
    let previous = none
    for song in data.index {
      if song.letter != previous { group-head(song.letter) }
      previous = song.letter
      let target = label("song-" + song.id)
      [#index-row(
        [#song.title #h(1.5mm) #text(10pt, fill: muted, song.artist)],
        index-number(target),
        target,
      ) #label("index-" + song.id)]
    }
    if data.reference_page or data.credits { group-head[Reference] }
    if data.reference_page {
      for chart in data.charts {
        index-row(
          [Chord shapes #h(1.5mm) #text(10pt, fill: muted, chart.letters)],
          index-number(label(chart.label)),
          label(chart.label),
        )
      }
    }
    if data.credits { index-row([Credits], index-number(<credits>), <credits>) }
  })
  #report("index", "", <index>)
]

// ---------- set lists ----------

// Each set's name and running time, then its songs, each row a link to the song.
#let running-order-page() = page(
  margin: (x: side, top: 16mm, bottom: bottom-m),
  foreground: page-furniture("running-order"),
)[
  #heading(level: 1)[Running order] <running-order>
  #kicker[RUNNING ORDER] \
  #text(26pt, weight: "bold", data.title) \
  #text(10pt, fill: muted, data.count)
  #v(2mm)
  #for s in data.sections {
    if s.name != "" {
      block(above: 5mm, below: 1mm, {
        text(12pt, weight: "bold", fill: red, s.name)
        if s.running_time != "" { h(2mm); text(10pt, fill: muted, s.running_time) }
      })
    }
    for song in s.songs {
      let target = label("song-" + song.id)
      index-row(
        [#song.title #h(1.5mm) #text(10pt, fill: muted, song.artist)],
        index-number(target),
        target,
        pad: 1.8mm,
      )
    }
  }
]

// Before a set: its name, running time and notes.
#let break-page(s) = page(
  margin: (x: side, top: 60mm, bottom: bottom-m),
  foreground: page-furniture(s.key, back: <running-order>),
)[
  #heading(level: 1, s.name) #label(s.key)
  #text(40pt, weight: "bold", s.name) \
  #if s.running_time != "" { text(14pt, fill: muted, s.running_time) }
  #notes-block(s.notes)
]

// ---------- reference ----------

// The chord shapes in the book's tuning, then (with reference-notes on) the notes in
// each chord. Each carries the strip with Reference lit; the first is the Reference
// target.
#let reference-page(body) = page(
  margin: (x: side, top: 16mm, bottom: bottom-m),
  foreground: page-furniture("ref"),
  body,
)
#let reference-head(title, sub) = [
  #kicker[REFERENCE] \
  #text(26pt, weight: "bold", title) \
  #text(10pt, fill: muted, sub)
  #v(4mm)
]

// A row per root and a column per type, in one tuning. The cells are diagrams only,
// shrunk to fit all 108 on one page: the row and column name the chord. The first
// chart opens Reference; with several, each bookmark names its tuning.
#let chart-page(chart, first, several) = reference-page[
  #let tuning = [#chart.name (#chart.letters)]
  #if first [#heading(level: 1)[Reference] <reference>]
  #let mark = heading(level: 2, if several [Chord shapes: #tuning] else [Chord shapes])
  #if first { mark } else [#mark #label(chart.label)]
  #reference-head([Chord shapes], tuning)
  #grid(
    columns: (12mm,) + (1fr,) * 9,
    row-gutter: 3mm,
    align: center + horizon,
    [], ..data.chart_headings.map(h => text(9pt, weight: "bold", fill: muted, h)),
    ..chart.rows.map(row => (
      align(left, text(14pt, weight: "bold", fill: muted, row.root)),
      ..row.shapes.map(frets => if frets != none { scale(85%, reflow: true, diagram(frets)) }),
    )).flatten(),
  )
]

// The same roots and types, with each type's formula: fixed data, as checked.
#let notes-page() = reference-page[
  #heading(level: 2)[Notes in each chord]
  #reference-head([Notes in each chord], [The notes that make each chord, counted from its root, 1])
  #let notes = data.chord_notes
  #table(
    columns: (15mm,) + (1fr,) * 9,
    inset: (x: 0.8mm, y: 2.2mm),
    stroke: (bottom: 0.5pt + rule, x: none, top: none),
    align: left + top,
    table.header(
      [], ..notes.types.map(t => text(8.5pt, weight: "bold", t.name)),
      [], ..notes.types.map(t => text(8.5pt, fill: muted, t.formula)),
    ),
    ..notes.rows.map(row => (
      text(9pt, weight: "bold", fill: muted, row.root),
      ..row.cells.map(c => [#text(8.5pt, weight: "bold", c.chord) \ #text(8.5pt, c.notes)]),
    )).flatten(),
  )
]

// ---------- title page ----------

#let title-page() = page(margin: (x: side, top: 60mm, bottom: bottom-m))[
  #heading(level: 1)[Title]
  #kicker(if data.type == "set-list" [SET LIST] else [SONGBOOK]) \
  #text(40pt, weight: "bold", data.title) \
  #if data.subtitle != "" { text(18pt, data.subtitle); linebreak() }
  #text(14pt, fill: muted, data.edition)
  // The tuning, only in a book that has chord shapes in it.
  #if data.chord_diagrams or data.reference_page {
    linebreak()
    text(10pt, fill: muted)[Chord shapes: #data.tuning.name ukulele (#data.tuning.letters)]
  }
  #notes-block(data.notes)
  #place(bottom + left, text(10pt, fill: muted)[Made with StrumBook])
]

// ---------- credits ----------

// The song credits, then "About this book" on a page of its own. The first page
// carries the Credits bookmark; with no credited songs, that's the About page.
#let credits-section() = {
  let credited = data.songs.filter(s => s.credit != "")
  let section-page(body) = page(
    margin: (x: side, top: 16mm, bottom: bottom-m),
    foreground: page-furniture("credits"),
    body,
  )
  let opening = [#heading(level: 1)[Credits] <credits>]
  if credited.len() > 0 {
    section-page[
      #opening
      #kicker[CREDITS] \
      #text(26pt, weight: "bold")[Words and music]
      #v(2mm)
      #columns(2, gutter: 8mm, for song in credited [
        #link(label("song-" + song.id), block(breakable: false, below: 3.5mm, {
          text(11pt, weight: "bold", song.title)
          linebreak()
          text(9pt, fill: muted, song.credit)
        })) #label("credit-" + song.id)
      ])
    ]
  }
  let made = (
    ("StrumBook", "built this book on " + data.built, "https://github.com/sam-tmts/strumbook"),
    ("Typst", "laid out the pages", "https://typst.app"),
    ("Atkinson Hyperlegible", "set the words, in the Braille Institute's typeface made to be easy to read",
      "https://www.brailleinstitute.org/freefont/"),
  )
  // Every source, by name; only a public link is shown, never a git address.
  for s in data.sources {
    made.push((s.name, "songs from this collection", if s.link != "" { s.link }))
  }
  let address(url) = url.trim("https://", at: start).trim("http://", at: start).trim("/", at: end)
  section-page[
    #if credited.len() == 0 { opening }
    #heading(level: 2)[About this book]
    #kicker[ABOUT THIS BOOK] \
    #text(26pt, weight: "bold")[How it was made]
    #v(4mm)
    // Rules under each row, like the index. The address sits under the description.
    #table(
      columns: (auto, 1fr),
      inset: (left: 0mm, right: 5mm, y: 2.6mm),
      stroke: (bottom: 0.5pt + rule, x: none, top: none),
      ..made.map(((name, what, url)) => {
        let name = text(11pt, weight: "bold", name)
        if url == none {
          (name, [#text(10pt, what) \ #text(9pt, fill: muted)[No public link]])
        } else {
          (link(url, name), [#text(10pt, what) \ #link(url, text(9pt, fill: muted, address(url)))])
        }
      }).flatten()
    )
  ]
}

// ---------- the book ----------

#if measuring {
  index-page()
  for song in data.songs {
    song-page(song, true, "-with")
    song-page(song, false, "-without")
  }
} else {
  if data.title_page { title-page() }
  if data.type == "set-list" { running-order-page() }
  if data.index_page { index-page() }
  for song in data.songs {
    let set-break = song.at("break", default: none)
    if set-break != none { break-page(set-break) }
    song-page(song, song.show_diagrams, "")
  }
  if data.reference_page {
    for (i, chart) in data.charts.enumerate() {
      chart-page(chart, i == 0, data.charts.len() > 1)
    }
    if data.reference_notes { notes-page() }
  }
  if data.credits { credits-section() }
}
