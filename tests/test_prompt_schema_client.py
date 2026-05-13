import json
import contextlib
import io
import unittest
from unittest.mock import Mock, patch

from tests.unit_test_helpers import add_orchestrator_to_path


add_orchestrator_to_path()

from llm.client import LlamaClient, route_task
from llm.prompt import SYSTEM_CORE_INSTRUCTION, construct_prompt
from tools.schema import ToolRegistry, ToolSchema, registry


class TestPromptConstruction(unittest.TestCase):
    def test_construct_prompt_includes_system_instruction_context_and_assistant_trigger(self):
        prompt = construct_prompt(
            messages=[{"role": "user", "content": "Find my notes"}],
            active_context={"cwd": "/tmp/astra", "user": "tester"},
            memory_retrievals=["remember this", "and that"],
            tools=[{"name": "run_shell", "danger_tier": "medium"}],
            task_state={"status": "processing"},
        )

        self.assertTrue(prompt.startswith(SYSTEM_CORE_INSTRUCTION))
        self.assertIn("[Available Tools]", prompt)
        self.assertIn('"cwd": "/tmp/astra"', prompt)
        self.assertIn("[Relevant Memories]", prompt)
        self.assertIn("- remember this", prompt)
        self.assertIn("- and that", prompt)
        self.assertIn('"status": "processing"', prompt)
        self.assertTrue(prompt.endswith("<|im_start|>assistant"))

    def test_construct_prompt_preserves_message_order_and_roles(self):
        messages = [
            {"role": "user", "content": "one"},
            {"role": "assistant", "content": "two"},
            {"role": "system", "content": "three"},
        ]

        prompt = construct_prompt(messages, {}, [], [], {})

        self.assertLess(prompt.index("<|im_start|>user\none"), prompt.index("<|im_start|>assistant\ntwo"))
        self.assertLess(prompt.index("<|im_start|>assistant\ntwo"), prompt.index("<|im_start|>system\nthree"))

    def test_system_instruction_contains_safety_and_search_guidelines(self):
        self.assertIn("SEARCH WITHOUT PERMISSION", SYSTEM_CORE_INSTRUCTION)
        self.assertIn("HIDDEN FILE BLACKLIST", SYSTEM_CORE_INSTRUCTION)
        self.assertIn("MANDATORY CONFIRMATION", SYSTEM_CORE_INSTRUCTION)
        self.assertIn("UNIVERSAL VERIFICATION", SYSTEM_CORE_INSTRUCTION)
        self.assertIn("SEARCH RESILIENCE", SYSTEM_CORE_INSTRUCTION)
        self.assertIn("RENAMING WITH EXIFTOOL", SYSTEM_CORE_INSTRUCTION)

    def test_tools_are_serialized_as_json_in_prompt(self):
        tools = [{"name": "save_memory", "input_schema": {"content": "string"}}]

        prompt = construct_prompt([], {}, [], tools, {})

        pretty_tools = json.dumps(tools, indent=2)
        self.assertIn(pretty_tools, prompt)


class TestToolSchemaAndRegistry(unittest.TestCase):
    def test_tool_schema_to_dict_contains_all_fields(self):
        schema = ToolSchema(
            name="example",
            description="Does a thing",
            input_schema={"x": "string"},
            output_schema={"ok": "bool"},
            danger_tier="high",
        )

        self.assertEqual(
            schema.to_dict(),
            {
                "name": "example",
                "description": "Does a thing",
                "input_schema": {"x": "string"},
                "output_schema": {"ok": "bool"},
                "danger_tier": "high",
            },
        )

    def test_tool_schema_defaults_to_low_danger(self):
        schema = ToolSchema("safe", "Safe tool", {}, {})

        self.assertEqual(schema.to_dict()["danger_tier"], "low")

    def test_registry_replaces_tools_by_name(self):
        registry_under_test = ToolRegistry()
        registry_under_test.register(ToolSchema("duplicate", "old", {}, {}))
        registry_under_test.register(ToolSchema("duplicate", "new", {"x": "string"}, {}))

        tools = registry_under_test.get_all_tools()

        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["description"], "new")
        self.assertEqual(tools[0]["input_schema"], {"x": "string"})

    def test_default_registry_contains_base_tools(self):
        tools = {tool["name"]: tool for tool in registry.get_all_tools()}

        self.assertIn("run_shell", tools)
        self.assertIn("save_memory", tools)
        self.assertEqual(tools["run_shell"]["danger_tier"], "medium")
        self.assertEqual(tools["save_memory"]["danger_tier"], "low")


class TestLlamaClient(unittest.TestCase):
    def test_generate_posts_completion_request_and_strips_text(self):
        response = Mock()
        response.json.return_value = {"choices": [{"text": "  hello\n"}]}
        response.raise_for_status.return_value = None

        with patch("llm.client.requests.post", return_value=response) as post:
            result = LlamaClient("http://model.test/v1").generate("prompt", max_tokens=17)

        self.assertEqual(result, "hello")
        post.assert_called_once_with(
            "http://model.test/v1/completions",
            json={
                "prompt": "prompt",
                "max_tokens": 17,
                "temperature": 0.7,
                "stop": ["<|im_end|>", "<|endoftext|>"],
            },
            timeout=30,
        )

    def test_generate_returns_error_string_when_request_fails(self):
        with patch("llm.client.requests.post", side_effect=RuntimeError("boom")):
            with contextlib.redirect_stdout(io.StringIO()):
                result = LlamaClient("http://model.test/v1").generate("prompt")

        self.assertEqual(result, "Error calling LLM.")

    def test_generate_returns_error_string_when_response_shape_is_unexpected(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"choices": []}

        with patch("llm.client.requests.post", return_value=response):
            with contextlib.redirect_stdout(io.StringIO()):
                result = LlamaClient("http://model.test/v1").generate("prompt")

        self.assertEqual(result, "Error calling LLM.")

    def test_route_task_returns_default_http_client(self):
        with contextlib.redirect_stdout(io.StringIO()):
            client = route_task("general")

        self.assertIsInstance(client, LlamaClient)
        self.assertEqual(client.server_url, "http://localhost:8080/v1")


if __name__ == "__main__":
    unittest.main()
