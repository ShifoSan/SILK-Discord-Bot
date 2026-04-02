import os
from google import genai
from google.genai import types

def generate_level_up_message(user_name: str, new_level: int, persona_instruction: str = "You are a helpful and encouraging AI assistant.") -> str:
    """
    Generates a personalized, engaging level-up message using google-genai.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return f"🎉 Congratulations {user_name}! You've reached Level {new_level}!"

    try:
        client = genai.Client(api_key=api_key)

        prompt = (
            f"System Instruction: {persona_instruction}\n\n"
            f"User '{user_name}' just leveled up to Level {new_level}! "
            "Write a short, engaging, 1-2 sentence congratulatory message. "
            "Do not use emojis if the persona is serious, but do if it's casual."
        )

        response = client.models.generate_content(
            model='gemma-3-27b-it',
            contents=prompt,
        )

        if response.text:
             return response.text.strip()

    except Exception as e:
        print(f"Error generating level up message: {e}")

    return f"🎉 Congratulations {user_name}! You've reached Level {new_level}!"
