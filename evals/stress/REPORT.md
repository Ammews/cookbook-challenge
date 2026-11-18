# Stress run

22 of 50 documents run: **19 read as a recipe, 3 refused as not a recipe, 0 errors.** 11 reported several recipes on the page. Cost $0.096 for the first run (53 new calls this time), 587 s in total.

No expected answers here: read each output in `results/` next to its scan in `files/`.
Every document is also run through the vegan rule, to see what it flags.

| Document | Type | Lang | Read by | Result | Recipes | Ingr. | Steps | Guessed | Problems (found/left) | Warnings | Vegan | Time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [hw-de-bertha-braten-1](results/hw-de-bertha-braten-1.md) | handwritten | de | vision | Rindfleischerbraten | 2 | 11 | 9 |  | 0/0 | 6 | not fully | 30 s |
| [hw-de-bertha-saucen](results/hw-de-bertha-saucen.md) | handwritten | de | vision | Eiweiß-Guß | 3 | 6 | 4 |  | 0/0 | 5 | ok | 21 s |
| [hw-de-bertha-backwaren](results/hw-de-bertha-backwaren.md) | handwritten | de | vision | Grießguß | 5 | 5 |  |  | 0/0 | 4 | ok | 23 s |
| [hw-de-bertha-getraenke](results/hw-de-bertha-getraenke.md) | handwritten | de | vision | Löffelbiskuit | 4 | 5 | 4 |  | 0/0 | 6 | ok | 26 s |
| [hw-en-17c-recipe-book-1](results/hw-en-17c-recipe-book-1.md) | handwritten | en | vision | For a scald Head | 9 | 2 | 3 |  | 0/0 | 6 | ok | 17 s |
| [hw-en-fanshawe](results/hw-en-fanshawe.md) | handwritten | en | vision | Drink for a Rheumatick Body inclined to  | 4 | 13 | 4 | 1 | 0/0 | 6 | ok | 27 s |
| [hw-en-daffys-elixir](results/hw-en-daffys-elixir.md) | handwritten | en | vision | Dr Daffy's Elixir | 1 | 9 | 6 | 1 | 1/0 | 9 | not fully | 37 s |
| [card-en-apple-cake](results/card-en-apple-cake.md) | card | en | vision | Apple Cake | 1 | 10 | 7 |  | 0/0 | 8 | ok | 24 s |
| [card-en-aunt-ruth](results/card-en-aunt-ruth.md) | card | en | vision | Aunt Ruth's Pound Cake | 1 | 5 | 8 |  | 0/0 | 4 | ok | 15 s |
| [card-en-key-lime-pie](results/card-en-key-lime-pie.md) | card | en | vision | Ann's Key Lime Pie | 2 | 7 | 7 |  | 0/0 | 7 | not fully | 25 s |
| [card-en-fudge-cake](results/card-en-fudge-cake.md) | card | en | vision | Wellsey Fudge Cake | 1 | 10 | 5 |  | 0/0 | 7 | not fully | 24 s |
| [pdf-en-stag-waffles](results/pdf-en-stag-waffles.md) | printed | en | pdf_text_layer | Waffles | 1 | 7 | 4 |  | 1/0 | 5 | ok | 24 s |
| [pdf-en-stag-chili](results/pdf-en-stag-chili.md) | printed | en | pdf_text_layer | Chili con Carne | 1 | 8 | 8 | 1 | 1/0 | 8 | ok | 31 s |
| [pdf-en-stag-favorite-menu](results/pdf-en-stag-favorite-menu.md) | printed | en | pdf_text_layer | A Favorite Menu: Corned Beef Hash with B | 1 | 15 | 14 | 2 | 2/0 | 7 | not fully | 54 s |
| [pdf-de-augsburgisches](results/pdf-de-augsburgisches.md) | printed | de | vision | Rouletten von Kalbfleisch auf andre Art | 3 | 12 | 8 |  | 0/0 | 5 | not fully | 40 s |
| [pdf-de-davidis](results/pdf-de-davidis.md) | printed | de | vision | Gebackener Aal | 12 | 6 | 3 | 1 | 0/0 | 6 | not fully | 34 s |
| [pdf-fr-gouffe](results/pdf-fr-gouffe.md) | printed | fr | vision | Marmelade d'abricots | 4 | 2 | 6 | 1 | 1/0 | 7 | ok | 51 s |
| [pdf-en-way-to-mans-heart](results/pdf-en-way-to-mans-heart.md) | printed | en | vision | Winter Salad | 7 | 5 | 5 | 1 | 1/1 | 9 | not fully | 31 s |
| [edge-de-juedisches-kochbuch](results/edge-de-juedisches-kochbuch.md) | printed | de | vision | not a recipe |  |  |  |  | 0/0 |  |  | 5 s |
| [edge-nl-soap-recipe](results/edge-nl-soap-recipe.md) | handwritten | nl | vision | Zeep (soap recipe) | 1 | 3 | 4 |  | 0/0 | 6 | ok | 23 s |
| [edge-fr-handwritten-note](results/edge-fr-handwritten-note.md) | handwritten | fr | vision | not a recipe |  |  |  |  | 0/0 |  |  | 13 s |
| [edge-fr-carnet-1872](results/edge-fr-carnet-1872.md) | handwritten | fr | vision | not a recipe |  |  |  |  | 0/0 |  |  | 10 s |
