"""Canonical tool definitions.

Declared as plain dicts so both the Pipecat pipeline and the dependency-light eval
script (scripts/ivr_eval.py) consume the exact same schemas -- the eval is only a
regression net if it tests what actually ships.
"""

from typing import Any

TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "press_digits",
        "description": (
            "Send DTMF tones to the phone system. Use to select a menu option, or to enter "
            "a number that appears verbatim in KNOWN FACTS. NEVER use this for a number you\n"
            "do not have -- call request_missing_info instead."
        ),
        "properties": {
            "digits": {
                "type": "string",
                "description": "Digits to press, e.g. '2' or '5550142#'.",
            }
        },
        "required": ["digits"],
    },
    {
        "name": "wait_and_listen",
        "description": (
            "Do nothing and keep listening. Use when a menu is still reading its options, "
            "when on hold, or when the other party is mid-sentence."
        ),
        "properties": {
            "seconds": {
                "type": "number",
                "description": "Roughly how long to stay quiet before reassessing.",
            }
        },
        "required": ["seconds"],
    },
    {
        "name": "human_reached",
        "description": (
            "Declare that a live human -- not an automated system -- is now speaking. This "
            "immediately calls the principal and bridges them in, so a false positive is "
            "costly. Only call this for unscripted speech directed at you."
        ),
        "properties": {
            "evidence": {
                "type": "string",
                "description": "What specifically indicates this is a live person.",
            }
        },
        "required": ["evidence"],
    },
    {
        "name": "request_missing_info",
        "description": (
            "The call is asking for information that is NOT in KNOWN FACTS. Ask the "
            "principal for it. Always prefer this over guessing."
        ),
        "properties": {
            "question": {
                "type": "string",
                "description": "The specific question to put to the principal.",
            }
        },
        "required": ["question"],
    },
    {
        "name": "abandon_call",
        "description": (
            "End the call. Use for a dead end, a wrong number, an objective that cannot be "
            "completed by phone, or an explicit refusal."
        ),
        "properties": {"reason": {"type": "string"}},
        "required": ["reason"],
    },
]


def openai_tools() -> list[dict[str, Any]]:
    """Tool schemas in OpenAI function-calling format (what Ollama's /v1 endpoint wants)."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": {
                    "type": "object",
                    "properties": t["properties"],
                    "required": t["required"],
                },
            },
        }
        for t in TOOL_DEFS
    ]


def function_schemas() -> list["FunctionSchema"]:  # noqa: F821
    """Same tools as Pipecat FunctionSchema objects, for the LLM context."""
    from pipecat.adapters.schemas.function_schema import FunctionSchema

    return [
        FunctionSchema(
            name=t["name"],
            description=t["description"],
            properties=t["properties"],
            required=t["required"],
        )
        for t in TOOL_DEFS
    ]
