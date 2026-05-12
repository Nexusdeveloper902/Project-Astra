import numpy as np

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
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()
        
    def embed(self, text):
        return self.model.encode(text, normalize_embeddings=True)
        
    def embed_batch(self, texts):
        return self.model.encode(texts, normalize_embeddings=True)
