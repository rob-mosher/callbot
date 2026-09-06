# callbot

An agent that places a phone call on your behalf, navigates the phone tree, and bridges you
in once a real human is on the line.

- **LLM:** Ollama, self-hosted — local or elsewhere on your subnet, set via `OLLAMA_BASE_URL`.
  Reasoning never leaves your network.
- **STT:** Deepgram (cloud) — accuracy on 8 kHz phone audio is the binding constraint
- **TTS:** Kokoro (local ONNX)
- **Telephony:** Daily PSTN — native `send_dtmf()`, and two dial-out legs in one room *is* the bridge

## Status

| Phase | State |
|---|---|
| 0 — Brain, no telephony | scaffold, prompts, tools, guards, eval **done**; console bot remaining |
| 1 — Daily plumbing | blocked on Daily dial-out enablement + number purchase |
| 2 — Bridge | not started |
| 3 — Missing-info side channel | not started |
| 4 — Wrap-up / summary | not started |

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in DEEPGRAM_API_KEY, DAILY_*, PRINCIPAL_NUMBER
```

## Verify

```bash
PYTHONPATH=src .venv/bin/python scripts/ivr_eval.py          # IVR decision regression suite
PYTHONPATH=src .venv/bin/python scripts/ivr_eval.py qwen3:8b # compare another model
.venv/bin/python -m pytest tests/ -q                         # guard unit tests
```

`ivr_eval.py` replays IVR transcript snippets against the **real** shipped prompt and tool
schemas and asserts the correct decision across three seeds. Run it on every prompt or model
change — it is the only thing standing between a prompt tweak and a bot that fabricates a
member ID on a live call.

Current: **36/36** on `llama3.1:8b`.

## Collaborators

Contributions to this project — human and AI — are recorded in
[COLLABORATORS.md](COLLABORATORS.md) and in `Collaborator:` commit footers, following the
[Collaborators Framework](https://github.com/rob-mosher/collaborators-framework).

## How safety is enforced

Two layers, because one is not enough at 8B:

1. **Rule Zero** at the top of the system prompt — every identifier the bot speaks must appear
   verbatim in `KNOWN FACTS`. Position matters: buried mid-prompt, this rule failed 0/3.
2. **`guards.check_press_digits`** — code-level validation that rejects non-DTMF junk and any
   sequence longer than a menu selection that isn't grounded in `KNOWN FACTS`. Rejections are
   returned to the model as a tool result so it self-corrects mid-call instead of dying.

`KNOWN FACTS` is a disclosure allowlist, not a convenience: it bounds what the bot *can* say
about you, no matter what the person on the other end asks.

## License

MIT — see [LICENSE](LICENSE).
