import os
import numpy as np
from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings

class EmbeddingsService:
    def __init__(self, model: str = "text-embedding-3-small"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        
        self.embeddings = OpenAIEmbeddings(
            model=model,
            api_key=api_key
        )
    
    def embed_text(self, text: str) -> List[float]:
        return self.embeddings.embed_query(text)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embeddings.embed_documents(texts)
    
    def compute_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

embeddings_service: Optional[EmbeddingsService] = None

def get_embeddings_service() -> EmbeddingsService:
    global embeddings_service
    if embeddings_service is None:
        try:
            embeddings_service = EmbeddingsService()
        except Exception as e:
            return None
    return embeddings_service

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8))
