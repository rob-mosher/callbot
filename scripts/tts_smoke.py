#!/usr/bin/env python3
"""Prove local TTS actually produces audio, through a real pipeline.

Constructing KokoroTTSService succeeds even when it cannot synthesize -- the failure only
appears at synthesis time, which is how a voiceless agent reached a live session once. This
runs the service inside a genuine PipelineTask (which supplies the TaskManager and StartFrame
it needs) and asserts that real audio comes out.

    PYTHONPATH=src .venv/bin/python scripts/tts_smoke.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipecat.frames.frames import EndFrame, Frame, TTSAudioRawFrame, TTSSpeakFrame  # noqa: E402
from pipecat.pipeline.pipeline import Pipeline  # noqa: E402
from pipecat.pipeline.runner import PipelineRunner  # noqa: E402
from pipecat.pipeline.task import PipelineTask  # noqa: E402
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor  # noqa: E402
from pipecat.services.kokoro.tts import KokoroTTSService  # noqa: E402

from callbot.config import settings  # noqa: E402

PHRASE = "Thank you for calling. Please hold while I connect you."


class AudioCounter(FrameProcessor):
    def __init__(self):
        super().__init__()
        self.audio_bytes = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, TTSAudioRawFrame):
            self.audio_bytes += len(frame.audio)
        await self.push_frame(frame, direction)


async def main() -> int:
    tts = KokoroTTSService(settings=KokoroTTSService.Settings(voice=settings.kokoro_voice))
    counter = AudioCounter()
    task = PipelineTask(Pipeline([tts, counter]))
    await task.queue_frames([TTSSpeakFrame(PHRASE), EndFrame()])
    await PipelineRunner(handle_sigint=False).run(task)

    ok = counter.audio_bytes > 0
    secs = counter.audio_bytes / (tts.sample_rate * 2) if tts.sample_rate else 0
    print(f"\n  voice={settings.kokoro_voice} rate={tts.sample_rate}")
    print(f"  audio: {counter.audio_bytes} bytes (~{secs:.1f}s)")
    print(f"  RESULT: {'TTS WORKS' if ok else 'NO AUDIO PRODUCED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
