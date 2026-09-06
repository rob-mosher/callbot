import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from callbot.guards import check_bridge_timing, check_press_digits

FACTS = {"full_name": "Casey Rivera", "callback_number": "555-0142"}


def test_menu_selections_allowed():
    for d in ("0", "2", "12", "#", "*"):
        assert check_press_digits(d, FACTS).ok, d


def test_known_number_allowed_with_and_without_hash():
    assert check_press_digits("5550142", FACTS).ok
    assert check_press_digits("5550142#", FACTS).ok


def test_non_dtmf_junk_rejected():
    # The exact failure llama3.1:8b produces on "say or enter your member ID".
    r = check_press_digits("member ID number", FACTS)
    assert not r.ok and "request_missing_info" in r.reason


def test_fabricated_identifier_rejected():
    # The earlier failure mode: a plausible-looking invented ID.
    assert not check_press_digits("1234#", FACTS).ok
    assert not check_press_digits("19850312", FACTS).ok


def test_empty_rejected():
    assert not check_press_digits("", FACTS).ok
    assert not check_press_digits("   ", FACTS).ok


def test_no_facts_means_no_long_sequences():
    assert check_press_digits("2", {}).ok
    assert not check_press_digits("5550142", {}).ok


def test_bridge_refused_in_opening_seconds():
    r = check_bridge_timing(3.0, 15)
    assert not r.ok and "Too early" in r.reason


def test_bridge_allowed_after_threshold():
    assert check_bridge_timing(15.0, 15).ok
    assert check_bridge_timing(120.0, 15).ok
