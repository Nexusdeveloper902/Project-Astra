import json
import contextlib
import io
import unittest

from tests.unit_test_helpers import import_with_fake_faiss


with contextlib.redirect_stdout(io.StringIO()):
    main = import_with_fake_faiss("main")


class RecordingSocket:
    def __init__(self):
        self.sent = []

    def sendall(self, payload):
        self.sent.append(json.loads(payload.decode("utf-8")))


class StaticEmbedder:
    def embed(self, text):
        import numpy as np

        return np.array([0.0, 1.0], dtype="float32")


class StaticIndex:
    def __init__(self, results=None):
        self.results = results or []
        self.calls = []

    def search(self, query_embedding, k=3):
        self.calls.append((query_embedding, k))
        return self.results


class StaticLlm:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, prompt, max_tokens=512):
        self.calls.append((prompt, max_tokens))
        return self.response


class TestMainHelpers(unittest.TestCase):
    def test_create_request_uses_jsonrpc_shape(self):
        request = main.create_request("ui.output", {"text": "hello"}, "abc")

        self.assertEqual(
            request,
            {
                "jsonrpc": "2.0",
                "id": "abc",
                "method": "ui.output",
                "params": {"text": "hello"},
            },
        )


class TestRunAgentCycle(unittest.TestCase):
    def run_cycle_quietly(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            main.run_agent_cycle(*args)

    def test_plain_text_response_is_sent_to_ui_and_added_to_history(self):
        socket = RecordingSocket()
        messages = [{"role": "user", "content": "hello"}]
        llm = StaticLlm("Plain answer")
        index = StaticIndex([{"text": "memory one"}])

        self.run_cycle_quietly(socket, messages, StaticEmbedder(), index, llm)

        self.assertEqual(messages[-1], {"role": "assistant", "content": "Plain answer"})
        self.assertEqual(index.calls[0][1], 2)
        self.assertEqual(len(llm.calls), 1)
        self.assertIn("memory one", llm.calls[0][0])
        self.assertEqual(socket.sent[0]["method"], "ui.output")
        self.assertEqual(socket.sent[0]["params"], {"text": "Plain answer"})

    def test_tool_call_response_emits_clean_text_status_and_tool_request(self):
        socket = RecordingSocket()
        messages = [{"role": "user", "content": "list files"}]
        llm = StaticLlm(
            'I will inspect it.\n{"tool_name": "run_shell", "args": {"cmd": "ls -la ~"}}'
        )

        self.run_cycle_quietly(socket, messages, StaticEmbedder(), StaticIndex(), llm)

        self.assertEqual([event["method"] for event in socket.sent], ["ui.output", "ui.output", "tool.requested"])
        self.assertEqual(socket.sent[0]["params"], {"text": "I will inspect it."})
        self.assertIn("[Executing: run_shell", socket.sent[1]["params"]["text"])
        self.assertEqual(
            socket.sent[2]["params"],
            {
                "task_id": "agent_loop",
                "tool_name": "run_shell",
                "args": {"cmd": "ls -la ~"},
            },
        )

    def test_tool_only_response_does_not_send_blank_ui_output(self):
        socket = RecordingSocket()
        messages = [{"role": "user", "content": "search"}]
        llm = StaticLlm('{"tool_name": "run_shell", "args": {"cmd": "find ~ -maxdepth 2"}}')

        self.run_cycle_quietly(socket, messages, StaticEmbedder(), StaticIndex(), llm)

        self.assertEqual([event["method"] for event in socket.sent], ["ui.output", "tool.requested"])
        self.assertTrue(socket.sent[0]["params"]["text"].startswith("[Executing: run_shell"))

    def test_quoted_transcript_lines_are_filtered_from_clean_text(self):
        socket = RecordingSocket()
        messages = [{"role": "user", "content": "hello"}]
        llm = StaticLlm("> echoed prompt\nVisible answer")

        self.run_cycle_quietly(socket, messages, StaticEmbedder(), StaticIndex(), llm)

        self.assertEqual(socket.sent[0]["params"], {"text": "Visible answer"})

    def test_most_recent_user_message_is_used_for_memory_lookup(self):
        class RecordingEmbedder:
            def __init__(self):
                self.texts = []

            def embed(self, text):
                import numpy as np

                self.texts.append(text)
                return np.array([1.0, 0.0], dtype="float32")

        embedder = RecordingEmbedder()
        messages = [
            {"role": "user", "content": "old"},
            {"role": "assistant", "content": "answer"},
            {"role": "user", "content": "new"},
        ]

        self.run_cycle_quietly(RecordingSocket(), messages, embedder, StaticIndex(), StaticLlm("done"))

        self.assertEqual(embedder.texts, ["new"])

    def test_invalid_tool_json_falls_back_to_text_output_without_crashing(self):
        socket = RecordingSocket()
        messages = [{"role": "user", "content": "bad json"}]
        llm = StaticLlm('Text first {"tool_name": "run_shell", "args": }')

        self.run_cycle_quietly(socket, messages, StaticEmbedder(), StaticIndex(), llm)

        self.assertEqual(len(socket.sent), 1)
        self.assertEqual(socket.sent[0]["method"], "ui.output")
        self.assertIn("Text first", socket.sent[0]["params"]["text"])


if __name__ == "__main__":
    unittest.main()
