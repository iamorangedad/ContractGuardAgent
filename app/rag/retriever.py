import logging

from app.config import get_config
from app.rag.db import search_templates, search_playbook, get_all_playbook_rules
from app.services.embeddings import get_embeddings_service, cosine_similarity

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self):
        self._embeddings_service = None
        self._rule_vectors = {}

    @property
    def use_embeddings(self) -> bool:
        return bool(get_config().get("embeddings", {}).get("use_embeddings", False))
    
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
                rule_embedding = self._embed_rule(rule)
                similarity = cosine_similarity(query_embedding, rule_embedding)
                scored_rules.append((similarity, rule))
            
            scored_rules.sort(key=lambda x: x[0], reverse=True)
            return [rule for _, rule in scored_rules[:top_k]]
        except Exception:
            logger.exception("语义检索失败，改用全文检索")
            return self.retrieve_playbook(query, category, top_k)
    
    def _embed_rule(self, rule: dict) -> list:
        rule_id = rule.get("id")
        cached = self._rule_vectors.get(rule_id)
        if cached is not None:
            return cached
        rule_text = f"{rule.get('rule_name', '')} {rule.get('description', '')}"
        vector = self.embeddings_service.embed_text(rule_text)
        if rule_id is not None:
            self._rule_vectors[rule_id] = vector
        return vector

    def retrieve_for_contract(self, contract_text: str, category: str = None) -> dict:
        templates = self.retrieve_templates(contract_text[:500], top_k=2)
        playbook_rules = self._rules_for_category(category)

        if not playbook_rules:
            if self.use_embeddings:
                playbook_rules = self.semantic_search_playbook(contract_text[:500], category, top_k=10)
            else:
                playbook_rules = self.retrieve_playbook(contract_text[:500], category, top_k=10)
        elif self.use_embeddings and self.embeddings_service:
            playbook_rules = self._rerank(contract_text[:500], playbook_rules)

        return {
            "templates": templates,
            "playbook_rules": playbook_rules
        }

    def _rules_for_category(self, category: str = None) -> list:
        rules = []
        seen = set()
        for name in [category, "通用"]:
            if not name:
                continue
            for rule in get_all_playbook_rules(name):
                rule_id = rule.get("id")
                if rule_id in seen:
                    continue
                seen.add(rule_id)
                rules.append(rule)
        return rules

    def _rerank(self, query: str, rules: list) -> list:
        try:
            query_embedding = self.embeddings_service.embed_text(query)
            scored = []
            for rule in rules:
                similarity = cosine_similarity(query_embedding, self._embed_rule(rule))
                scored.append((similarity, rule))
            scored.sort(key=lambda item: item[0], reverse=True)
            return [rule for _, rule in scored]
        except Exception:
            logger.exception("规则重排序失败，保留原顺序")
            return rules

retriever = Retriever()
