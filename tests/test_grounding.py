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
