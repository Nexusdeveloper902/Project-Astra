import os
import tempfile
import unittest

import numpy as np

from tests.unit_test_helpers import add_orchestrator_to_path, import_with_fake_faiss


add_orchestrator_to_path()

from memory.embedder import DummyEmbedder
from memory.parser import parse_vault


class TestParseVault(unittest.TestCase):
    def test_parse_vault_returns_one_document_per_non_empty_markdown_chunk(self):
        with tempfile.TemporaryDirectory() as vault:
            note_path = os.path.join(vault, "note.md")
            with open(note_path, "w", encoding="utf-8") as handle:
                handle.write("First paragraph\n\n\nSecond paragraph\n\n  \nThird")

            docs = parse_vault(vault)

        self.assertEqual([doc["text"] for doc in docs], ["First paragraph", "Second paragraph", "Third"])
        self.assertEqual([doc["id"] for doc in docs], [f"{note_path}_0", f"{note_path}_1", f"{note_path}_2"])
        self.assertTrue(all(doc["source"] == note_path for doc in docs))
        self.assertTrue(all(doc["tags"] == [] for doc in docs))

    def test_parse_vault_recurses_into_nested_markdown_files(self):
        with tempfile.TemporaryDirectory() as vault:
            nested = os.path.join(vault, "nested", "deeper")
            os.makedirs(nested)
            top_path = os.path.join(vault, "top.md")
            nested_path = os.path.join(nested, "nested.md")
            ignored_path = os.path.join(nested, "ignored.txt")

            for path, content in ((top_path, "top"), (nested_path, "nested"), (ignored_path, "ignored")):
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)

            docs = parse_vault(vault)

        self.assertEqual({doc["text"] for doc in docs}, {"top", "nested"})
        self.assertEqual({doc["source"] for doc in docs}, {top_path, nested_path})

    def test_parse_vault_returns_empty_list_for_empty_or_missing_vault(self):
        with tempfile.TemporaryDirectory() as vault:
            self.assertEqual(parse_vault(vault), [])
        self.assertEqual(parse_vault(os.path.join(tempfile.gettempdir(), "does-not-exist-astra")), [])


class TestDummyEmbedder(unittest.TestCase):
    def test_embed_returns_float32_unit_vector_with_configured_dimension(self):
        vector = DummyEmbedder(dim=16).embed("hello")

        self.assertEqual(vector.shape, (16,))
        self.assertEqual(vector.dtype, np.float32)
        self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=5)

    def test_embed_is_deterministic_for_same_text_within_process(self):
        embedder = DummyEmbedder(dim=12)

        first = embedder.embed("same input")
        second = embedder.embed("same input")

        np.testing.assert_array_equal(first, second)

    def test_embed_batch_stacks_vectors_in_input_order(self):
        embedder = DummyEmbedder(dim=8)
        texts = ["alpha", "beta", "gamma"]

        batch = embedder.embed_batch(texts)

        self.assertEqual(batch.shape, (3, 8))
        np.testing.assert_array_equal(batch[0], embedder.embed("alpha"))
        np.testing.assert_array_equal(batch[1], embedder.embed("beta"))
        np.testing.assert_array_equal(batch[2], embedder.embed("gamma"))


class TestMemoryIndex(unittest.TestCase):
    def setUp(self):
        self.index_module = import_with_fake_faiss("memory.index")

    def test_search_empty_index_returns_empty_list(self):
        index = self.index_module.MemoryIndex(dim=2)

        self.assertEqual(index.search(np.array([1.0, 0.0], dtype="float32")), [])

    def test_search_returns_nearest_metadata_with_float_distance(self):
        index = self.index_module.MemoryIndex(dim=2)
        embeddings = np.array([[0.0, 0.0], [10.0, 10.0], [1.0, 1.0]], dtype="float32")
        metadatas = [{"text": "origin"}, {"text": "far"}, {"text": "near"}]

        index.add(embeddings, metadatas)
        results = index.search(np.array([0.5, 0.5], dtype="float32"), k=2)

        self.assertEqual([result["text"] for result in results], ["origin", "near"])
        self.assertTrue(all(isinstance(result["distance"], float) for result in results))

    def test_search_does_not_mutate_original_metadata(self):
        index = self.index_module.MemoryIndex(dim=2)
        metadata = {"text": "stored"}

        index.add(np.array([[0.0, 0.0]], dtype="float32"), [metadata])
        result = index.search(np.array([0.0, 0.0], dtype="float32"), k=1)[0]

        self.assertEqual(result["distance"], 0.0)
        self.assertNotIn("distance", metadata)

    def test_search_with_k_larger_than_index_size_returns_available_results(self):
        index = self.index_module.MemoryIndex(dim=2)
        index.add(np.array([[3.0, 4.0]], dtype="float32"), [{"text": "only"}])

        results = index.search(np.array([3.0, 4.0], dtype="float32"), k=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "only")


if __name__ == "__main__":
    unittest.main()
