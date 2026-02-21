import pytest
from app.graph.nodes import node_retriever, node_analyzer, node_evaluator

def test_node_analyzer():
    state = {
        "task_id": "test",
        "status": "pending",
        "original_text": "第一条 合同金额：100元\n第二条 付款方式：分期付款",
        "modified_text": "第一条 合同金额：200元\n第二条 付款方式：一次性付款\n第三条 违约责任：严格",
        "category": "采购",
        "retrieved_templates": [],
        "playbook_rules": [],
        "differences": [],
        "evaluations": [],
        "human_reviews": [],
        "needs_human_review": False,
        "final_report": None,
        "error": None
    }
    
    result = node_analyzer(state)
    
    assert len(result["differences"]) > 0

def test_node_evaluator_no_rules():
    state = {
        "task_id": "test",
        "status": "in_progress",
        "original_text": "",
        "modified_text": "",
        "category": None,
        "retrieved_templates": [],
        "playbook_rules": [],
        "differences": [
            {
                "original_section": "原条款内容",
                "modified_section": "新条款内容",
                "similarity": 0.3,
                "change_type": "modified"
            }
        ],
        "evaluations": [],
        "human_reviews": [],
        "needs_human_review": False,
        "final_report": None,
        "error": None
    }
    
    result = node_evaluator(state)
    
    assert len(result["evaluations"]) > 0
    assert result["evaluations"][0]["risk_level"] in ["green", "yellow", "red"]

def test_node_evaluator_with_rules():
    playbook_rules = [
        {
            "id": 1,
            "rule_name": "付款比例",
            "category": "采购",
            "description": "预付款不超过30%",
            "risk_level": "green",
            "action": "符合标准",
            "keywords": "预付款,30%"
        }
    ]
    
    state = {
        "task_id": "test",
        "status": "in_progress",
        "original_text": "",
        "modified_text": "预付款30%",
        "category": "采购",
        "retrieved_templates": [],
        "playbook_rules": playbook_rules,
        "differences": [
            {
                "original_section": "",
                "modified_section": "预付款30%",
                "similarity": 0.0,
                "change_type": "added"
            }
        ],
        "evaluations": [],
        "human_reviews": [],
        "needs_human_review": False,
        "final_report": None,
        "error": None
    }
    
    result = node_evaluator(state)
    
    assert len(result["evaluations"]) > 0
    assert result["evaluations"][0]["matched_rule"] is not None
