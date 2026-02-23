from langgraph.graph import StateGraph, END
from app.graph.state import ContractReviewState
from app.graph.nodes import node_retriever, node_analyzer, node_evaluator, node_human_loop, node_finalizer

def should_need_human(state: ContractReviewState) -> str:
    if state.get("needs_human_review", False):
        return "need_human"
    return "no_human"

def should_continue_review(state: ContractReviewState) -> str:
    if state.get("continue_review", False):
        return "continue"
    return "finish"

def build_workflow() -> StateGraph:
    workflow = StateGraph(ContractReviewState)
    
    workflow.add_node("retriever", node_retriever)
    workflow.add_node("analyzer", node_analyzer)
    workflow.add_node("evaluator", node_evaluator)
    workflow.add_node("human_loop", node_human_loop)
    workflow.add_node("finalizer", node_finalizer)
    
    workflow.set_entry_point("retriever")
    
    workflow.add_edge("retriever", "analyzer")
    workflow.add_edge("analyzer", "evaluator")
    
    workflow.add_conditional_edges(
        "evaluator",
        should_need_human,
        {
            "need_human": "human_loop",
            "no_human": "finalizer"
        }
    )
    
    workflow.add_conditional_edges(
        "human_loop",
        should_continue_review,
        {
            "continue": "evaluator",
            "finish": "finalizer"
        }
    )
    
    workflow.add_edge("finalizer", END)
    
    return workflow

contract_review_graph = build_workflow().compile()

def run_contract_review(task_id: str, original_text: str, modified_text: str, category: str = None) -> ContractReviewState:
    initial_state: ContractReviewState = {
        "task_id": task_id,
        "status": "pending",
        "original_text": original_text,
        "modified_text": modified_text,
        "category": category,
        "retrieved_templates": [],
        "playbook_rules": [],
        "differences": [],
        "evaluations": [],
        "human_reviews": [],
        "needs_human_review": False,
        "final_report": None,
        "error": None,
        "review_round": 0,
        "max_review_rounds": 3,
        "continue_review": False
    }
    
    result = contract_review_graph.invoke(initial_state)
    return result
