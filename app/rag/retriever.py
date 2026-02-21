from app.rag.db import search_templates, search_playbook, get_all_playbook_rules
from app.services.embeddings import get_embeddings_service, cosine_similarity
import os

class Retriever:
    def __init__(self):
        self.use_embeddings = os.getenv("USE_EMBEDDINGS", "false").lower() == "true"
        self._embeddings_service = None
    
    @property
    def embeddings_service(self):
        if self.use_embeddings and self._embeddings_service is None:
            self._embeddings_service = get_embeddings_service()
        return self._embeddings_service
    
    def retrieve_templates(self, query: str, top_k: int = 3) -> list:
        return search_templates(query, top_k)
    
    def retrieve_playbook(self, query: str, category: str = None, top_k: int = 5) -> list:
        return search_playbook(query, category, top_k)
    
    def get_all_rules(self, category: str = None) -> list:
        return get_all_playbook_rules(category)
    
    def semantic_search_playbook(
        self, 
        query: str, 
        category: str = None, 
        top_k: int = 5
    ) -> list:
        if not self.use_embeddings or not self.embeddings_service:
            return self.retrieve_playbook(query, category, top_k)
        
        try:
            playbook_rules = get_all_playbook_rules(category)
            if not playbook_rules:
                return []
            
            query_embedding = self.embeddings_service.embed_text(query)
            
            scored_rules = []
            for rule in playbook_rules:
                rule_text = f"{rule.get('rule_name', '')} {rule.get('description', '')}"
                rule_embedding = self.embeddings_service.embed_text(rule_text)
                similarity = cosine_similarity(query_embedding, rule_embedding)
                scored_rules.append((similarity, rule))
            
            scored_rules.sort(key=lambda x: x[0], reverse=True)
            return [rule for _, rule in scored_rules[:top_k]]
        except Exception:
            return self.retrieve_playbook(query, category, top_k)
    
    def retrieve_for_contract(self, contract_text: str, category: str = None) -> dict:
        templates = self.retrieve_templates(contract_text[:500], top_k=2)
        
        if self.use_embeddings:
            playbook_rules = self.semantic_search_playbook(contract_text[:500], category, top_k=10)
        else:
            playbook_rules = self.retrieve_playbook(contract_text[:500], category, top_k=10)
        
        return {
            "templates": templates,
            "playbook_rules": playbook_rules
        }

retriever = Retriever()
