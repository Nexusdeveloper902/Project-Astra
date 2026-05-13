import unittest
from unittest.mock import Mock, patch
import json
from tests.unit_test_helpers import add_orchestrator_to_path

add_orchestrator_to_path()

# We'll mock the LLM client to return a tool call
from llm.client import LlamaClient
import main as orchestrator_main

class TestMemoryCategorizationLLM(unittest.TestCase):
    @patch("main.emit_event")
    @patch("llm.client.LlamaClient.generate")
    def test_agent_categorizes_preference_memory(self, mock_generate, mock_emit):
        # Setup: LLM returns a tool call for a preference
        mock_generate.return_value = """I'll remember that.
TOOL_CALL_START
{
  "tool_name": "save_memory",
  "args": {
    "content": "User prefers Neovim for coding",
    "category": "preferences",
    "tags": ["editor", "neovim"]
  }
}
TOOL_CALL_END
"""
        # Orchestrator state
        s = Mock()
        messages = [{"role": "user", "content": "I prefer using Neovim for coding."}]
        embedder = Mock()
        embedder.embed.return_value = [0.1] * 384
        index = Mock()
        index.search.return_value = []
        llm_client = LlamaClient()
        
        # Run cycle
        orchestrator_main.run_agent_cycle(s, messages, embedder, index, llm_client, "test_task")
        
        # Verify save_memory was emitted with correct category
        found_save = False
        for call in mock_emit.call_args_list:
            method = call.args[1]
            params = call.args[2]
            if method == "tool.requested" and params.get("tool_name") == "save_memory":
                self.assertEqual(params["args"]["category"], "preferences")
                self.assertIn("neovim", params["args"]["tags"])
                found_save = True
                break
        
        self.assertTrue(found_save, "save_memory tool request not found in emitted events")

if __name__ == "__main__":
    unittest.main()
