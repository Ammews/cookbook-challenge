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
| `edge-*` | 6 | A book cover, a soap recipe, medieval medical recipes, a phone photo, a mislabelled medieval manuscript, an 1872 notebook page |

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

## First run: 22 of the 50 documents

[`REPORT.md`](REPORT.md) has the table. What reading the outputs next to the scans showed:

- **No crashes**: 22 documents, 0 errors, $0.10 in total (about $0.004 and 27 s per document).
- **Refusals were right.** The book cover and the 1872 notebook page were refused
  as "not a recipe". So was a file named "Note-manuscrite-recette": the image is
  in fact a medieval Church Slavonic manuscript, mislabelled on Commons. The
  pipeline was right and the file name was wrong.
- **Several recipes per page is the normal case**, not the exception: 11 of the
  19 recipe pages held more than one (up to 12 on two pages of Davidis). The
  pipeline extracts the first and names the others in a warning. For handwritten
  family cookbooks that loses most of the page; extracting every recipe on a page
  is the next improvement this set argues for.
- **"Recipe" is not the same as "food".** A soap recipe and three 17th-century
  medical recipes (Daffy's Elixir, a cure for a scald head, a drink for
  rheumatism) were extracted as recipes. Nothing checks that a recipe is edible;
  a vegan or scaled soap recipe is meaningless.
- **Concrete misreadings, flagged.** On a Bertha page the old pound sign (℔) was
  transcribed as "₩" (the Korean won sign), and "1 Stange Vanille" as "1 Tüten
  Vanille". The model listed the symbol as unreadable in its warnings, so a
  reviewer is told to check it.
- **Pages with only ingredient lists** (Bertha, Backwaren) come out with no steps
  and a warning saying so, instead of invented steps.
- **Old OCR text layers** (the Stag PDFs) produced quotes the code check could not
  find at first (1–2 problems); the correction round fixed all but one, which
  was demoted to "guessed".
