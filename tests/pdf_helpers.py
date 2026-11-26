"""Helpers for inspecting built books with pypdf."""

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ArrayObject, DictionaryObject

FIXTURES = Path(__file__).parent / "fixtures" / "carols"
STRIP_CELLS = 28  # Index, A-Z, Reference


@dataclass(frozen=True)
class Link:
    rect: tuple[float, float, float, float]
    target: int  # zero-based page number

    @property
    def size(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.rect
        return (round(x1 - x0, 1), round(y1 - y0, 1))


def text_of(reader: PdfReader) -> str:
    """All extracted text with whitespace collapsed."""
    return re.sub(r"\s+", " ", " ".join(p.extract_text() for p in reader.pages))


def _target_page(reader: PdfReader, dest: object) -> int:
    """Resolve an explicit or named destination to a page number."""
    if isinstance(dest, ArrayObject):
        return reader.get_page_number(dest[0].get_object())
    name = str(dest)
    named = reader.named_destinations[name]
    return reader.get_destination_page_number(named)


def links_on(reader: PdfReader, page_number: int) -> list[Link]:
    links = []
    for ref in reader.pages[page_number].get("/Annots", []):
        annot = ref.get_object()
        if annot.get("/Subtype") != "/Link":
            continue
        action = annot.get("/A")
        action = action.get_object() if action is not None else DictionaryObject()
        dest = annot.get("/Dest", action.get("/D"))
        if dest is None:
            continue
        x0, y0, x1, y1 = (float(v) for v in annot["/Rect"])
        rect = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        links.append(Link(rect, _target_page(reader, dest.get_object())))
    return links


def split_links(reader: PdfReader, page_number: int) -> tuple[list[Link], list[Link]]:
    """Return (strip links left to right, all other links) for a page.

    The strip is the equal-sized links in the bottom band of the page. Its cell
    count depends on the style and options.
    """
    height = float(reader.pages[page_number].mediabox.height)
    links = links_on(reader, page_number)
    strip = [link for link in links if (link.rect[1] + link.rect[3]) / 2 < height / 4]
    strip.sort(key=lambda link: link.rect[0])
    return strip, [link for link in links if link not in strip]


@dataclass(frozen=True)
class BookMap:
    """Where things are, from the top-level bookmarks."""

    titles: list[str]  # bookmark titles in order
    pages: list[int]  # first page of each bookmark
    page_count: int

    def first_page(self, title: str) -> int:
        return self.pages[self.titles.index(title)]

    def pages_of(self, title: str) -> range:
        i = self.titles.index(title)
        end = self.pages[i + 1] if i + 1 < len(self.pages) else self.page_count
        return range(self.pages[i], end)


def book_map(reader: PdfReader) -> BookMap:
    top = [item for item in reader.outline if not isinstance(item, list)]
    return BookMap(
        titles=[item.title for item in top],
        pages=[reader.get_destination_page_number(item) for item in top],
        page_count=len(reader.pages),
    )
