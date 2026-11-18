# Stress set

Fifty real documents of the kind the pipeline is meant for: handwritten pages,
recipe cards, scanned cookbook pages and PDFs, in English, German, French,
Dutch and Catalan, from the 1600s to the 2020s. Unlike the
[evaluation set](../README.md) they have no expected answers. They exist to find
where the pipeline breaks or hesitates, and to read its output next to the scan.

## What is in it

| Group | Count | What it tests |
| --- | --- | --- |
| `hw-de-bertha-*` | 11 | A German handwritten family cookbook ("Kochbuch von Bertha"): the closest thing to the Sauerbraten |
| `hw-en-*` | 7 | English recipe books from the 1600s and 1700s (Wellcome Collection); one is a medicine, not food |
| `card-en-*` | 8 | Recipe cards, typed and handwritten, 1950s to today; two are two-page scans combined into a PDF; one is 448 px wide |
| `pdf-en-stag-*` | 8 | *The Stag Cook Book* (1922), one page each, PDFs **with** a text layer (old OCR); one is a menu, not a recipe |
| `pdf-de-*`, `pdf-fr-*`, `pdf-en-*` | 10 | Two consecutive pages cut from scanned cookbooks (no text layer), many in Fraktur; pages often hold several recipes or a recipe cut at the page break |
| `edge-*` | 6 | A book cover, a soap recipe, medieval medical recipes, a phone photo, a French note, an 1872 notebook page |

Every file's source page, author and licence are in [`manifest.yaml`](manifest.yaml).
All are public domain or under an open licence (CC0, CC BY, CC BY-SA); CC BY and
CC BY-SA files are attributed there. Images were downscaled to 1800 px on the
long side; book pages were cut from the full scans and the page numbers taken
are recorded.

## Run it

```bash
uv run cookbook stress                 # all 50 (about $0.40 and 40 minutes on a first run)
uv run cookbook stress card-en-apple-cake pdf-fr-gouffe   # selected documents
```

Each document runs through ingest, extraction and the vegan rule. Its Markdown
and JSON go to `results/`, and [`REPORT.md`](REPORT.md) summarises the run:
what was read as a recipe, refused or failed, how many recipes were on the
page, how many values were guessed, what the code check found, cost and time.
Results are cached, so a repeat run is free.
