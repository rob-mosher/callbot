"""Pipeline assembly, shared by every transport.

The transport is injected rather than constructed here, so the console harness
(SmallWebRTC, browser mic) and the eventual Daily PSTN bot run the identical brain.
Anything tuned here is tuned for both.
"""

import time
from collections.abc import Callable, Mapping
from typing import Any

from loguru import logger
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.ollama.llm import OLLamaLLMService

from callbot.config import settings
from callbot.guards import check_bridge_timing, check_press_digits
from callbot.prompts import build_system_prompt
from callbot.tools import function_schemas

# Actions the agent can take that the caller must react to (dial the principal, hang up).
ActionSink = Callable[[str, dict[str, Any]], Any]


def _register_handlers(
    llm: OLLamaLLMService, facts: Mapping[str, str], emit: ActionSink, started_at: float
) -> None:
    """Wire tool handlers. Every handler reports back to the model via result_callback.

    press_digits is the only guarded one: a rejection is returned as a normal tool result so
    the model self-corrects on the next turn instead of the call dying.
    """

    async def press_digits(params: FunctionCallParams):
        digits = str(params.arguments.get("digits", ""))
        verdict = check_press_digits(digits, facts)
        if not verdict.ok:
            logger.warning(f"[guard] rejected press_digits({digits!r}): {verdict.reason}")
            await params.result_callback({"status": "rejected", "reason": verdict.reason})
            return
        logger.info(f"[dtmf] {digits}")
        emit("press_digits", {"digits": digits})
        await params.result_callback({"status": "sent", "digits": digits})

    async def wait_and_listen(params: FunctionCallParams):
        secs = params.arguments.get("seconds", 5)
        logger.info(f"[wait] {secs}s")
        await params.result_callback({"status": "waiting", "seconds": secs})

    async def human_reached(params: FunctionCallParams):
        evidence = params.arguments.get("evidence", "")
        timing = check_bridge_timing(time.monotonic() - started_at, settings.min_seconds_before_bridge)
        if not timing.ok:
            logger.warning(f"[guard] rejected human_reached: {timing.reason}")
            await params.result_callback({"status": "rejected", "reason": timing.reason})
            return
        logger.success(f"[human reached] {evidence}")
        emit("human_reached", {"evidence": evidence})
        await params.result_callback(
            {"status": "bridging", "instruction": "Tell them briefly to hold while you connect."}
        )

    async def request_missing_info(params: FunctionCallParams):
        question = params.arguments.get("question", "")
        logger.warning(f"[needs info] {question}")
        emit("request_missing_info", {"question": question})
        await params.result_callback(
            {"status": "asking", "instruction": "Ask the other party to hold for a moment."}
        )

    async def abandon_call(params: FunctionCallParams):
        reason = params.arguments.get("reason", "")
        logger.error(f"[abandon] {reason}")
        emit("abandon_call", {"reason": reason})
        await params.result_callback({"status": "ending"})

    for name, fn in (
        ("press_digits", press_digits),
        ("wait_and_listen", wait_and_listen),
        ("human_reached", human_reached),
        ("request_missing_info", request_missing_info),
        ("abandon_call", abandon_call),
    ):
        llm.register_function(name, fn)


def build_task(
    transport,
    *,
    objective: str,
    facts: Mapping[str, str],
    emit: ActionSink | None = None,
    greeting: str | None = None,
) -> PipelineTask:
    """Assemble the STT -> LLM -> TTS pipeline against a ready transport."""
    emit = emit or (lambda action, data: logger.debug(f"[action] {action} {data}"))

    stt = DeepgramSTTService(api_key=settings.deepgram_api_key)
    tts = KokoroTTSService(settings=KokoroTTSService.Settings(voice=settings.kokoro_voice))
    llm = OLLamaLLMService(
        base_url=settings.ollama_base_url,
        # Temperature 0 matches the conditions scripts/ivr_eval.py validates under.
        # Diverging here would make the eval stop predicting live behavior.
        settings=OLLamaLLMService.Settings(model=settings.ollama_model, temperature=0.0),
    )
    _register_handlers(llm, facts, emit, time.monotonic())

    system = build_system_prompt(
        objective=objective,
        facts=facts,
        bot_name=settings.bot_name,
        principal_name=settings.principal_name,
    )
    messages: list[Any] = [{"role": "system", "content": system}]
    if greeting:
        messages.append({"role": "user", "content": greeting})

    context = LLMContext(messages, ToolsSchema(standard_tools=function_schemas()))
    aggregators = LLMContextAggregatorPair(context)

    pipeline = Pipeline([
        transport.input(),
        stt,
        aggregators.user(),
        llm,
        tts,
        transport.output(),
        aggregators.assistant(),
    ])

    return PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True),
        idle_timeout_secs=settings.max_call_seconds,
    )


def default_vad() -> SileroVADAnalyzer:
    return SileroVADAnalyzer()
