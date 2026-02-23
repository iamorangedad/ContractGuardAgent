from typing import TypedDict, List, Dict, Any, Optional

class ContractReviewState(TypedDict):
    task_id: str
    status: str
    original_text: str
    modified_text: str
    category: Optional[str]
    
    retrieved_templates: List[Dict[str, Any]]
    playbook_rules: List[Dict[str, Any]]
    
    differences: List[Dict[str, Any]]
    evaluations: List[Dict[str, Any]]
    
    human_reviews: List[Dict[str, Any]]
    needs_human_review: bool
    
    final_report: Optional[str]
    error: Optional[str]
    
    review_round: int
    max_review_rounds: int
    continue_review: bool
