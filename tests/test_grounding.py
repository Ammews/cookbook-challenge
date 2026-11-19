import pytest

from cookbook.extract.grounding import number_supported, numbers_in, quote_in_text

PAGE = (
    "Zum Einlegen kocht man ½ l Essig, ½ l Wasser, 4 in Scheiben geschnittene Zwiebeln, "
    "Pfeffer, Nelken, Salz und Lorbeerblätter. Man läßt den Braten langsam gar-\nbrötscheln."
)


def test_exact_quote_is_found():
    assert quote_in_text("4 in Scheiben geschnittene Zwiebeln", PAGE)


def test_fraction_written_differently_is_still_the_same_text():
    assert quote_in_text("1/2 l Essig", PAGE)


def test_case_spacing_and_line_break_hyphen_are_tolerated():
    assert quote_in_text("man  LÄSST den braten langsam garbrötscheln", PAGE.replace("läßt", "lässt"))


def test_small_transcription_noise_is_tolerated():
    assert quote_in_text("4 in Scheiben geschnitene Zwiebeln", PAGE)


def test_invented_quote_is_rejected():
    assert not quote_in_text("2 Pfund Rindfleisch", PAGE)


def test_empty_quote_is_rejected():
    assert not quote_in_text("  ", PAGE)


def test_long_s_matches_round_s():
    assert quote_in_text("Rother Sommerkohl", "Rother Sommerkohl ist dem Winterkohl")
    assert quote_in_text("Roſther", "Rosther")


@pytest.mark.parametrize(
    ("quote", "expected"),
    [
        ("½ l Essig", 0.5),
        ("2 ¼ cups flour", 2.25),
        ("3/4 c molasses", 0.75),
        ("1,2 Liter Gemüsebrühe", 1.2),
        ("2–3 eggs", 3),
        ("vier Zwiebeln", 4),
        ("two eggs", 2),
        ("uma xícara", 1),
    ],
)
def test_numbers_are_found_in_every_common_spelling(quote, expected):
    assert number_supported(expected, quote)


def test_number_not_in_the_quote_is_not_supported():
    assert not number_supported(5, "4 in Scheiben geschnittene Zwiebeln")


def test_digit_inside_a_word_still_counts_once():
    assert 12 in numbers_in("12 oz")


# The fuzzy match tolerates noise in words, never in numbers. Before this, a
# quote with one digit changed was still ~90% similar and passed, and the
# number check then found the wrong number in the model's own (wrong) quote.

STEP = "Man schneidet 4 Zwiebeln in Scheiben und gibt 2 Lorbeerblätter und ½ l Essig dazu."


@pytest.mark.parametrize(
    "quote",
    ["5 Zwiebeln", "3 Lorbeerblätter", "9 Zwiebeln in Scheiben", "4 Zwiebeln in Scheiben und gibt 3 Lorbeerblätter"],
)
def test_a_changed_number_is_not_accepted_as_transcription_noise(quote):
    assert not quote_in_text(quote, STEP)


def test_noise_in_words_is_still_tolerated_when_the_numbers_match():
    assert quote_in_text("4 Zwiebeln in Scheibn", STEP)
    assert quote_in_text("gibt 2 Lorberblätter und", STEP)


def test_fraction_sign_and_slash_are_the_same_number_in_a_near_match():
    assert quote_in_text("und 1/2 l Esig dazu", STEP)


def test_a_number_at_the_edge_of_the_window_is_read_in_full():
    page = "Dann 12 Eier schlagen und alles gut verrühren."
    assert quote_in_text("Dann 12 Eier schlagn", page)
    assert not quote_in_text("Dann 13 Eier schlagn", page)


def test_an_article_gained_or_lost_does_not_count_as_a_number():
    assert quote_in_text("add a pinch of salt and stir well", "add the pinch of salt and stir well")


def test_a_changed_number_word_is_not_accepted_either():
    assert not quote_in_text("fünf Zwiebeln in Scheiben schneiden", "vier Zwiebeln in Scheiben schneiden")
