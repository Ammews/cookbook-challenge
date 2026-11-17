# Sauerbraten

*Source file: `Recipe.pdf` (2 page(s), read by vision) · models: claude-haiku-5-5 · 3 model call(s), 13208 tokens in / 10613 out, 41 s · cost: $0.0066 (repeat runs are served from the cache for $0)*

**Serves:** 6 (**changed**: scaled from 4 servings (assumed by the user: 4))

**Source column:** *read* = written in the document (with the page and the exact words); *guessed* = not written, deduced by the model, with its reasoning; *not given* = the document does not say; *changed* = set by a rule (scaling, vegan).

## Ingredients

| Amount | Ingredient | Source |
| --- | --- | --- |
| ¾ l | Essig (vinegar) | **changed** (scaled); read, p. 1: “1/2 l Essig” |
| ¾ l | Wasser (water) | **changed** (scaled); read, p. 1: “1/2 l Wasser” |
| 6 | Zwiebeln (onions), in Scheiben geschnitten | **changed** (scaled); read, p. 1: “4 in Scheiben geschnittene Zwiebeln” |
| amount not given | Pfeffer (pepper) | read, p. 1: “Pfeffer” |
| amount not given | Nelken (cloves) | read, p. 1: “Nelken” |
| amount not given | Salz (salt) | read, p. 1: “Salz” |
| amount not given | Lorbeerblätter (bay leaves) | read, p. 1: “Lorbeerblätter” |
| amount not given | Braten (roast), fest, Bratenstück | read, p. 1: “die festen Bratenstücke” |
| amount not given | Essigwasser (vinegar water) *[made in the recipe]* | read, p. 2: “das Essigwasser heiß darüber” |
| amount not given | Speck (bacon), auslassen | read, p. 2: “den Speck auslassen” |
| amount not given | Butter | read, p. 2: “Butter dazugeben” |
| some (einige) | Äpfel (apples) *[optional]* | read, p. 2: “einige Äpfel, Möhren und Wacholderbeeren” |
| some (einige) | Möhren (carrots) *[optional]* | read, p. 2: “einige Äpfel, Möhren und Wacholderbeeren” |
| some (einige) | Wacholderbeeren (juniper berries) *[optional]* | read, p. 2: “einige Äpfel, Möhren und Wacholderbeeren” |
| amount not given | Bratenfond (pan juices) *[made in the recipe]* | read, p. 2: “den Bratenfond mit Mehl an” |
| amount not given | Mehl (flour) | read, p. 2: “mit Mehl an” |
| amount not given | Rotwein (red wine) | read, p. 2: “Essigwasser und Rotwein” |
| amount not given | Korinthen (currants), gequollen | read, p. 2: “gequollene Korinthen u. Rosinen” |
| amount not given | Rosinen (raisins), gequollen | read, p. 2: “Korinthen u. Rosinen” |
| to taste (soviel Zucker) | Zucker (sugar) | read, p. 2: “soviel Zucker, daß die Soße einen säuerlich-süßen Geschmack bekommt” |

## Tools

- pot (named in the recipe)

## Method

1. Hierzu eignen sich am besten die festen Bratenstücke.
   *uses: roast*
2. Zum Einlegen Essig, Wasser, Zwiebeln, Pfeffer, Nelken, Salz und Lorbeerblätter aufkochen.
   *uses: vinegar, water, onions, pepper, cloves, salt, bay leaves*
3. Wird der Braten am 1. oder 2. Tag gebraucht, das Essigwasser heiß darübergießen.
   *only if: if the roast is used on day 1 or day 2; uses: vinegar water, roast*
4. Soll der Braten erst nach 8 Tagen zubereitet werden, das Essigwasser kalt darauf gießen.
   *only if: if the roast is prepared only after 8 days; uses: vinegar water, roast*
5. Zum Anbraten den Speck auslassen, Butter dazugeben und den abgetrockneten Braten ins heiße Fett geben.
   *uses: bacon, butter, roast*
6. Wenn der Braten von allen Seiten knusprig angebraten ist, etwas Essigwasser hinzugießen.
   *only if: when the roast is browned crisply on all sides; uses: roast, vinegar water*
7. Optional einige Äpfel, Möhren und Wacholderbeeren in den Topf geben.
   *only if: optional; uses: apples, carrots, juniper berries; with: pot*
8. Den Braten mit den Zutaten langsam garbrötscheln lassen.
   *uses: roast, apples, carrots, juniper berries; with: pot*
9. Für die Soße den Bratenfond mit Mehl anschwitzen, mit Essigwasser und Rotwein auffüllen, gequollene Korinthen und Rosinen hinzugeben und so viel Zucker, dass die Soße süßsauer schmeckt.
   *uses: pan juices, flour, vinegar water, red wine, currants, raisins, sugar*
10. Den Braten, falls noch nicht geschnitten, eine Stunde vor dem Anrichten in die Soße legen, damit er deren Geschmack annimmt.
   *only if: if the roast is not yet cut; time: eine Stunde; uses: roast*

## What changed against the original

| Rule | What | Before | After | Why |
| --- | --- | --- | --- | --- |
| scale | servings | 4 | 6 | Requested 6 servings; the original serves 4 (assumed by the user: 4). |
| scale | essig | ½ l Essig | ¾ l Essig | ×1 ½ |
| scale | wasser | ½ l Wasser | ¾ l Wasser | ×1 ½ |
| scale | zwiebeln | 4 Zwiebeln | 6 Zwiebeln | ×1 ½ |
| scale | amounts not given | Pfeffer, Nelken, Salz, Lorbeerblätter, Braten, Essigwasser, Speck, Butter, Äpfel, Möhren, Wacholderbeeren, Bratenfond, Mehl, Rotwein, Korinthen, Rosinen, Zucker | unchanged | The recipe gives no number for these, so there is nothing to multiply. Adjust by taste. |
| scale | times | as written | unchanged | Cooking and marinating times depend on the size of each piece, not on the number of people. A bigger roast needs longer: check doneness instead of the clock. |
| scale | tools | pot | check sizes | Amounts change by ×1 ½; check that pots and pans still fit. |

## Check before cooking

- The type of meat and its amount are not stated; the roast quantity is absent.
- No amounts are given for pepper, cloves, salt, bay leaves, bacon, butter, flour, red wine, currants, raisins; quantities left absent.
- Servings are not stated and cannot be reliably estimated from the text.
- The text was read by vision; old spelling such as 'garbrötscheln', 'Anbraten' and 'läßt' should be checked against the scan.
- Apples, carrots and juniper berries are marked optional from 'kann man'; amounts are only 'einige'.
- The step about adding the pan-juice sauce mentions 'dass' where the source reads 'daß'; check transcription.
