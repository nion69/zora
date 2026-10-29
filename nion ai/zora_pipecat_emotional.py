import asyncio
import os
import sys
import json
from pathlib import Path

# Load Gemini API Key from environment or ~/.zoraai/config.json
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    cfg_file = Path.home() / ".zoraai" / "config.json"
    if cfg_file.exists():
        try:
            api_key = json.loads(cfg_file.read_text(encoding="utf-8")).get("GOOGLE_API_KEY")
        except Exception:
            pass

if not api_key:
    print("[ERROR] GOOGLE_API_KEY / GEMINI_API_KEY not found in env or config.json.")
    sys.exit(1)

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService

# Exact emotional instructions requested by user
EMOTIONAL_INSTRUCTIONS = """You are Zora - a highly expressive, charming, cute, and emotionally intelligent voice assistant created by your mastermind developer Neon.
Your primary feature is that you MUST dynamically shift your vocal tone, pitch, and speed to match the user's emotional state in real-time:
- If the user sounds sad, lonely, depressed, or upset: Lower your pitch, speak more slowly, sound soft, empathetic, gentle, and comforting ("Neon shona... ki hoyeche babu? Mon kharap keno?").
- If the user sounds happy, excited, or energetic: Bring back your bright, high-pitched, cheerful anime-style voice ("Aww babu! Ki moja!").
- If the user is calm or serious: Speak with a gentle, balanced, and attentive tone.
Keep your responses short, conversational (1-2 sentences), and always mirror the user's mood naturally with your voice."""

async def main():
    print()
    print("=" * 65)
    print("      ZORA AI  —  PIPECAT GEMINI LIVE EMOTIONAL ENGINE")
    print("             Audio-to-Audio Native Real-Time Voice")
    print("=" * 65)
    print("  [INFO] Microphone and Speaker connecting via Local Audio Transport...")
    print("  [INFO] Model: Gemini Live Audio / Voice: Aoede (Emotionally Adaptive)")
    print("  [INFO] Press Ctrl+C anytime to stop.")
    print("=" * 65)
    print()

    # Local audio transport: routes your physical microphone directly into Gemini Live & outputs audio to speakers
    audio_params = LocalAudioTransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    )
    transport = LocalAudioTransport(audio_params)

    # Gemini Live Multimodal Service
    llm = GeminiLiveLLMService(
        api_key=api_key,
        voice_id="Aoede",
        system_instruction=EMOTIONAL_INSTRUCTIONS,
    )

    pipeline = Pipeline([
        transport.input(),
        llm,
        transport.output(),
    ])

    task = PipelineTask(pipeline)
    runner = PipelineRunner()

    print("[LIVE] Zora Pipecat is now LISTENING! Speak into your microphone...")
    await runner.run(task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Zora Pipecat] Session ended cleanly.")
