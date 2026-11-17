# Evaluation set

Twelve inputs chosen to break the pipeline in different ways, each with a list
of checks a correct extraction must pass. There is no "correct JSON" to diff
against: each case holds checks a human can review one at a time, such as
"onion: exactly one ingredient, quantity 4" or "lemon must not appear, it is
only in the notes".

## Cases

| Case | Input | What it tests |
| --- | --- | --- |
| `de-sauerbraten-1887` | scanned PDF, handwriting | The case-study recipe. Kept local, never committed. |
| `de-davidis-1879-fraktur` | scanned page, Fraktur print | Blackletter type, three recipes on one page, prose with no ingredient list. Has a human reference transcription. |
| `en-gingerbread-card` | photo of a typed card | Two-column layout, "c" and "t" abbreviations. |
| `ru-soviet-notebook` | low-resolution photo | Cyrillic, handwriting, three recipes. Success means warning, not reading it perfectly. |
| `en-chocolate-chip-cookies` | text | One amount in four units; notes that name other ingredients. |
| `en-pound-cake` | text | Intro amounts that are not the recipe; old pound units. |
| `en-chicken-paprikash` | text | Stated servings and equipment; ranges; vegan stress test. |
| `en-hummus` | text | Already vegan; salt listed twice. |
| `pt-bolo-de-cenoura` | text | Seven recipes on one page; Brazilian household units. |
| `de-linseneintopf` | text | Vegetarian, not vegan; decimal comma; 21 ingredients. |
| `not-a-recipe` | text | A shopping list. The pipeline must refuse, not invent steps. |
| `en-vegan-traps` | text | Pesto, Worcestershire sauce and egg noodles (animal, unnamed); butternut and coconut milk (plant, animal-sounding names). Checks the animal-content classification. |

## Layout

```
evals/cases/<id>/
  case.yaml                    source, licence, traps and the checks
  input.txt | input.jpg        the document (absent for local-only cases)
  reference_transcription.txt  optional: human transcription of an image
```

The check format is defined in `src/cookbook/evaluation/spec.py` and applied
by `src/cookbook/evaluation/checks.py`.

## Review status

The checks were drafted by the coding agent from the sources. A model writing
the answer key for another model is circular, so **every case starts with
`reviewed: false`** and only counts as ground truth once a person has compared
each check with the source and set it to `true`.

## Sources and licences

Only openly licensed or public-domain material is committed. Wikibooks texts are
CC BY-SA 4.0; each `case.yaml` links the exact page revision used, which is the
attribution the licence asks for. Image licences are listed per case. The
Sauerbraten page comes from a printed book, so it stays out of git like any
customer document would.

## Known gaps the set already exposes

- **Ranges.** "2–3 cups", "2–3 cloves" and "1–2 Theelöffel" have no proper
  representation: `Quantity` holds one number. The checks accept any value in
  the range for now.
- **Several recipes in one document.** Three cases need the pipeline to report
  how many recipes it found; extraction has to provide that.
