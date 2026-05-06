import os
from google import genai
from google.genai import types

async def generate_level_up_message(user_name: str, new_level: int, persona_instruction: str = "You are a helpful and encouraging AI assistant.") -> str:
    """
    Generates a personalized, engaging level-up message using google-genai.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return f"🎉 Congratulations {user_name}! You've reached Level {new_level}!"

    try:
        client = genai.Client(api_key=api_key)

        system_instruction = (
            f"{persona_instruction} You are to generate EXACTLY ONE short, hype-filled congratulatory message. "
            "DO NOT provide multiple options. DO NOT provide choices. Output ONLY the final message text and nothing else."
        )

        prompt = (
            f"User '{user_name}' just leveled up to Level {new_level}! "
            "Write a short, engaging, 1-2 sentence congratulatory message. "
            "Do not use emojis if the persona is serious, but do if it's casual."
        )

        response = await client.aio.models.generate_content(
            model='gemma-4-31b-it',
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system_instruction)
        )

        if response.text:
             return response.text.strip()

    except Exception as e:
        print(f"Error generating level up message: {e}")

    return f"🎉 Congratulations {user_name}! You've reached Level {new_level}!"
