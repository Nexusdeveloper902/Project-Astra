import numpy as np
import os

class DummyEmbedder:
    def __init__(self, dim=768):
        self.dim = dim
        
    def embed(self, text):
        np.random.seed(abs(hash(text)) % (2**32))
        vec = np.random.randn(self.dim).astype('float32')
        vec = vec / np.linalg.norm(vec)
        return vec
        
    def embed_batch(self, texts):
        return np.vstack([self.embed(t) for t in texts])

class RealEmbedder:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        # Ensure model is cached locally in the project directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(base_dir, "models", "embeddings")
        os.makedirs(cache_dir, exist_ok=True)
        
        self.model = SentenceTransformer(model_name, cache_folder=cache_dir)
        self.dim = self.model.get_embedding_dimension()
        
    def embed(self, text):
        return self.model.encode(text, normalize_embeddings=True)
        
    def embed_batch(self, texts):
        return self.model.encode(texts, normalize_embeddings=True)
