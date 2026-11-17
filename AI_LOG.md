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

**Things I should double-check myself**
- The transcription prompt tells the model to re-join words hyphenated across
  lines. That is convenient for later quote matching, but it means the
  transcription is not strictly literal.
- Haiku 5.5 rejects `temperature`, so "temperature 0" is not available as a
  determinism tool. Reproducibility comes from the cache instead.
