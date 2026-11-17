"""Check, in plain code, that what the model says it read is really in the document.

Two checks, both deterministic:
- quote check: every quote must appear in the document text (tolerating the
  small differences a transcription introduces: "½" vs "1/2", case, spacing,
  long s, hyphenation);
- number check: an exact quantity marked "read" must have its number in its
  own quote. "4 Zwiebeln" can support 4, it cannot support 5.

Anything that fails is reported as a violation. The extractor sends the
violations back to the model once, and demotes whatever still fails to
"inferred" with a review warning.
"""

import re
import unicodedata
from difflib import SequenceMatcher

_FRACTIONS = {
    "½": 1 / 2, "⅓": 1 / 3, "⅔": 2 / 3, "¼": 1 / 4, "¾": 3 / 4,
    "⅕": 1 / 5, "⅛": 1 / 8, "⅜": 3 / 8, "⅝": 5 / 8, "⅞": 7 / 8,
}
_NUMBER_WORDS = {
    # en
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "dozen": 12, "half": 0.5,
    # de
    "ein": 1, "eine": 1, "einen": 1, "einem": 1, "einer": 1, "zwei": 2, "drei": 3, "vier": 4,
    "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "zwölf": 12,
    "halb": 0.5, "halbe": 0.5, "halben": 0.5,
    # pt
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "meia": 0.5, "meio": 0.5, "dúzia": 12,
}
_FUZZY_THRESHOLD = 0.85
_MIN_FUZZY_LENGTH = 6


def normalise(text: str) -> str:
    """Make document text and quotes comparable."""
    text = unicodedata.normalize("NFC", text)
    for char, value in _FRACTIONS.items():
        text = text.replace(char, f" {_fraction_text(value)} ")
    text = text.replace("ſ", "s").replace("­", "")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)  # re-join hyphenated line breaks
    text = re.sub(r"[‐-―−]", "-", text)
    text = text.lower()
    text = re.sub(r"[^\w/.,-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def quote_in_text(quote: str, text: str) -> bool:
    """True if the quote appears in the text, allowing for small transcription noise."""
    needle, haystack = normalise(quote), normalise(text)
    if not needle:
        return False
    if needle in haystack:
        return True
    if len(needle) < _MIN_FUZZY_LENGTH or len(haystack) < len(needle):
        return False
    window = len(needle)
    step = max(1, window // 6)
    for start in range(0, len(haystack) - window + 1, step):
        if SequenceMatcher(None, needle, haystack[start:start + window]).ratio() >= _FUZZY_THRESHOLD:
            return True
    return False


def numbers_in(text: str) -> list[float]:
    """Every number a quote can support: digits, decimals, fractions, mixed numbers, number words."""
    text = text.lower()
    for char, value in _FRACTIONS.items():
        text = text.replace(char, f" {_fraction_text(value)} ")
    found: list[float] = []
    consumed = text
    for whole, num, den in re.findall(r"(\d+)\s+(\d+)\s*/\s*(\d+)", consumed):
        if int(den):
            found.append(int(whole) + int(num) / int(den))
    for num, den in re.findall(r"(\d+)\s*/\s*(\d+)", consumed):
        if int(den):
            found.append(int(num) / int(den))
    for match in re.findall(r"\d+(?:[.,]\d+)?", consumed):
        found.append(float(match.replace(",", ".")))
    for word in re.findall(r"[^\W\d_]+", text):
        if word in _NUMBER_WORDS:
            found.append(float(_NUMBER_WORDS[word]))
    return found


def number_supported(value: float, quote: str, tolerance: float = 0.01) -> bool:
    return any(abs(value - n) <= tolerance * max(1.0, abs(value)) for n in numbers_in(quote))


def _fraction_text(value: float) -> str:
    for den in (2, 3, 4, 5, 8):
        num = round(value * den)
        if abs(num / den - value) < 1e-9:
            return f"{num}/{den}"
    return str(value)
