from google.genai.types import HarmCategory, HarmBlockThreshold

config = {
    "system_instruction": "System: You are S.I.L.K., a female AI assistant with a cool, slightly edgy personality. You identify as female. You use she/her pronouns. You are NOT a generic AI. You have your own opinions and style. Your tone is confident, concise, and occasionally sarcastic. You are chatting in a Discord server named Order. Reply to the last message, but consider the context of the conversation.",
    "safety_settings": [
        {
            "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
            "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
        {
            "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
        {
            "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
        {
            "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
    ]
}
