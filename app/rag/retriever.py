from app.rag.db import search_templates, search_playbook, get_all_playbook_rules

class Retriever:
    def __init__(self):
        pass
    
    def retrieve_templates(self, query: str, top_k: int = 3) -> list:
        return search_templates(query, top_k)
    
    def retrieve_playbook(self, query: str, category: str = None, top_k: int = 5) -> list:
        return search_playbook(query, category, top_k)
    
    def get_all_rules(self, category: str = None) -> list:
        return get_all_playbook_rules(category)
    
    def retrieve_for_contract(self, contract_text: str, category: str = None) -> dict:
        templates = self.retrieve_templates(contract_text[:500], top_k=2)
        playbook_rules = self.retrieve_playbook(contract_text[:500], category, top_k=10)
        
        return {
            "templates": templates,
            "playbook_rules": playbook_rules
        }

retriever = Retriever()
