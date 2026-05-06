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
