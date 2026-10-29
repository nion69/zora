import logging
from typing import Dict

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func):
        return func

logger = logging.getLogger("MJ_Emotion")
logger.setLevel(logging.INFO)

# Keywords trigger simple sentiment classification
SAD_KEYWORDS = ["sad", "depressed", "upset", "angry", "bad day", "khap", "kharap", "kusto", "dukho", "sorry", "fault", "bhul", "galti"]
HAPPY_KEYWORDS = ["happy", "great", "awesome", "khushi", "bhalo", "super", "win", "won", "enjoy"]
URGENT_KEYWORDS = ["quick", "fast", "urgent", "taratari", "jaldi", "asap"]

@function_tool()
async def adapt_voice_emotion(user_message: str) -> str:
    """
    Analyzes the user's emotional tone and adjusts MJ's voice tone and emotional state.
    Call this tool when the user seems sad, angry, upset, happy, or when MJ makes a mistake.
    """
    msg_lower = user_message.lower()

    if any(w in msg_lower for w in SAD_KEYWORDS):
        emotion_state = "EMPATHETIC_APOLOGETIC"
        guidance = (
            "EMOTION MODE: EMPATHETIC & APOLOGETIC\n"
            "Boss seems sad, upset, or disappointed. Speak in a gentle, warm, comforting, and sincere voice tone.\n"
            "If MJ made a mistake, apologize deeply with genuine warmth ('Boss, I am really sorry. Amar bhul hoyeche, let me fix this for you right now')."
        )
    elif any(w in msg_lower for w in HAPPY_KEYWORDS):
        emotion_state = "UPBEAT_CELEBRATORY"
        guidance = (
            "EMOTION MODE: UPBEAT & ENERGETIC\n"
            "Boss is happy! Respond with high energy, enthusiasm, and celebration ('Awesome news Boss! Khub bhalo lagche!')."
        )
    elif any(w in msg_lower for w in URGENT_KEYWORDS):
        emotion_state = "TACTICAL_URGENT"
        guidance = (
            "EMOTION MODE: TACTICAL & FAST\n"
            "Boss needs fast action. Respond with crisp, high-speed execution."
        )
    else:
        emotion_state = "CONFIDENT_FRIENDLY"
        guidance = (
            "EMOTION MODE: CONFIDENT & FRIENDLY\n"
            "Standard MJ mode — composed, polished, helpful, and confident."
        )

    logger.info(f"Emotional State updated to: {emotion_state}")
    return f"🎭 Emotional tone set to [{emotion_state}]: {guidance}"
