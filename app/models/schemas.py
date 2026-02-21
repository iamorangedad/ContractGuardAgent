from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum

class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    FAILED = "failed"

class RiskLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

class ContractUpload(BaseModel):
    original_text: str
    modified_text: str
    category: Optional[str] = None

class ContractTask(BaseModel):
    task_id: str
    status: ReviewStatus
    original_text: str
    modified_text: str
    category: Optional[str] = None
    differences: Optional[List[Dict[str, Any]]] = None
    evaluations: Optional[List[Dict[str, Any]]] = None
    human_reviews: Optional[List[Dict[str, Any]]] = None
    final_report: Optional[str] = None
    created_at: Optional[str] = None

class DifferenceItem(BaseModel):
    original_section: str
    modified_section: str
    similarity: float

class EvaluationItem(BaseModel):
    difference: DifferenceItem
    risk_level: RiskLevel
    matched_rule: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None
    explanation: Optional[str] = None

class HumanReviewItem(BaseModel):
    evaluation_id: int
    approved: bool
    modified_suggestion: Optional[str] = None
    comment: Optional[str] = None

class ReviewSubmit(BaseModel):
    task_id: str
    reviews: List[HumanReviewItem]

class TaskStatus(BaseModel):
    task_id: str
    status: ReviewStatus
    message: Optional[str] = None
