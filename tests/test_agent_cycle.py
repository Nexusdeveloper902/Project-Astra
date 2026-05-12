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
        if isinstance(response, str):
            self.responses = [response]
        else:
            self.responses = list(response)
        self.calls = []
        self.default_params = {"temperature": 0.7, "max_tokens": 512}
    def generate(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]

class TestMainHelpers(unittest.TestCase):
    def test_create_request_uses_jsonrpc_shape(self):
        request = main.create_request("ui.output", {"text": "hello"}, "abc")
        self.assertEqual(request, {
            "jsonrpc": "2.0",
            "id": "abc",
            "method": "ui.output",
            "params": {"text": "hello"},
        })

class TestRunAgentCycle(unittest.TestCase):
    def setUp(self):
        self.original_route_task = main.route_task
        self.llm = None
        main.route_task = self.mock_route_task

    def tearDown(self):
        main.route_task = self.original_route_task

    def mock_route_task(self, task_type):
        return self.llm

    def run_cycle_quietly(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            main.run_agent_cycle(*args)

    def test_plain_text_response_is_sent_to_ui_and_added_to_history(self):
        socket = RecordingSocket()
        messages = [{"role": "user", "content": "hello"}]
        self.llm = StaticLlm(["intent", "Plain answer"])
        index = StaticIndex([{"text": "memory one"}])

        self.run_cycle_quietly(socket, messages, StaticEmbedder(), index, self.llm)

        self.assertEqual(messages[-1], {"role": "assistant", "content": "Plain answer"})
        
        methods = [event["method"] for event in socket.sent]
        self.assertEqual(methods, [
            "task.updated", "intent.contracted", "task.updated", 
            "memory.retrieved", "task.updated", "execution.context_captured", 
            "ui.output", "task.completed"
        ])
        self.assertEqual(socket.sent[6]["params"]["text"], "Plain answer")

    def test_tool_call_response_emits_clean_text_status_and_tool_request(self):
        socket = RecordingSocket()
        messages = [{"role": "user", "content": "list files"}]
        self.llm = StaticLlm(["intent", 'I will inspect it.\nTOOL_CALL_START\n{"tool_name": "run_shell", "args": {"cmd": "ls -la ~"}}\nTOOL_CALL_END'])

        self.run_cycle_quietly(socket, messages, StaticEmbedder(), StaticIndex(), self.llm)

        methods = [event["method"] for event in socket.sent]
        self.assertEqual(methods, [
            "task.updated", "intent.contracted", "task.updated", 
            "memory.retrieved", "task.updated", "execution.context_captured", 
            "ui.output", "ui.output", "tool.requested"
        ])
        self.assertEqual(socket.sent[6]["params"]["text"], "I will inspect it.")
        self.assertIn("[Executing: run_shell", socket.sent[7]["params"]["text"])

    def test_tool_only_response_does_not_send_blank_ui_output(self):
        socket = RecordingSocket()
        messages = [{"role": "user", "content": "search"}]
        self.llm = StaticLlm(["intent", 'TOOL_CALL_START\n{"tool_name": "run_shell", "args": {"cmd": "find ~ -maxdepth 2"}}\nTOOL_CALL_END'])

        self.run_cycle_quietly(socket, messages, StaticEmbedder(), StaticIndex(), self.llm)

        methods = [event["method"] for event in socket.sent]
        self.assertEqual(methods, [
            "task.updated", "intent.contracted", "task.updated", 
            "memory.retrieved", "task.updated", "execution.context_captured", 
            "ui.output", "tool.requested"
        ])

    def test_quoted_transcript_lines_are_filtered_from_clean_text(self):
        socket = RecordingSocket()
        messages = [{"role": "user", "content": "hello"}]
        self.llm = StaticLlm(["intent", "> echoed prompt\nVisible answer"])

        self.run_cycle_quietly(socket, messages, StaticEmbedder(), StaticIndex(), self.llm)

        ui_output = next(event for event in socket.sent if event["method"] == "ui.output")
        self.assertEqual(ui_output["params"]["text"], "Visible answer")

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
        self.llm = StaticLlm(["intent", "done"])

        self.run_cycle_quietly(RecordingSocket(), messages, embedder, StaticIndex(), self.llm)
        self.assertEqual(embedder.texts, ["new"])

    def test_invalid_tool_json_falls_back_to_text_output_without_crashing(self):
        socket = RecordingSocket()
        messages = [{"role": "user", "content": "bad json"}]
        self.llm = StaticLlm(["intent 1", 'Text first {"tool_name": "run_shell", "args": }', "intent 2", 'Valid retry without tool'])

        self.run_cycle_quietly(socket, messages, StaticEmbedder(), StaticIndex(), self.llm)

        methods = [event["method"] for event in socket.sent]
        self.assertEqual(methods[:8], [
            "task.updated", "intent.contracted", "task.updated", "memory.retrieved", 
            "task.updated", "execution.context_captured", "ui.output", "tool.rejected"
        ])
        self.assertIn("Text first", socket.sent[6]["params"]["text"])

if __name__ == "__main__":
    unittest.main()
