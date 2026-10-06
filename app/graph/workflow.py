import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from app.graph.nodes import (
    node_analyzer,
    node_evaluator,
    node_finalizer,
    node_human_loop,
    node_retriever,
)
from app.graph.state import ContractReviewState
from app.rag.db import get_db_path

_graph = None
_connection = None


def should_need_human(state: ContractReviewState) -> str:
    if state.get("needs_human_review", False):
        return "need_human"
    return "no_human"


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
            "no_human": "finalizer",
        },
    )
    workflow.add_edge("human_loop", "finalizer")
    workflow.add_edge("finalizer", END)
    return workflow


def get_graph():
    global _graph, _connection
    if _graph is None:
        checkpoint_path = Path(get_db_path()).parent / "graph_checkpoints.sqlite"
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(str(checkpoint_path), check_same_thread=False)
        saver = SqliteSaver(_connection)
        saver.setup()
        _graph = build_workflow().compile(checkpointer=saver)
    return _graph


def reset_graph():
    """关闭检查点连接，下次调用会按当前数据库路径重新打开。"""
    global _graph, _connection
    _graph = None
    if _connection is not None:
        _connection.close()
        _connection = None


def _thread_config(task_id: str) -> dict:
    return {"configurable": {"thread_id": task_id}}


def _result_from_snapshot(snapshot) -> dict:
    values = snapshot.values or {}
    interrupted = bool(snapshot.next) or bool(snapshot.interrupts)
    status = "waiting_human" if interrupted else values.get("status") or "completed"
    return {
        "status": status,
        "differences": values.get("differences", []),
        "evaluations": values.get("evaluations", []),
        "human_reviews": values.get("human_reviews", []),
        "final_report": values.get("final_report"),
        "error": values.get("error"),
    }


def run_contract_review(task_id: str, original_text: str, modified_text: str, category: str = None) -> dict:
    graph = get_graph()
    graph.checkpointer.delete_thread(task_id)
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
        "max_review_rounds": 1,
        "continue_review": False,
    }
    config = _thread_config(task_id)
    graph.invoke(initial_state, config)
    return _result_from_snapshot(graph.get_state(config))


def resume_contract_review(task_id: str, reviews: list) -> dict:
    graph = get_graph()
    config = _thread_config(task_id)
    snapshot = graph.get_state(config)
    if not snapshot.next and not snapshot.interrupts:
        raise ValueError("任务没有停在人工审核节点")
    graph.invoke(Command(resume=reviews), config)
    return _result_from_snapshot(graph.get_state(config))
