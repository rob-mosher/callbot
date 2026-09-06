"""Code-level guards on tool arguments.

The prompt is the first line of defense against an 8B model saying something wrong on the
principal's behalf; it is not a sufficient one. These guards enforce the same rules in code,
where they cannot be talked out of.

Rejections are returned to the model as a tool result so it can correct itself mid-call --
that is deliberately more useful than raising, which would just kill the call.
"""

from collections.abc import Mapping
from dataclasses import dataclass

# Digits, DTMF symbols, and pause characters accepted by phone systems.
_DTMF_CHARS = set("0123456789*#,pw")

# Sequences at or below this length are menu selections ("2", "0", "12"); longer ones are
# account numbers, IDs, or dates, and must be traceable to KNOWN FACTS.
MENU_SELECTION_MAX_LEN = 2


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    reason: str = ""


def _digits_only(value: str) -> str:
    return "".join(c for c in value if c.isdigit())


def check_press_digits(digits: str, facts: Mapping[str, str]) -> GuardResult:
    """Reject non-DTMF junk and any long sequence not grounded in KNOWN FACTS."""
    raw = (digits or "").strip()
    if not raw:
        return GuardResult(False, "No digits supplied.")

    if not set(raw) <= _DTMF_CHARS:
        return GuardResult(
            False,
            f"{raw!r} is not a dialable sequence -- a phone keypad only sends digits, * and #. "
            "If you were asked for information you do not have, call request_missing_info.",
        )

    bare = _digits_only(raw)
    if len(bare) <= MENU_SELECTION_MAX_LEN:
        return GuardResult(True)

    # Long sequence: must appear in the disclosure allowlist.
    known = {_digits_only(str(v)) for v in facts.values()}
    known.discard("")
    if any(bare in k or k in bare for k in known):
        return GuardResult(True)

    return GuardResult(
        False,
        f"You tried to send {bare!r}, which does not appear in KNOWN FACTS. Do not guess "
        "identifiers. Call request_missing_info to ask for it instead.",
    )
