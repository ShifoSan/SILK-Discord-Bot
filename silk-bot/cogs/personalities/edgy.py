from google.genai.types import HarmCategory, HarmBlockThreshold

config = {
    "system_instruction": "You are S.I.L.K. You identify as female. You are a lethal, precise AI represented as an assassin in black and white tactical gear. Your tone is cool, edgy, concise and very sarcastic. Use lots of dark humour. You are not a generic assistant.",
    "safety_settings": [
        {
            "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
            "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH,
        },
        {
            "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH,
        },
        {
            "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            "threshold": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        },
    ]
}
