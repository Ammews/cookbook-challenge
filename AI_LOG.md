# AI log

How I worked with the coding agent (Claude Code) on this case. One entry per
working session: what I asked for, what the agent did, what was wrong, and what
I decided. Mistakes are listed on purpose.

## Session 1: understanding the case

**Asked:** create the public repository with no AI co-author lines, then gather
study material so I could understand the domain before building.

**What happened**
- The agent created the repo and added a `.gitignore` that keeps `Recipe.pdf`
  and `.env` out of git before any code existed.
- It rendered the two recipe pages and read them, which showed early that the
  PDF has no text layer (each page is one image).

**What went wrong**
- I asked for study material recommended by other people (videos, PDFs). The
  agent instead wrote its own long explainer. I had to correct it; the second
  attempt was a curated, link-checked list.
- When I asked whether the videos would actually help me build the project, the
  agent admitted that about a third of its list was only background, and cut
  the plan from 4.5 hours to 1.5.

## Session 2: stack and data model

**Decisions I made**
- **Python + CLI instead of Java/Spring + Angular.** My first idea was Java and
  Angular because I know them better. The agent argued against the Angular
  part (UI is not scored, it eats the time budget) and laid out the trade-off
  for Java versus Python. I chose Python because it is finlyt's stack and the
  LLM tooling is better, knowing I only have basic Python.
- **Domain objects.** I proposed Recipe, Ingredient and method. The agent
  proposed adding `Source` (where each value came from, and whether it was read
  or inferred), a separate `Quantity`, `Tool`, `Servings` and review warnings. I
  accepted these and asked for SOLID and modular code.

**What the agent built**
- Pydantic models, one file per concept, immutable, with validation rules that
  double as hallucination guards (for example: a value marked "read" must carry
  its quote; a vague quantity such as "einige" cannot hold a number).

**What went wrong**
- The agent wrote plain commit messages. I wanted Conventional Commits. The
  commits were not pushed yet, so it reworded them.
- The agent first looked for the repo in a folder I had moved; it had to
  search for the new location.

## Session 3: ingest stage

**Asked:** build ingest using Anthropic, with cheap models.

**What the agent built**
- File type detection from magic bytes, not from the extension.
- Readers per input kind. For PDFs the choice between text layer and vision is
  made per page, so mixed PDFs work.
- A `Transcriber` protocol with a Claude implementation (Haiku 5.5, structured
  output) and a disk cache wrapped around it.
- Token, time and cost reporting for every run.

**What went wrong, and how it was caught**
- **Image downscaling bug.** The first version opened image files through the
  PDF renderer, which measures pages in points. A 300 px image was silently
  shrunk to 225 px before going to the model. A test written for the
  "small images are not upscaled" rule failed and exposed it. Fixed by reading
  the image's real pixel size.
- **Unreadable error without an API key.** The SDK raises a bare `TypeError`
  when it finds no credentials, so the CLI printed a stack trace. The agent
  only found this by running the CLI without a key. Now it prints one line
  telling the user to set `ANTHROPIC_API_KEY`.
- **A shell command that created several test files failed** on quoting and
  created nothing. The agent noticed, checked what existed, and wrote the files
  one by one.

**First real run (Haiku 5.5, both pages)**
- 2 model calls, 8,758 input and 1,486 output tokens, 8.6 s, **$0.0016**. A
  second run was served entirely from the cache: 0 calls, $0.
- I compared the output with the pages by eye and found no wrong word. The
  drawing labels (Rosinen, Essig, Korinthen, Rotwein), the page numbers and
  the decorative header were kept out of the running text, as intended.
- Two things the model did that I did not ask for:
  - It wrote "1/2 l" where the page has the fraction sign "½ l". Harmless,
    but it shows the transcription is not character-exact, so later quote
    matching has to tolerate small differences.
  - It flagged **no** uncertain words, not even the dialect word
    "garbrötscheln". It read it correctly, but an empty list is not proof of
    certainty: one clean run says little about how stable the reading is.
    Running the same page several times and comparing is still to do.

## Session 4: evaluation set

**My idea:** collect recipes of many kinds online, with the expected results,
so the pipeline can be validated on more than the one recipe it was built on.

**What the agent pushed back on, and I agreed**
- **Licences.** Copying recipes from cooking sites into a public repo has the
  same problem as committing `Recipe.pdf`. It used only Wikibooks (CC BY-SA),
  Wikimedia Commons (public domain, CC0, CC BY-SA) and a text written for the
  project, and recorded the exact revision of every source.
- **Who writes the answer key.** If the agent writes the expected results and
  another model is graded against them, the evaluation is circular. The
  expectations are short checks I can review one by one, and every case starts
  as `reviewed: false` until I have done that.

**What it found while searching**
- A Fraktur-printed page from Henriette Davidis (1879) whose Wikisource
  volunteers already transcribed it. That gives a free human transcription to
  measure reading errors against.
- A Brazilian carrot-cake page with seven recipes on it, and a Soviet notebook
  with three, both useful for "several recipes in one document".
- The set already exposed a gap in my data model: ranges like "2–3 cups" have
  no representation, because `Quantity` holds one number.

**What went wrong**
- Wikimedia refused downloads with HTTP 429 until the agent sent a
  descriptive user agent, as their policy asks.
- Its first quoting of a YAML note broke the parser; the dataset test caught
  it.
- In two places its first draft of a check would have failed a correct
  answer (an ingredient named "fat from a Sauerbraten" would have tripped the
  "Sauerbraten must be absent" check). It removed those before committing, but
  this is exactly why I need to review the checks.

## Session 5: extraction, rules, output, evaluation, README (submission day)

**Asked:** finish everything today. I let the agent take small decisions and
report them, and asked for commits along the way.

**What the agent built**
- Extraction with Claude Haiku 5.5 and a code check of every quote and number,
  one correction round, then demotion to "guessed" with a warning.
- Scaling and vegan rules as pure functions, with a substitution table in a
  data file; tests for commutativity and idempotence.
- Markdown and JSON output with a source column per ingredient, a change table
  and a "check before cooking" list; `run` and `eval` commands.

**What went wrong, and how it was caught**
- **API rejected the first extraction schema** ("compiled grammar is too
  large"). Cause: every nullable field doubles the grammar for constrained
  decoding. The agent flattened the wire schema ("" and 0 for "not given")
  and kept the domain model strict.
- **Wrong vegan note in the sauce step.** Reading the generated example, the
  sauce step said "use seitan instead of Braten": "Braten" matched inside
  "Bratenfond". The agent's first fix (whole word, original name only) broke
  two tests, because a step saying "den Braten" was no longer recognised when
  the ingredient was called "Bratenstücke". Final fix: whole-word match on the
  name and on the table terms.
- **"2 oyster mushrooms" for a whole chicken.** Scaling 1 chicken to 6
  servings gives 2, and the vegan swap kept the count. Now protein swaps say
  "same weight as the chicken it replaces" instead of inventing grams, and a
  test checks that this still commutes with scaling.
- **Wine and sugar shown as "scaled"** in the output when they were only
  flagged by the vegan check. Fixed and tested.
- **Cost shown as $0 in the examples** because the calls came from the cache.
  The header now prices every call as on its first run.
- **First evaluation run: 287/294; after the fixes 294/294.** Five of the seven failures were mistakes
  in the agent's own checks (Portuguese tool names when the model answered in
  English; "creme de cenoura" counted as a duplicate carrot). Two were real:
  the model never listed the oven as a tool. One line in the prompt fixed it.
  This is why the checks stay `reviewed: false` until I go through them.

**Decision I made**
- With prompt v2 the model declined to guess the Sauerbraten servings. I did
  not want to push it into inventing a number, so scaling stops and asks for
  `--assume-servings` when servings are missing, and the output says "assumed
  by the user". With prompt v3 (the oven fix) the model inferred 4 servings
  from the litre of marinade, labelled as guessed. Same document, different
  prompt version, different answer: the cache keys include the prompt version
  for exactly this reason.

## Session 6: optional web page

**Asked:** a simple front end. The agent laid out three options (Streamlit,
static HTML, FastAPI + HTML) and argued against doing it at all on
submission day (UI is not scored). I chose FastAPI + HTML because it helps the
live demo in the interview.

**What it did to keep the risk low**
- Web packages are an optional extra; the three setup commands did not change.
- The endpoint only calls the existing pipeline; all wording comes from the
  same Python as the Markdown, so the page has no recipe logic.
- Endpoint tests run against a scripted model.

**What went wrong**
- Starting the preview server picked up a launch configuration for another of
  my projects from the parent folder and started that server instead. The
  agent stopped it, noticed why, and added its own entry next to mine
  instead of inside the repository.
- Looking at the page in the browser showed a preparation note printed twice
  ("finely chopped, finely chopped"); fixed in the view model.

**Things I should double-check myself**
- The transcription prompt tells the model to re-join words hyphenated across
  lines. That is convenient for later quote matching, but it means the
  transcription is not strictly literal.
- Haiku 5.5 rejects `temperature`, so "temperature 0" is not available as a
  determinism tool. Reproducibility comes from the cache instead.
