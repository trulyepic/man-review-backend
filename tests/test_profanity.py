import pytest

from app.moderation.profanity import contains_profanity, ensure_clean


def test_contains_profanity_detects_blocked_word_case_insensitively():
    assert contains_profanity("This is SHIT.") == "SHIT"


def test_contains_profanity_does_not_match_inside_larger_words():
    assert contains_profanity("Classic titles are welcome.") is None


def test_ensure_clean_allows_clean_text():
    ensure_clean("A thoughtful reply about a new chapter.")


def test_ensure_clean_raises_for_blocked_word():
    with pytest.raises(ValueError, match="inappropriate language"):
        ensure_clean("This is shit.")
