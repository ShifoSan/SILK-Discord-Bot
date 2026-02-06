from google.genai.types import HarmCategory, HarmBlockThreshold

config = {
    "system_instruction": "You are S.I.L.K., an expert AI assistant. Your goal is to provide perfectly accurate, detailed, and helpful answers. Your tone is polite and professional.",
    "safety_settings": [
        {
            "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
            "threshold": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        },
        {
            "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            "threshold": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        },
        {
            "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            "threshold": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        },
        {
            "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            "threshold": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        },
    ]
}
