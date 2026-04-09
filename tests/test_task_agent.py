import sys
from unittest.mock import MagicMock

# 1. Define real classes for dependencies that TaskAgent's classes inherit from
class MockCog: pass
class MockView: pass

# 2. Mock all dependencies before importing TaskAgent
discord = MagicMock()
discord.ui = MagicMock()
discord.ui.View = MockView
sys.modules["discord"] = discord

discord_ext = MagicMock()
discord_ext.commands = MagicMock()
discord_ext.commands.Cog = MockCog
sys.modules["discord.ext"] = discord_ext
sys.modules["discord.ext.commands"] = discord_ext.commands

google = MagicMock()
sys.modules["google"] = google
sys.modules["google.genai"] = google.genai

# Ensure a fresh import if it was already imported as a Mock
if "cogs.task_agent" in sys.modules:
    del sys.modules["cogs.task_agent"]

import pytest
# 3. Import TaskAgent from the actual source
from cogs.task_agent import TaskAgent

class TestTaskAgentExtractJson:
    """
    Test cases for TaskAgent.extract_json_from_markdown.
    The method is tested as an unbound method by passing None as 'self'
    since it is a pure string manipulation function.
    """

    def test_extract_json_with_json_label(self):
        text = "Here is the result:\n```json\n{\"key\": \"value\"}\n```"
        expected = "{\"key\": \"value\"}"
        assert TaskAgent.extract_json_from_markdown(None, text) == expected

    def test_extract_json_without_label(self):
        text = "```\n{\"key\": \"value\"}\n```"
        expected = "{\"key\": \"value\"}"
        assert TaskAgent.extract_json_from_markdown(None, text) == expected

    def test_extract_json_case_insensitive(self):
        text = "```JSON\n{\"key\": \"value\"}\n```"
        expected = "{\"key\": \"value\"}"
        assert TaskAgent.extract_json_from_markdown(None, text) == expected

    def test_extract_json_no_markdown(self):
        text = "{\"key\": \"value\"}"
        expected = "{\"key\": \"value\"}"
        assert TaskAgent.extract_json_from_markdown(None, text) == expected

    def test_extract_json_with_surrounding_text(self):
        text = "Intro text\n```json\n{\"key\": \"value\"}\n```\nOutro text"
        expected = "{\"key\": \"value\"}"
        assert TaskAgent.extract_json_from_markdown(None, text) == expected

    def test_extract_json_empty_input(self):
        text = ""
        expected = ""
        assert TaskAgent.extract_json_from_markdown(None, text) == expected

    def test_extract_json_multiple_blocks(self):
        # re.search finds the first one (non-greedy matching)
        text = "```json\n{\"first\": 1}\n```\n```json\n{\"second\": 2}\n```"
        expected = "{\"first\": 1}"
        assert TaskAgent.extract_json_from_markdown(None, text) == expected

    def test_extract_json_with_whitespace(self):
        text = "  ```json  \n  {\"key\": \"value\"}  \n  ```  "
        expected = "{\"key\": \"value\"}"
        assert TaskAgent.extract_json_from_markdown(None, text) == expected
