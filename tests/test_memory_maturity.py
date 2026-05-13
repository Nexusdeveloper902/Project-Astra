import unittest
import os
import shutil
import yaml
from tests.unit_test_helpers import add_orchestrator_to_path

add_orchestrator_to_path()

from memory.parser import parse_vault
from memory.policy import should_store

class TestMemoryMaturity(unittest.TestCase):
    def setUp(self):
        self.test_vault = "/tmp/astra_test_vault"
        if os.path.exists(self.test_vault):
            shutil.rmtree(self.test_vault)
        os.makedirs(self.test_vault)

    def tearDown(self):
        if os.path.exists(self.test_vault):
            shutil.rmtree(self.test_vault)

    def test_parser_extracts_yaml_frontmatter(self):
        # Create a test memory file with frontmatter
        mem_content = """---
id: mem_test_001
tags: [test, unit]
confidence: 0.8
---

This is a test memory body.
It has multiple paragraphs.

Paragraph 2.
"""
        os.makedirs(os.path.join(self.test_vault, "preferences"))
        with open(os.path.join(self.test_vault, "preferences/mem1.md"), 'w') as f:
            f.write(mem_content)

        docs = parse_vault(self.test_vault)
        self.assertEqual(len(docs), 2) # Two paragraphs
        
        doc = docs[0]
        self.assertEqual(doc["metadata"]["id"], "mem_test_001")
        self.assertEqual(doc["tags"], ["test", "unit"])
        self.assertEqual(doc["category"], "preferences")
        self.assertIn("test memory body", doc["text"])

    def test_memory_policy_heuristics(self):
        intent = {"persistence_policy": "if_useful"}
        
        # Should store stable facts
        self.assertTrue(should_store("User likes Neovim", "preferences", intent))
        
        # Should ignore short transient chatter
        self.assertFalse(should_store("Clicked button", "general", intent))
        
        # Should ignore short logs
        self.assertFalse(should_store("Task done", "logs", intent))
        
        # Should store long logs (summaries)
        long_log = "Completed Task: Install dependencies. Result: Successfully installed 15 packages including requests and PyYAML."
        self.assertTrue(should_store(long_log, "logs", intent))
        
        # Should obey 'never' policy
        self.assertFalse(should_store("Important fact", "facts", {"persistence_policy": "never"}))

if __name__ == "__main__":
    unittest.main()
