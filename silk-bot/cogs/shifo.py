import discord
from discord import app_commands
from discord.ext import commands
import os
from googleapiclient.discovery import build
import googleapiclient.errors
import asyncio

class Shifo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.channel_id = os.getenv("YOUTUBE_CHANNEL_ID")
        self.youtube = None

        if self.api_key:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize YouTube API client: {e}")
        else:
            print("Warning: YOUTUBE_API_KEY not found in environment variables.")

        if not self.channel_id:
            print("Warning: YOUTUBE_CHANNEL_ID not found in environment variables.")

    @app_commands.command(name="stats", description="Show ShifoLabs channel statistics")
    async def stats(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        if not self.youtube or not self.channel_id:
            await interaction.followup.send("YouTube API is not configured properly.")
            return

        try:
            request = self.youtube.channels().list(
                id=self.channel_id,
                part='statistics,snippet'
            )
            response = await self.bot.loop.run_in_executor(None, request.execute)

            if not response.get('items'):
                await interaction.followup.send("Could not find channel statistics.")
                return

            channel_data = response['items'][0]
            stats = channel_data['statistics']
            snippet = channel_data['snippet']

            embed = discord.Embed(
                title=f"{snippet['title']} Stats",
                color=discord.Color.from_str("#FF2E2E")
            )
            embed.set_thumbnail(url=snippet['thumbnails']['default']['url'])

            sub_count = int(stats['subscriberCount'])
            view_count = int(stats['viewCount'])
            video_count = int(stats['videoCount'])

            embed.add_field(name="Subscribers", value=f"{sub_count:,}", inline=True)
            embed.add_field(name="Total Views", value=f"{view_count:,}", inline=True)
            embed.add_field(name="Videos", value=f"{video_count:,}", inline=True)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"An error occurred while fetching stats: {str(e)}")

    @app_commands.command(name="latest", description="Get the latest ShifoLabs video")
    async def latest(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        if not self.youtube or not self.channel_id:
            await interaction.followup.send("YouTube API is not configured properly.")
            return

        try:
            # Step 1: Get Uploads playlist ID
            channel_request = self.youtube.channels().list(
                id=self.channel_id,
                part='contentDetails'
            )
            channel_response = await self.bot.loop.run_in_executor(None, channel_request.execute)

            if not channel_response.get('items'):
                await interaction.followup.send("Could not find channel info.")
                return

            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

            # Step 2: Get newest video from playlist
            playlist_request = self.youtube.playlistItems().list(
                playlistId=uploads_playlist_id,
                part='snippet',
                maxResults=1
            )
            playlist_response = await self.bot.loop.run_in_executor(None, playlist_request.execute)

            if not playlist_response.get('items'):
                await interaction.followup.send("No videos found in uploads.")
                return

            video_item = playlist_response['items'][0]['snippet']
            video_id = video_item['resourceId']['videoId']
            # title = video_item['title'] # Unused in output but good to have context

            await interaction.followup.send(f"Check out the latest ShifoLabs video! 🎥\nhttps://youtu.be/{video_id}")

        except Exception as e:
            await interaction.followup.send(f"An error occurred while fetching the latest video: {str(e)}")

    @app_commands.command(name="shoutout", description="Promote a YouTube channel")
    @app_commands.describe(channel_handle="The YouTube handle (e.g. @MrBeast)")
    async def shoutout(self, interaction: discord.Interaction, channel_handle: str):
        await interaction.response.defer(thinking=True)

        if not self.youtube:
            await interaction.followup.send("YouTube API is not configured properly.")
            return

        # Input Sanitization
        if not channel_handle.startswith('@'):
            channel_handle = f"@{channel_handle}"

        try:
            # Search for the channel
            search_request = self.youtube.search().list(
                q=channel_handle,
                type='channel',
                part='snippet',
                maxResults=1
            )
            search_response = await self.bot.loop.run_in_executor(None, search_request.execute)

            if not search_response.get('items'):
                await interaction.followup.send(f"Could not find channel with handle `{channel_handle}`.")
                return

            target_channel_id = search_response['items'][0]['snippet']['channelId']

            # Fetch channel stats
            channel_request = self.youtube.channels().list(
                id=target_channel_id,
                part='statistics,snippet'
            )
            channel_response = await self.bot.loop.run_in_executor(None, channel_request.execute)

            if not channel_response.get('items'):
                await interaction.followup.send("Found channel but could not fetch stats.")
                return

            channel_data = channel_response['items'][0]
            stats = channel_data['statistics']
            snippet = channel_data['snippet']

            embed = discord.Embed(
                title=snippet['title'],
                description=snippet['description'][:200] + "..." if len(snippet['description']) > 200 else snippet['description'],
                color=discord.Color.from_str("#FF2E2E"),
                url=f"https://www.youtube.com/channel/{target_channel_id}"
            )
            embed.set_thumbnail(url=snippet['thumbnails']['default']['url'])

            sub_count = int(stats['subscriberCount'])
            embed.add_field(name="Subscribers", value=f"{sub_count:,}", inline=True)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Shifo(bot))
