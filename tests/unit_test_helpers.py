import importlib
import os
import sys

import numpy as np


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ORCHESTRATOR_ROOT = os.path.join(PROJECT_ROOT, "orchestrator")


def add_orchestrator_to_path():
    if ORCHESTRATOR_ROOT not in sys.path:
        sys.path.insert(0, ORCHESTRATOR_ROOT)


class FakeFaissModule:
    class IndexFlatL2:
        def __init__(self, dim):
            self.dim = dim
            self.vectors = np.empty((0, dim), dtype="float32")

        @property
        def ntotal(self):
            return len(self.vectors)

        def add(self, embeddings):
            embeddings = np.asarray(embeddings, dtype="float32")
            if embeddings.ndim != 2 or embeddings.shape[1] != self.dim:
                raise ValueError("embeddings must be a 2D array matching index dim")
            self.vectors = np.vstack([self.vectors, embeddings])

        def search(self, query_embedding, k):
            query_embedding = np.asarray(query_embedding, dtype="float32")
            distances = np.full((query_embedding.shape[0], k), np.inf, dtype="float32")
            indices = np.full((query_embedding.shape[0], k), -1, dtype="int64")

            for row_idx, query in enumerate(query_embedding):
                if self.ntotal == 0:
                    continue
                all_distances = np.sum((self.vectors - query) ** 2, axis=1)
                order = np.argsort(all_distances)[:k]
                distances[row_idx, : len(order)] = all_distances[order]
                indices[row_idx, : len(order)] = order

            return distances, indices


def import_with_fake_faiss(module_name):
    add_orchestrator_to_path()
    sys.modules["faiss"] = FakeFaissModule()
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)
