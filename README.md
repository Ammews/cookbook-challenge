# Cookbook pipeline

Turns a recipe in any format (scanned PDF, photo, digital PDF, plain text, any
language) into a structured recipe you can scale and make vegan, and shows,
for every value, whether it was **read** from the page, **guessed**, or
**changed** by a rule.

Built for the finlyt Cookbook Challenge. The test input is a handwritten
Sauerbraten from 1887; the pipeline is also measured on an
[12-case evaluation set](evals/README.md) it was not tuned on.

**At a glance**

| | |
| --- | --- |
| Sauerbraten, first run | 3 model calls, ≈ 38 s, **≈ $0.006** (repeat runs: $0, from cache) |
| Evaluation set (12 inputs, 4 languages) | **315/316** checks passed, **≈ $0.05** for the whole set |
| Fraktur page from 1879 vs human transcription | **99 %** character similarity |
| Tests | 302, no network or API key needed (10 of them need the optional web extra) |
| Model | Claude Haiku 5.5 for reading and extracting; everything else is plain code |

## Run it

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env          # then put your ANTHROPIC_API_KEY in .env
uv run cookbook run Recipe.pdf --vegan --servings 6 --assume-servings 4
```

`Recipe.pdf` is not in the repository (it is a page from a printed book, the
same reason customer documents never go into git). **Put it in the repository
root.**

The command writes `out/recipe_vegan_6-servings.md` (to cook from) and `.json`
(everything, including provenance and cost).

```bash
uv run cookbook run <file>                  # extraction only
uv run cookbook run <file> --servings 6     # scale (needs servings: stated, inferred or --assume-servings)
uv run cookbook run <file> --vegan          # make it vegan
uv run cookbook run <file> --metric         # convert cups, spoons, lb, Pfund, oz to ml, l, g, kg
uv run cookbook eval                        # run the evaluation set, writes evals/results/latest.md
uv run cookbook ingest <file>               # only show what was read from the file
uv run pytest                               # tests (no API key needed)
```

### Optional: web page

A small local page to drop a file, tick "vegan", choose servings and see the
result with a colour-coded source for every value. It is an optional extra,
so the setup above stays the same.

```bash
uv sync --extra web
uv run --extra web cookbook web     # then open http://127.0.0.1:8000
```

It calls the same pipeline as the CLI (`src/cookbook/web/`: a FastAPI endpoint
and one HTML file with no build step and no external scripts).

Example outputs: [`examples/sauerbraten/`](examples/sauerbraten) (raw extraction,
6 servings, vegan, vegan for 6), plus a second recipe in English
([`examples/chicken-paprikash/`](examples/chicken-paprikash)) and a photographed
typewritten card ([`examples/gingerbread-card/`](examples/gingerbread-card)).

## Architecture

```
file ──► 1 INGEST ──► Document ──► 2 EXTRACT ──► Recipe ──► 3 MANIPULATE ──► Recipe + changes ──► 4 OUTPUT
         detect kind    page texts    LLM answer      every value     pure rules:         Markdown + JSON
         by content     + how read    + code check    has a Source    scale, vegan
```

| Module | What it does | LLM? |
| --- | --- | --- |
| `ingest/detect.py` | Decides PDF / image / text from the file's bytes, not its extension | no |
| `ingest/readers.py` | Text file: read it. PDF: per page, use the text layer if there is one, else render the page and send it to the vision model. Image: downscale and send | only for pages without text |
| `ingest/claude_transcriber.py` | Literal transcription; drawing labels and page numbers kept apart from the running text; unsure words listed | **yes** |
| `extract/` | Model answers in a fixed schema with a quote per value; `grounding.py` checks in code that every quote is in the document and every number is in its quote; problems go back to the model once; what still fails is demoted to "guessed" with a warning | **yes**, checked by code |
| `manipulate/` | Scaling and vegan as pure functions returning a new recipe and a list of changes. Substitutions are a [data file](src/cookbook/manipulate/vegan_substitutions.yaml) | no |
| `output/` | Markdown for the cook, JSON for machines | no |
| `evaluation/` | Runs the set, applies hand-reviewable checks, writes a report | no |
| `models/` | Pydantic domain objects, immutable, validating their own rules | no |

Each stage depends on interfaces, not on Claude: the readers take a
`Transcriber`, the extractor takes an `ExtractionModel`. Only `build_ingestor`
and `build_extractor` know about Anthropic, which is also how every test runs
with fakes.

### The data model is part of the hallucination defence

- `Source.status` is `read`, `inferred`, `missing` or `rule`. A `read` value
  **must** carry its quote; an `inferred` one **must** say why.
- `Quantity.kind` is `exact`, `vague`, `to_taste` or `absent`, and **only
  `exact` may hold a number**. There is no field where "einige Äpfel" could
  become 3 apples.
- Ranges ("2–3 cups") have a lower and an upper value.
- `is_intermediate` marks things the recipe makes and reuses
  (*Essigwasser*, *Bratenfond*).

## The four stages: what is hard, what I did, what I rejected

### 1. Ingest

**What is hard in this recipe**
- `Recipe.pdf` has **no text layer**: each page is one photo. Text extraction
  returns an empty string, so the router has to notice and switch to vision.
- **The drawings carry labels** that look like ingredients: *Rosinen*, *Essig*,
  *Korinthen*, *Rotwein*, plus a salt shaker and bay leaves. Raisins appear
  both in the drawing (p. 188) and in the text (p. 189).
- **Line breaks split words**: *Bra-tenstücke*, *abgetrockne-ten*,
  *gar-brötscheln*, *Rot-wein*. On p. 189 the lines slope, and "so gießt man"
  sits between two lines.
- **Dialect and old spelling**: *garbrötscheln* is in no standard dictionary;
  *läßt*, *daß*.

**What I did**
- Detect the type from magic bytes; decide text layer vs vision **per page**,
  so a PDF that mixes exported and scanned pages works.
- Vision transcription returns three things: running text, "not running text"
  (drawing labels, headers, page numbers) and uncertain words. The drawing
  labels are passed to extraction explicitly as *not evidence*.
- Re-join hyphenated words during transcription, so the next stage can match
  quotes.
- **Sentences across a page break**: pages are joined into one text before
  extraction, with page markers, so a sentence that starts on one page and
  ends on the next is read as one sentence and its quote is still found. In
  this recipe p. 188 happens to end with a full sentence; the Fraktur case in
  the evaluation set has a recipe cut mid-sentence at the bottom of the page.

**Result**: Haiku 5.5 read both pages without a wrong word I could find, kept
all four drawing labels out of the running text, and read *garbrötscheln*
correctly. It wrote "1/2 l" where the page has "½ l", which is why quote
matching tolerates small differences. On the Fraktur page from 1879 in the
evaluation set, the transcription was 99 % similar to the Wikisource
volunteers' transcription.

**Rejected**
- **Tesseract / classic OCR**: weak on handwriting and blackletter; a vision
  model was cheaper in engineering time and good enough.
- **Image straight to structured recipe in one call**: cheaper, but leaves no
  text to check quotes against. Keeping a transcription step makes the
  extraction verifiable.

### 2. Extract

**What is hard in this recipe**
- **The meat is never quantified** ("die festen Bratenstücke").
- **Servings are never stated.**
- **Quantities that are not numbers**: "einige Äpfel", "etwas Essigwasser",
  "soviel Zucker, daß die Soße einen säuerlich-süßen Geschmack bekommt" (an
  amount defined by a taste condition).
- **Optional ingredients** are signalled only by language: "Auch kann man
  einige Äpfel, Möhren und Wacholderbeeren in den Topf geben."
- **Intermediates**: *Essigwasser* is made in step 1 and used three times;
  *Bratenfond* is produced by browning the meat.
- **A conditional branch**: pour the marinade hot if the roast is used after
  1–2 days, cold if after 8.
- **Implied tools**: only *Topf* is named; slicing onions needs a knife.

**What I did**
- The model answers in a fixed schema, with an evidence status and a verbatim
  quote for every ingredient, tool, step and the servings.
- **Code checks every answer** (`extract/grounding.py`): each quote must be in
  the transcribed text (tolerating case, "½" vs "1/2", long s, hyphenation and
  small transcription noise), and each "read" amount must appear in its own
  quote ("4 Zwiebeln" supports 4, not 5). The tolerance in quote matching is
  for words only: a near match must hold exactly the same numbers, so a quote
  copied with a changed number ("5 Zwiebeln" for "4 Zwiebeln", 90 % similar)
  is rejected, not accepted as noise. Ids used by steps must exist.
- Problems go back to the model **once**, with the exact list. Whatever still
  fails is not hidden: it is demoted to "guessed" and a warning is added.
- **Duplicates are merged in code**, not only by asking the model: two entries
  with the same original or English name ("Salt" and "salt to taste") become
  one, the most precise amount is kept, steps are pointed at the survivor, and
  a warning says what was merged. Different things with similar names
  (*Korinthen* and *Rosinen*) stay apart.
- The prompt asks to extract only the recipe (not notes, variations or side
  dishes), to report how many recipes the document holds, and to refuse
  documents that are not recipes.

**Result on the Sauerbraten**: 20 ingredients, all with a quote that the code
found in the page; the meat has no amount; apples, carrots and juniper are
optional; *Essigwasser* and *Bratenfond* are intermediates; the hot/cold
marinade is a condition on two steps; raisins appear once. The servings are
**guessed and labelled as guessed**: "4, estimated from about 1 l of marinade".
With an earlier prompt version the model declined to guess ("cannot be
reliably estimated"), which is a fair answer too. The pipeline handles both:
if the servings are missing, scaling stops and asks for `--assume-servings`,
and the output then says "assumed by the user". Whatever the source, a scaled
recipe states what its starting number was based on.

**Rejected**
- **Rules/regex for ingredient lines**: would work on the English test recipes
  and fail on 1887 German prose.
- **Asking the model for a confidence score**: uncalibrated. Confidence here
  comes from evidence the code can check: quote found, number in quote,
  correction needed or not.
- **Nullable fields in the schema**: my first schema was rejected by the API
  ("compiled grammar is too large"). Every nullable field doubles the grammar,
  so the wire schema uses "" and 0 for "not given", and the mapper converts back.

### 3. Manipulate

**What is hard**
- **Not everything scales linearly.** Liquids do. Counted items need rounding
  (1.5 eggs). Salt, pepper and "soviel Zucker" have no number to scale.
  **Marinating and braising times do not depend on the number of people** but
  on the size of each piece. The pot may stop fitting.
- **Vegan when the meat is the dish.** Replacing *Braten* changes the
  marinade (a week in vinegar destroys seitan), the browning, and removes the
  *Bratenfond*, which the sauce is built on.
- **Order**: vegan-then-scale must equal scale-then-vegan.
- **Units**: the same letters mean different things. "t" is a teaspoon and "T"
  a tablespoon on an American card; a German *Pfund* is 500 g, an English
  pound 453.6 g; "colher (chá)" and "colher (sopa)" differ by three times.
  "Teeglas" and "Stück" have no standard size at all.

**What I did**
- Both rules are **pure functions in code**, `Recipe -> (Recipe, [Change])`.
  No model, no randomness, so they are reproducible and fully tested.
- Scaling: exact amounts × factor (ranges at both ends); counted items rounded
  to whole pieces and the rounding is reported; vague and to-taste amounts
  untouched with a note; times untouched with a note to check doneness; a pot
  size warning when the amount changes by ×1.5 or more.
- Vegan is split in two. **Recognising** what an ingredient contains is a
  language task, so the extraction model classifies every ingredient
  (`animal`: none, meat, poultry, fish, dairy, egg, honey, gelatin,
  other_animal, uncertain). **Deciding** what to do is code: a
  [substitution table](src/cookbook/manipulate/vegan_substitutions.yaml) in a
  data file anyone can review, searched only among the rows for that
  category. When no row fits ("pesto: contains dairy") or the model is
  unsure, the ingredient is **kept and flagged**, and the recipe is marked
  "not fully vegan". The rule never invents a substitute. Each swap is recorded with its reason;
  every step that used the ingredient gets a visible note, including advice
  that only exists because of the swap ("Marinate seitan for 1–2 days at most").
  The meat-based *Bratenfond* becomes vegetable stock with the pan juices of
  the substitute. Wine and sugar are **flagged, not changed** (fining agents,
  bone char).
- A whole chicken replaced by mushrooms becomes "same weight as the chicken",
  not "2 mushrooms": a count of the original means nothing for the substitute.
- **Metric conversion** (`--metric`) is a third rule
  ([`units.py`](src/cookbook/manipulate/units.py)): cups, spoons, fl oz, lb,
  oz, *Pfund*, *Lot* and Brazilian spoons and cups to ml, l, g and kg. Units
  are matched as written (case matters for t/T); units with no standard size
  are left alone and listed, never guessed. It runs last, so rounding happens
  once, after scaling.
- **Tests prove** that vegan and scaling commute, that vegan applied twice equals
  once, that an already vegan recipe is unchanged, and that "Braten" is not
  matched inside "Bratenfond" (a bug the examples exposed; see AI_LOG.md).

**Rejected**
- **"LLM, make this vegan"**: not reproducible, hard to explain, and nothing
  guarantees it removes the *Speck*. An LLM could later *rewrite the step
  text* fluently; the code check would then verify that no replaced
  ingredient is still mentioned.
- **Recognising animal products with a word list** (the first version): it
  missed pesto, mayonnaise and salami without a warning, and turned butternut
  squash into vegan butter and coconut milk into oat milk. That put a
  language task in code; the model now classifies, the table decides.
- **Letting the model invent a substitute when the table has none**: it would
  give a confident answer exactly where the system knows least. A warning
  asking the cook to choose is the honest answer.
- **Classifying each ingredient's role in the dish** (fat for frying, binder):
  closer to how a cook substitutes, but a role belongs to each use, not to
  the ingredient, and it is another unverifiable model output. Left for later.
- **Scaling cooking times**: physically wrong for a roast.
- **Converting cups of flour to grams**: needs the density of each ingredient
  (a cup of flour ≈ 125 g, of sugar ≈ 200 g). Without a reviewed density
  table that would be a guess, so volume stays volume (2 ½ c flour → 600 ml).

### 4. Output

**What is hard**: the cook must see which parts were read and which were
guessed, and what the manipulation changed.

**What I did**: a Markdown page with one table row per ingredient and a
**Source** column: *read, p. 2: "einige Äpfel, Möhren und Wacholderbeeren"*,
***guessed**: reason*, *not given*, ***changed**: reason*. A table of every
change against the original, and a **Check before cooking** list with the
model's warnings, guessed values and vegan label checks. The JSON has the full
result, including token use per call.

A small optional web page shows the same data with colour-coded source
badges. It holds no recipe logic: the wording comes from the same Python code
as the Markdown.

**Rejected**: a full front-end framework. UI is not scored; a single HTML file
is enough to demo and keeps the setup to three commands.

## The AI challenges

**Hallucination.** Three layers. The *schema* has no place for an invented
number on a vague amount. The *prompt* says what not to extract. *Code*
verifies every quote and every read number against the document, sends
failures back once and demotes what still fails. Detection is measurable: the
evaluation set has "must be absent" checks for ingredients that appear only in
notes, variations, side-dish lists or drawings, and a shopping list that must
be refused rather than turned into a recipe.

**Non-determinism.** Haiku 5.5 does not accept `temperature`, so "temperature
0" is not even available. Reproducibility comes from design instead: every
model response is cached on disk under a key of input + prompt version +
model, so the same document gives the same result, and repeat runs cost $0.
Everything after extraction is deterministic code. Tests never call the model:
they use fakes and fixed answers. Changing the prompt bumps its version, which
invalidates the cache on purpose.

One known gap: the file name is part of the text sent to the extraction model,
so renaming a file (`Recipe.pdf` to `Recipe (4).pdf`) is a cache miss and a new
model call. The page images are still cached, but the extraction can come back
slightly different, for example servings "not stated" instead of "guessed: 4",
or a step split in two. Both answers pass the evaluation checks; it is the
non-determinism above, made visible.

**Validation without ground truth.** [`evals/`](evals/README.md): 11 inputs
(handwriting, Fraktur print, a typed card, Russian, Portuguese, multi-recipe
pages, a non-recipe), each with checks a person can review one by one
("onion: exactly one ingredient, quantity 4"; "lemon must not appear"). The
checks were drafted by the coding agent, so they start as `reviewed: false`:
a model writing the answer key for another model is circular until a human
confirms it. The first run already found **errors in my checks** (Portuguese
tool names, a legitimate intermediate counted as a duplicate) and **one real
weakness** (the oven was not listed as a tool), fixed with one line in the
prompt. First run 287/294, after the fixes **294/294**. With the vegan refactor (prompt v4) and a twelfth case built from vegan traps: **316/317** (the one failure: the model stopped listing the skewer in the pound cake). A later run from an empty cache gave **315/316**: the skewer came back, and the paprikash came out with 16 steps where the check allows 8 to 14. Both are the model's run-to-run variation, not a code change. Report:
[`evals/results/latest.md`](evals/results/latest.md). A perfect score on 11
cases whose checks I have not reviewed yet is a starting point, not proof.

**LLM or code.**

| Task | Where | Why |
| --- | --- | --- |
| Detect file type, choose reader | code | deterministic, free |
| Read handwriting, Fraktur, photos | LLM (vision) | nothing else does it |
| Understand language: optional, intermediate, condition, which amount belongs to what | LLM | needs reading comprehension in any language |
| Say what an ingredient contains (pesto: dairy; coconut milk: none) | LLM | knowledge of products in any language; a word list cannot keep up |
| Choose the vegan substitute, or flag that none is known | code | must be reproducible and reviewable |
| Check quotes and numbers | code | the whole point is not to trust the model |
| Scale, vegan, unit handling | code | must be reproducible and explainable |
| Render output | code | no reason for a model |

In production I would move more to code: a dictionary for common ingredient
names and units, the model only for what it misses.

**Cost and latency.** Measured, not estimated, and printed after every run.
Sauerbraten: 2 vision calls (8.8 k tokens in, 1.5 k out, 9 s) and one
extraction call (4.5 k in, 8 k out, 29 s); total **≈ $0.006 and ≈ 38 s**.
Most of the time is extraction output, which includes the model's thinking;
lower effort would cut it if the evaluation holds. The whole evaluation set
costs **≈ $0.04**. With $5 of credit this project can run about 800
Sauerbratens.

**Trust.** Every ingredient line shows its status, page and exact quote, or
the reason it was guessed, or the rule that changed it. The header shows the
models, calls, tokens and cost. Warnings collect everything uncertain.

## How this maps to finlyt

| Here | At finlyt |
| --- | --- |
| Drawing labels that look like ingredients | Logos, stamps and headers that look like figures |
| Hyphenated words across lines | Tables continuing on the next page |
| Raisins in the drawing and in the text | The same figure in the balance sheet and the notes |
| Meat never quantified | A missing figure that must not be invented |
| *Essigwasser* reused three times | A subtotal used in several positions |
| Vegan rule changing the *Bratenfond* | A bank correction rule with side effects on dependent positions and KPIs |
| Servings scaled from an assumption, labelled as such | EUR vs TEUR, and any figure based on an assumption |

## Known limitations and what I would do with another week

- **Review the evaluation checks myself** and grow the set to ~30 cases,
  including real failures (blurred photos, two-column magazine layouts).
- **Measure stability**: run each case several times without the cache;
  values that change between runs are uncertain and should be flagged.
- **Rewrite vegan steps fluently** with an LLM, verified by code (no replaced
  ingredient may still be mentioned).
- **Volume to weight for dry ingredients**, with a reviewed density table
  (flour, sugar, butter), so "2 ½ c flour" can become grams.
- **Key the extraction cache on content only**: leave the file name out of the
  prompt, so the same document always gives the same answer whatever it is
  called.
- **Lower model effort** for extraction and compare quality, cost and latency
  on the evaluation set; try a stronger model only where the set shows a gap.
- **Several recipes per document**: today the first is extracted and the rest
  are reported; a reviewer should be able to pick which one.
- **LangGraph**: the pipeline is a fixed workflow with one correction loop,
  which plain functions express well. With human review steps (an analyst
  approving before anything is saved), a graph with checkpoints would earn
  its place.

## Working with the coding agent

The code was written with Claude Code, steered and reviewed by me.
[`AI_LOG.md`](AI_LOG.md) records each session: what I asked, what the agent
did, where it was wrong and how it was caught.

## Repository layout

```
src/cookbook/
  ingest/       detect, readers, vision transcriber, cache
  extract/      prompt, wire schema, grounding checks, mapper, extractor
  manipulate/   rules, scale, vegan + substitution table
  output/       Markdown and JSON
  evaluation/   check spec, evaluator, dataset loader, runner
  models/       domain objects
  web/          optional FastAPI endpoint + one HTML page
  cli.py        cookbook run | ingest | eval | web
evals/          11 cases, report
examples/       generated outputs
tests/          unit tests, no network
```
