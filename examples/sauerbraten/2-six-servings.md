# Sauerbraten

*Source file: `Recipe.pdf` (2 page(s), read by vision) · models: claude-haiku-5-5 · 3 model call(s), 13741 tokens in / 10609 out, 41 s · cost: $0.0067 (repeat runs are served from the cache for $0)*

**Serves:** 6 (**changed**: scaled from 4 servings (assumed by the user: 4))

**Source column:** *read* = written in the document (with the page and the exact words); *guessed* = not written, deduced by the model, with its reasoning; *not given* = the document does not say; *changed* = set by a rule (scaling, vegan).

## Ingredients

| Amount | Ingredient | Source |
| --- | --- | --- |
| 0.75 l | Essig (vinegar) | **changed** (scaled); read, p. 1: “1/2 l Essig” |
| 0.75 l | Wasser (water) | **changed** (scaled); read, p. 1: “1/2 l Wasser” |
| 6 | Zwiebeln (onion), in Scheiben geschnitten | **changed** (scaled); read, p. 1: “4 in Scheiben geschnittene Zwiebeln” |
| amount not given | Pfeffer (pepper) | read, p. 1: “Pfeffer” |
| amount not given | Nelken (cloves) | read, p. 1: “Nelken” |
| amount not given | Salz (salt) | read, p. 1: “Salz” |
| amount not given | Lorbeerblätter (bay leaves) | read, p. 1: “Lorbeerblätter” |
| amount not given | Bratenstücke (roast meat), fest *[contains meat]* | read, p. 1: “die festen Bratenstücke” |
| amount not given | Speck (bacon), auslassen *[contains meat]* | read, p. 2: “den Speck auslassen” |
| amount not given | Butter *[contains dairy]* | read, p. 2: “Butter dazugeben” |
| some (einige) | Äpfel (apples) *[optional]* | read, p. 2: “einige Äpfel, Möhren und Wacholderbeeren in den Topf geben” |
| some (einige) | Möhren (carrots) *[optional]* | read, p. 2: “einige Äpfel, Möhren und Wacholderbeeren in den Topf geben” |
| some (einige) | Wacholderbeeren (juniper berries) *[optional]* | read, p. 2: “einige Äpfel, Möhren und Wacholderbeeren in den Topf geben” |
| amount not given | Mehl (flour) | read, p. 2: “mit Mehl an” |
| amount not given | Rotwein (red wine) | read, p. 2: “Essigwasser und Rotwein auf” |
| amount not given | Korinthen (currants), gequollen | read, p. 2: “gequollene Korinthen u. Rosinen” |
| amount not given | Rosinen (raisins), gequollen | read, p. 2: “gequollene Korinthen u. Rosinen” |
| to taste (soviel Zucker, daß die Soße einen säuerlich-süßen Geschmack bekommt) | Zucker (sugar) | read, p. 2: “soviel Zucker, daß die Soße einen säuerlich-süßen Geschmack bekommt” |
| amount not given | Essigwasser (vinegar water) *[made in the recipe]* | read, p. 2: “das Essigwasser heiß darüber” |
| amount not given | Bratenfond (pan juices) *[made in the recipe, contains meat]* | read, p. 2: “den Bratenfond mit Mehl an” |

## Tools

- pot (named in the recipe)
- frying pan (implied: Implied for searing the roast in step 5; not named in the text.)

## Method

1. Zum Einlegen kocht man Essig, Wasser, Zwiebeln, Pfeffer, Nelken, Salz und Lorbeerblätter.
   *uses: vinegar, water, onion, pepper, cloves, salt, bay leaves; with: pot*
2. Hierzu eignen sich am besten die festen Bratenstücke.
   *uses: roast meat*
3. Will man den Braten nach dem 1. Tag oder 2. Tag gebrauchen, so gießt man das Essigwasser heiß darüber.
   *only if: if the roast is used on day 1 or day 2; uses: vinegar water, roast meat*
4. Soll der Braten erst nach 8 Tagen zubereitet werden, so gießt man es kalt darauf.
   *only if: if the roast is prepared only after 8 days; time: nach 8 Tagen; uses: vinegar water, roast meat*
5. Zum Anbraten den Speck auslassen, Butter dazugeben, dann gibt man den abgetrockneten Braten ins heiße Fett.
   *uses: bacon, butter, roast meat; with: frying pan*
6. Wenn er von allen Seiten knusprig angebraten ist, gießt man etwas Essigwasser hinzu.
   *only if: when the roast is browned crisp on all sides; uses: roast meat, vinegar water; with: frying pan*
7. Auch kann man einige Äpfel, Möhren und Wacholderbeeren in den Topf geben.
   *only if: optional; uses: apples, carrots, juniper berries; with: pot*
8. Man läßt den Braten langsam mit den Zutaten garbrötscheln.
   *time: langsam; uses: roast meat, apples, carrots, juniper berries; with: pot*
9. Für die Soße schwitzt man den Bratenfond mit Mehl an, füllt mit Essigwasser und Rotwein auf, gibt dann gequollene Korinthen u. Rosinen hinzu und soviel Zucker, daß die Soße einen säuerlich-süßen Geschmack bekommt.
   *uses: pan juices, flour, vinegar water, red wine, currants, raisins, sugar; with: pot*
10. Man legt den Braten, wenn er noch nicht geschnitten ist, eine Stunde vor dem Anrichten in die Soße, damit er den Geschmack derselben bekommt.
   *only if: if the roast is not yet cut; time: eine Stunde; uses: roast meat*

## What changed against the original

| Rule | What | Before | After | Why |
| --- | --- | --- | --- | --- |
| scale | servings | 4 | 6 | Requested 6 servings; the original serves 4 (assumed by the user: 4). |
| scale | vinegar | 0.5 l Essig | 0.75 l Essig | ×1 ½ |
| scale | water | 0.5 l Wasser | 0.75 l Wasser | ×1 ½ |
| scale | onion | 4 Zwiebeln | 6 Zwiebeln | ×1 ½ |
| scale | amounts not given | Pfeffer, Nelken, Salz, Lorbeerblätter, Bratenstücke, Speck, Butter, Äpfel, Möhren, Wacholderbeeren, Mehl, Rotwein, Korinthen, Rosinen, Zucker, Essigwasser, Bratenfond | unchanged | The recipe gives no number for these, so there is nothing to multiply. Adjust by taste. |
| scale | times | as written | unchanged | Cooking and marinating times depend on the size of each piece, not on the number of people. A bigger roast needs longer: check doneness instead of the clock. |
| scale | tools | pot, frying pan | check sizes | Amounts change by ×1 ½; check that pots and pans still fit. |

## Check before cooking

- The number of servings is not stated; no estimate was possible from the amounts.
- The type of meat is not named; the roast is recorded as roast meat.
- Quantities for meat, bacon, butter, flour, red wine, currants, raisins and spices are not given in the text.
- Apples, carrots and juniper berries are marked by 'einige' and are optional because the text says one can add them.
- Currants and raisins are listed in one phrase; both are recorded separately with the same quote.
- 'garbrötscheln' is an old term for slow braising; kept as written.
- The frying pan and the heat source are implied by the steps and are not named in the text.
- Essigwasser and Bratenfond are intermediates made in the recipe; the marinade and sauce quantities are not stated.
