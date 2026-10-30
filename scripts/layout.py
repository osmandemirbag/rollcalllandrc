"""Rebuild the reading order of the multi-column name lists in the TBMM PDFs.

The PDFs carry an ABBYY OCR text layer. Plain `pdftotext` interleaves the
three to five printed columns, so we read word boxes (`pdftotext -bbox`) and
rebuild the layout ourselves:

  page -> rows (words sharing a baseline across the whole page)
       -> bands between full-width section headers ('[Kabul edenler]' ...)
       -> columns inside a band, found from vertical white-space gutters
       -> lines inside a column, read top to bottom, columns left to right
"""
import html
import re
import subprocess
from dataclasses import dataclass

import numpy as np


@dataclass
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str


@dataclass
class Page:
    number: int
    width: float
    height: float
    words: list


_PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
_WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')


# Vertical column rules read by the OCR as stray characters.
RULE = re.compile(r"[|Il1!\]\[ı'.,:;•\-—_\\/]{0,2}")


def read_pages(pdf, first, last) -> list[Page]:
    r = subprocess.run(["pdftotext", "-bbox", "-f", str(first), "-l", str(last), str(pdf), "-"],
                       capture_output=True, text=True)
    pages = []
    for k, m in enumerate(_PAGE.finditer(r.stdout)):
        words = [Word(float(a), float(b), float(c), float(d), html.unescape(t).replace("\u00ad", "-").replace("|", "").strip())
                 for a, b, c, d, t in _WORD.findall(m[3]) if not RULE.fullmatch(html.unescape(t).strip())]
        pages.append(Page(first + k, float(m[1]), float(m[2]), words))
    return pages


def group_rows(words, tol=None):
    """Cluster words into rows by vertical centre."""
    if not words:
        return []
    h = np.median([w.y1 - w.y0 for w in words])
    tol = tol or 0.5 * h
    ws = sorted(words, key=lambda w: (w.y0 + w.y1) / 2)
    rows, cur, cy = [], [ws[0]], (ws[0].y0 + ws[0].y1) / 2
    for w in ws[1:]:
        c = (w.y0 + w.y1) / 2
        if c - cy <= tol:
            cur.append(w)
            cy = np.mean([(x.y0 + x.y1) / 2 for x in cur])
        else:
            rows.append(sorted(cur, key=lambda w: w.x0))
            cur, cy = [w], c
    rows.append(sorted(cur, key=lambda w: w.x0))
    return rows


def row_text(row) -> str:
    return " ".join(w.text for w in row)


def gutters(words, x_lo, x_hi, min_gap=6.0):
    """x positions of vertical white-space gutters between columns."""
    if not words:
        return []
    n = int(x_hi - x_lo) + 2
    cov = np.zeros(n)
    for w in words:
        a, b = int(w.x0 - x_lo), int(w.x1 - x_lo) + 1
        cov[max(a, 0):min(b, n)] += 1
    # A long name may spill into a gutter; tolerate a little coverage.
    thresh = int(0.05 * len(group_rows(words)))
    low = cov <= thresh
    cuts, i = [], 0
    margin = 25
    while i < n:
        if low[i]:
            j = i
            while j < n and low[j]:
                j += 1
            if j - i >= min_gap and i > margin and j < n - margin:
                cuts.append(x_lo + (i + j) / 2)
            i = j
        else:
            i += 1
    # Merge cuts that are too close to be separate columns.
    merged = []
    for c in cuts:
        if merged and c - merged[-1] < 60:
            continue
        merged.append(c)
    return merged


def column_lines(words, x_lo, x_hi):
    """Lines of a band in reading order: column by column, top to bottom."""
    cuts = gutters(words, x_lo, x_hi)
    edges = [-1e9] + cuts + [1e9]
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        col = [w for w in words if a <= (w.x0 + min(w.x1, w.x0 + 25)) / 2 < b]
        for r in group_rows(col):
            out.append((r, len(out)))
    return [r for r, _ in out]
