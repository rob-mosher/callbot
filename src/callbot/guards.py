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


def check_bridge_timing(elapsed_seconds: float, min_seconds: int) -> GuardResult:
    """Refuse to bridge in the opening seconds of a call.

    Bridging dials the principal's phone, so a false positive rings them for nothing and
    drops them into a call with an IVR. Recorded greetings and "how can I help you today"
    prompts are exactly what fools a small model early, before there is enough conversation
    to judge. Cheap insurance on an expensive mistake.
    """
    if elapsed_seconds < min_seconds:
        remaining = min_seconds - elapsed_seconds
        return GuardResult(
            False,
            f"Too early to bridge ({elapsed_seconds:.0f}s into the call; {remaining:.0f}s to go). "
            "Keep working the call. If this really is a person, say something to them and "
            "confirm from their reply before declaring again.",
        )
    return GuardResult(True)
