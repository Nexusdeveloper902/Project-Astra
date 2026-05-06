import faiss
import numpy as np

class MemoryIndex:
    def __init__(self, dim=768):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.metadata = []
        
    def add(self, embeddings, metadatas):
        self.index.add(embeddings)
        self.metadata.extend(metadatas)
        
    def search(self, query_embedding, k=3):
        if self.index.ntotal == 0:
            return []
            
        query_embedding = query_embedding.reshape(1, -1)
        distances, indices = self.index.search(query_embedding, k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1:
                res = self.metadata[idx].copy()
                res["distance"] = float(dist)
                results.append(res)
        return results
