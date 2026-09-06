#!/usr/bin/env python3
"""IVR decision regression suite.

Replays transcript snippets against the real shipped prompt (callbot.prompts) and the real
shipped tool schemas (callbot.tools), so this stays a genuine regression net rather than a
test of a parallel copy. Run it on every model or prompt change.

    PYTHONPATH=src python scripts/ivr_eval.py [model ...]

Each case expects either a tool name, a "|"-separated set of acceptable tools, or SPEAK
(meaning: the right move is to say something, not call a tool).
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from callbot.config import settings  # noqa: E402
from callbot.prompts import build_system_prompt  # noqa: E402
from callbot.tools import openai_tools  # noqa: E402

SPEAK = "SPEAK"
SEEDS = (1, 2, 3)

OBJECTIVE = "Cancel Casey's dental insurance policy."
FACTS = {"full_name": "Casey Rivera", "callback_number": "555-0142"}

# (name, transcript, expected, expected_digits or None)
CASES = [
    ("menu_billing", "Thank you for calling Delta Dental. For claims status, press 1. For billing and policy changes, press 2. For provider information, press 3.", "press_digits", "2"),
    ("menu_midread", "Thank you for calling. Please listen carefully as our menu options have recently changed. For claims,", "wait_and_listen", None),
    ("menu_representative", "For all other inquiries or to speak with a representative, press 0.", "press_digits", "0"),
    ("asks_member_id", "Please say or enter your member ID number.", "request_missing_info", None),
    ("asks_dob", "For verification, please enter your date of birth as eight digits.", "request_missing_info", None),
    ("asks_ssn4", "Please enter the last four digits of your social security number.", "request_missing_info", None),
    ("asks_callback_known", "Please enter your ten digit callback number.", "press_digits", "5550142"),
    ("hold_music", "Your call is important to us. Please continue to hold. The next available representative will be with you shortly.", "wait_and_listen", None),
    ("conversational_ivr", "In a few words, please tell me the reason for your call today.", SPEAK, None),
    ("human_greeting", "Hi there, this is Marcus, sorry about the wait -- what can I help you with today?", "human_reached", None),
    ("asks_if_bot", "Wait, am I talking to a real person or is this a recording?", f"{SPEAK}|human_reached", None),
    ("dead_end", "We are unable to process cancellations by phone. You must submit a written request by mail. Goodbye.", "abandon_call|human_reached", None),
]


def decide(model: str, transcript: str, seed: int) -> tuple[str, str]:
    """Return (tool_name or SPEAK, detail)."""
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": build_system_prompt(
                objective=OBJECTIVE, facts=FACTS,
                bot_name=settings.bot_name, principal_name="Casey")},
            {"role": "user", "content": f'Call audio transcript: "{transcript}"'},
        ],
        "tools": openai_tools(),
        "tool_choice": "auto",
        "temperature": 0,
        "seed": seed,
    }).encode()
    req = urllib.request.Request(
        f"{settings.ollama_base_url.rstrip('/')}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        msg = json.load(r)["choices"][0]["message"]
    calls = msg.get("tool_calls") or []
    if calls:
        fn = calls[0]["function"]
        return fn["name"], fn.get("arguments", "")
    return SPEAK, (msg.get("content") or "").strip()


def run(model: str) -> bool:
    print(f"\n=== {model} ===")
    passed = total = 0
    for name, transcript, want, want_digits in CASES:
        results = []
        for seed in SEEDS:
            try:
                results.append(decide(model, transcript, seed))
            except (urllib.error.URLError, OSError, KeyError, ValueError) as e:
                results.append((f"ERROR:{type(e).__name__}", str(e)[:60]))
        good = 0
        for got, detail in results:
            ok = got in want.split("|")
            if ok and want_digits:
                try:
                    got_digits = str(json.loads(detail).get("digits", "")).strip()
                    ok = got_digits.rstrip("#") == want_digits.rstrip("#")
                except (json.JSONDecodeError, AttributeError):
                    ok = False
            good += ok
        passed += good
        total += len(SEEDS)
        mark = "OK   " if good == len(SEEDS) else ("FAIL " if good == 0 else "FLAKY")
        expect = want + (f"/{want_digits}" if want_digits else "")
        print(f"  {mark} {name:22} {good}/{len(SEEDS)}  expect={expect}")
        if good < len(SEEDS):
            for got, detail in results:
                print(f"          got {got}: {detail[:88]}")
    print(f"  ---- {passed}/{total}")
    return passed == total


if __name__ == "__main__":
    models = sys.argv[1:] or [settings.ollama_model]
    sys.exit(0 if all([run(m) for m in models]) else 1)
