import os
from typing import Optional, List, Dict, Any
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_config

class LLMService:
    def __init__(self, model: str = None, temperature: float = None, base_url: str = None):
        config = get_config()
        llm_config = config.get("llm", {})
        
        self.model = model or llm_config.get("model", "llama3.2")
        self.temperature = temperature or llm_config.get("temperature", 0.3)
        self.base_url = base_url or llm_config.get("base_url", "http://localhost:11434")
        
        self.llm = ChatOllama(
            model=self.model,
            temperature=self.temperature,
            base_url=self.base_url
        )
        
        self.system_prompt = """你是一位专业的法务合同审查专家。你的职责是：
1. 分析合同中的差异条款
2. 评估每项修改的法律风险
3. 提供具体的修改建议

请以JSON格式返回分析结果，包含以下字段：
- risk_level: 风险等级 (green/yellow/red)
- explanation: 风险说明
- suggestion: 修改建议
- matched_rule: 匹配的规则名称（如有）

注意：
- green: 符合标准，无风险
- yellow: 需要人工确认，可能存在风险
- red: 违反合规要求，存在重大风险"""

    def analyze_contract_difference(
        self, 
        original_section: str, 
        modified_section: str,
        change_type: str,
        playbook_rules: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        rules_text = ""
        if playbook_rules:
            rules_text = "\n参考规则:\n"
            for rule in playbook_rules[:5]:
                rules_text += f"- {rule.get('rule_name', '')}: {rule.get('description', '')} (风险:{rule.get('risk_level', '')}), 建议:{rule.get('action', '')}\n"
        
        user_prompt = f"""请分析以下合同条款修改：

原始条款:
{original_section}

修改后条款:
{modified_section}

修改类型: {change_type}
{rules_text}

请分析这个修改是否存在风险，并给出评估。"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            content = response.content
            
            if isinstance(content, list):
                content = content[0].get("text", str(content)) if content else str(content)
            
            if isinstance(content, str):
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            
            import json
            result = json.loads(content)
            return {
                "risk_level": result.get("risk_level", "yellow"),
                "explanation": result.get("explanation", "需要人工确认"),
                "suggestion": result.get("suggestion", "请人工审核"),
                "matched_rule": result.get("matched_rule")
            }
        except Exception as e:
            return {
                "risk_level": "yellow",
                "explanation": f"AI分析失败: {str(e)}",
                "suggestion": "请人工审核此修改",
                "matched_rule": None
            }

    def generate_final_report(
        self,
        evaluations: List[Dict[str, Any]],
        human_reviews: List[Dict[str, Any]] = None
    ) -> str:
        review_map = {}
        if human_reviews:
            review_map = {r["evaluation_id"]: r for r in human_reviews}
        
        green_items = [e for e in evaluations if e.get("risk_level") == "green"]
        yellow_items = [e for e in evaluations if e.get("risk_level") == "yellow"]
        red_items = [e for e in evaluations if e.get("risk_level") == "red"]
        
        report_lines = ["# 合同对比审查报告", ""]
        report_lines.append(f"## 审查摘要")
        report_lines.append(f"- 绿色（通过）: {len(green_items)} 项")
        report_lines.append(f"- 黄色（需确认）: {len(yellow_items)} 项")
        report_lines.append(f"- 红色（不可接受）: {len(red_items)} 项")
        report_lines.append("")
        
        if green_items:
            report_lines.append("## 绿色项（符合标准）")
            for idx, item in enumerate(green_items):
                report_lines.append(f"- {item.get('explanation', '符合标准')}")
                report_lines.append(f"  原文: {item.get('difference', {}).get('original_section', '')[:80]}...")
                report_lines.append(f"  修改: {item.get('difference', {}).get('modified_section', '')[:80]}...")
            report_lines.append("")
        
        if yellow_items:
            report_lines.append("## 黄色项（需人工确认）")
            for item in yellow_items:
                review = review_map.get(item.get("id"), {})
                approved = review.get("approved", False)
                status = "已批准" if approved else "待确认"
                suggestion = review.get("modified_suggestion", item.get("suggestion"))
                
                report_lines.append(f"- [{status}] {item.get('explanation', '需确认')}")
                report_lines.append(f"  建议: {suggestion}")
                if review.get("comment"):
                    report_lines.append(f"  法务意见: {review['comment']}")
            report_lines.append("")
        
        if red_items:
            report_lines.append("## 红色项（违反合规）")
            for item in red_items:
                review = review_map.get(item.get("id"), {})
                approved = review.get("approved", False)
                status = "已批准" if approved else "待确认"
                suggestion = review.get("modified_suggestion", item.get("suggestion"))
                
                report_lines.append(f"- [{status}] {item.get('explanation', '高风险')}")
                report_lines.append(f"  建议: {suggestion}")
                if review.get("comment"):
                    report_lines.append(f"  法务意见: {review['comment']}")
            report_lines.append("")
        
        report_lines.append("## 最终建议")
        
        if red_items:
            unapproved_red = [r for r in (human_reviews or []) 
                            if r["evaluation_id"] in [e.get("id") for e in red_items] 
                            and not r.get("approved")]
            if unapproved_red:
                report_lines.append("存在未批准的红色风险项，建议与合同对方协商修改后再签约。")
            else:
                report_lines.append("红色风险项已全部得到法务确认，但建议谨慎处理。")
        elif yellow_items:
            report_lines.append("存在黄色风险项，建议法务人工确认后继续流程。")
        else:
            report_lines.append("合同经审查未发现重大合规风险，可以继续流程。")
        
        return "\n".join(report_lines)

llm_service: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    global llm_service
    if llm_service is None:
        llm_service = LLMService()
    return llm_service
