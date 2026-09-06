#!/usr/bin/env python3
"""Phase 0 harness: talk to the agent through your browser, no telephony.

You play the phone tree out loud; the agent decides. Every tool call is logged, so you can
watch it pick digits, wait through a menu, refuse to invent an ID, or declare a human.

    PYTHONPATH=src .venv/bin/python scripts/console_bot.py
    # then open http://localhost:7860

Uses the same callbot.bot pipeline the Daily PSTN bot will use, so what you tune here is
what ships. Browser mic via WebRTC deliberately avoids portaudio and terminal mic
permissions on macOS.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from loguru import logger  # noqa: E402
from pipecat.pipeline.runner import PipelineRunner  # noqa: E402
from pipecat.runner.types import RunnerArguments, SmallWebRTCRunnerArguments  # noqa: E402
from pipecat.transports.base_transport import TransportParams  # noqa: E402
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport  # noqa: E402

from callbot.bot import build_task, default_vad  # noqa: E402
from callbot.config import settings  # noqa: E402

# Edit these to rehearse a different call.
OBJECTIVE = os.getenv(
    "CALLBOT_OBJECTIVE",
    "Cancel the dental insurance policy, and get written confirmation of the cancellation date.",
)
FACTS = {
    "full_name": settings.principal_name,
    "callback_number": "555-0142",
}


async def bot(runner_args: RunnerArguments):
    """Entry point discovered by the Pipecat runner."""
    if not isinstance(runner_args, SmallWebRTCRunnerArguments):
        raise RuntimeError("console_bot is WebRTC-only; run it with the default runner.")

    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=default_vad(),
        ),
    )

    logger.info(f"objective: {OBJECTIVE}")
    logger.info(f"known facts: {list(FACTS)}")
    logger.info("speak a phone menu at it -- tool calls are logged below")

    task = build_task(
        transport,
        objective=OBJECTIVE,
        facts=FACTS,
        greeting="[The call has just connected. You hear the line open.]",
    )

    @transport.event_handler("on_client_connected")
    async def _on_connected(_transport, _client):
        logger.info("client connected -- agent is listening")

    @transport.event_handler("on_client_disconnected")
    async def _on_disconnected(_transport, _client):
        logger.info("client disconnected")
        await task.cancel()

    await PipelineRunner(handle_sigint=runner_args.handle_sigint).run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
