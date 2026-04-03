import os
import asyncio
import datetime
from typing import List, Dict, Optional

import discord
from discord.ext import commands, tasks
from motor.motor_asyncio import AsyncIOMotorClient
from google import genai
from google.genai import types

class Memory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Initialize MongoDB
        mongo_uri = os.getenv("MONGO_URI")
        if mongo_uri:
            # Similar to the level system database setup
            self.mongo_client = AsyncIOMotorClient(mongo_uri)
            self.db = self.mongo_client['silk_db']
            self.collection = self.db['user_memories']
        else:
            print("Warning: MONGO_URI not found. Memory module will not function.")
            self.mongo_client = None
            self.collection = None

        # Initialize GenAI client
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            print("Warning: GEMINI_API_KEY not found. Memory module will not function.")
            self.client = None

        # Tracking processed message IDs to avoid duplicates without clearing the queues
        # Format: {channel_id_or_user_id: last_processed_message_id}
        self.last_processed_message_ids: Dict[int, int] = {}

        # Start the background task
        if self.collection is not None and self.client is not None:
            self.memory_extractor_task.start()

    def cog_unload(self):
        self.memory_extractor_task.cancel()

    @tasks.loop(minutes=10)
    async def memory_extractor_task(self):
        """
        Background task that runs every 10 minutes to extract facts from recent conversations.
        """
        await self.bot.wait_until_ready()

        # Dictionaries to collect messages per user
        user_conversations: Dict[int, List[str]] = {}

        # 1. Server Chat Cog Queue
        chat_cog = self.bot.get_cog("Chat")
        if chat_cog:
            # Assuming the chat cog has a dictionary of deques for server chats as instructed
            # such as chat_cog.server_history or similar.
            chat_queues = getattr(chat_cog, 'server_history', getattr(chat_cog, 'chat_history', getattr(chat_cog, 'reply_history', {})))
            if isinstance(chat_queues, dict):
                for channel_id, queue in chat_queues.items():
                    for msg in queue:
                        # Extract ID
                        msg_id = getattr(msg, 'id', None)
                        if msg_id is None and isinstance(msg, dict):
                            msg_id = msg.get('id')

                        # If we successfully got an ID and it's newer than our last processed
                        if msg_id is not None:
                            last_id = self.last_processed_message_ids.get(channel_id, 0)
                            if msg_id > last_id:
                                uid = getattr(msg, 'author', None)
                                uid = uid.id if uid else msg.get('author_id')

                                if uid and getattr(msg, 'content', None):
                                    if uid not in user_conversations:
                                        user_conversations[uid] = []
                                    user_conversations[uid].append(f"[User]: {msg.content}")

                                self.last_processed_message_ids[channel_id] = max(self.last_processed_message_ids.get(channel_id, 0), msg_id)
                        else:
                            # Fallback if no ID is present (e.g., if the deque stores plain strings)
                            # To avoid duplication bug, we attempt to extract a pseudo ID or just ignore.
                            pass

        # 2. DM Chat Cog Queue
        # Handle the requested 'DMGatekeeper' cog name, falling back to 'DMChat' if needed.
        dm_cog = self.bot.get_cog("DMGatekeeper") or self.bot.get_cog("DMChat")
        if dm_cog:
            dm_queues = getattr(dm_cog, 'dm_history', {})
            for user_id, queue in dm_queues.items():
                for msg in queue:
                    msg_id = getattr(msg, 'id', None)
                    if msg_id is None and isinstance(msg, dict):
                        msg_id = msg.get('id')

                    # Some implementations might just store strings in the deque and append an ID logic later.
                    # If we find an ID, we process it:
                    if msg_id is not None:
                        last_id = self.last_processed_message_ids.get(user_id, 0)
                        if msg_id > last_id:
                            if user_id not in user_conversations:
                                user_conversations[user_id] = []

                            content = getattr(msg, 'content', None) or msg.get('content', str(msg))
                            user_conversations[user_id].append(content)

                            self.last_processed_message_ids[user_id] = max(self.last_processed_message_ids.get(user_id, 0), msg_id)
                    elif isinstance(msg, str):
                        # Extreme fallback if deque contains just strings without IDs and the system relies on it
                        # The instructions say "only process messages that are newer than that ID".
                        # If we have strings, we can't do that safely without IDs.
                        pass

        # Process queued conversations per user
        for uid, msgs in user_conversations.items():
            if msgs:
                conv_text = "\n".join(msgs)
                await self._process_user_facts(uid, conv_text)

    async def _process_user_facts(self, user_id: int, conversation_text: str):
        """
        Extracts facts from a conversation text and saves them to MongoDB.
        """

        system_instruction = (
            "You are an AI assistant designed to extract significant facts, preferences, or plans from a user's conversation. "
            "Analyze the following conversation and extract any clear, long-term facts about the user (e.g., 'User is learning Python', 'User lives in Tokyo', 'User loves pizza', 'User is planning to buy a car in December'). "
            "Return EACH fact on a new line. Do NOT use bullet points or any other formatting. "
            "If there are NO significant facts, return an empty string. "
            "Ensure the facts are stated clearly and concisely."
        )

        try:
            # 1. Extraction using gemini-3.1-flash-lite-preview
            # Use native async method for google-genai
            response = await self.client.aio.models.generate_content(
                model='gemini-3.1-flash-lite-preview',
                contents=f"{system_instruction}\n\nConversation:\n{conversation_text}"
            )

            if response.text:
                facts = [fact.strip() for fact in response.text.split('\n') if fact.strip() and not fact.isspace()]

                for fact in facts:
                    # 2. Embedding using gemini-embedding-2-preview
                    # Output is a 768-dimensional float array
                    embedding_response = await self.client.aio.models.embed_content(
                        model='gemini-embedding-2-preview',
                        contents=fact
                    )

                    embedding_vector = embedding_response.embeddings[0].values

                    # 3. Save to MongoDB
                    doc = {
                        "user_id": str(user_id),
                        "memory_text": fact,
                        "embedding": embedding_vector,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc)
                    }
                    await self.collection.insert_one(doc)

        except Exception as e:
            print(f"Error extracting/saving memory for user {user_id}: {e}")

    async def get_user_memories(self, user_id: str, current_query: str) -> List[str]:
        """
        Asynchronously retrieves the most relevant memories for a user based on the current query.

        Requires an Atlas Vector Search index named 'vector_index' on the 'embedding' field
        with 768 dimensions.
        """
        if not self.client or not self.collection:
            return []

        try:
            # 1. Generate embedding for current query
            embedding_response = await self.client.aio.models.embed_content(
                model='gemini-embedding-2-preview',
                contents=current_query
            )
            query_vector = embedding_response.embeddings[0].values

            # 2. Run MongoDB $vectorSearch
            # NOTE: For this to work, you MUST create a vector search index in MongoDB Atlas UI.
            # Index Name: 'vector_index'
            # Configuration (JSON):
            # {
            #   "fields": [
            #     {
            #       "numDimensions": 768,
            #       "path": "embedding",
            #       "similarity": "cosine",
            #       "type": "vector"
            #     },
            #     {
            #       "path": "user_id",
            #       "type": "filter"
            #     }
            #   ]
            # }
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_vector,
                        "numCandidates": 50,
                        "limit": 5,
                        "filter": {"user_id": str(user_id)}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "memory_text": 1,
                        "timestamp": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]

            cursor = self.collection.aggregate(pipeline)
            results = await cursor.to_list(length=5)

            # 3. Format results
            formatted_memories = []
            for doc in results:
                # e.g., '[March 2026: User is making a Minecraft mod]'
                ts: datetime.datetime = doc['timestamp']
                date_str = ts.strftime("%B %Y")
                memory_str = doc['memory_text']
                formatted_memories.append(f"[{date_str}: {memory_str}]")

            return formatted_memories

        except Exception as e:
            print(f"Error retrieving memories for user {user_id}: {e}")
            return []

async def setup(bot):
    await bot.add_cog(Memory(bot))
