import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_config
from app.services.report import build_structured_report

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位专业的法务合同审查专家。你的职责是：
1. 分析合同中的差异条款
2. 评估每项修改的法律风险
3. 提供具体的修改建议

请只返回一个 JSON 对象，不要输出其他文字。字段如下：
- risk_level: green、yellow 或 red
- explanation: 风险说明
- suggestion: 修改建议
- matched_rule: 匹配的规则名称，没有则为 null

green 表示符合标准，yellow 表示需要人工确认，red 表示违反合规要求。"""


class LLMService:
    def __init__(self):
        config = get_config().get("llm", {})
        self.provider = config.get("provider", "ollama")
        self.model = config.get("model", "llama3.2")
        self.temperature = config.get("temperature", 0.1)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.llm = self._build_client()

    def _build_client(self):
        if self.provider == "openai":
            from langchain_openai import ChatOpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is not set")
            return ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                api_key=api_key,
            )

        from langchain_community.chat_models import ChatOllama

        return ChatOllama(
            model=self.model,
            temperature=self.temperature,
            base_url=self.base_url,
        )

    def analyze_contract_difference(
        self,
        original_section: str,
        modified_section: str,
        change_type: str,
        playbook_rules: List[Dict[str, Any]] = None,
        templates: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        rules_text = ""
        if playbook_rules:
            rules_text = "\n参考规则:\n"
            for rule in playbook_rules[:8]:
                rules_text += (
                    f"- {rule.get('rule_name', '')}: {rule.get('description', '')} "
                    f"(风险:{rule.get('risk_level', '')}), 建议:{rule.get('action', '')}\n"
                )

        template_text = ""
        if templates:
            template_text = "\n参考模板:\n"
            for template in templates[:2]:
                snippet = (template.get("content") or "")[:400]
                template_text += f"- {template.get('title', '')}（{template.get('category', '')}）\n{snippet}\n"

        user_prompt = f"""请分析以下合同条款修改：

原始条款:
{original_section}

修改后条款:
{modified_section}

修改类型: {change_type}
{rules_text}
{template_text}

请分析这个修改是否存在风险，并给出评估。"""

        response = self.llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        result = _parse_json_content(response.content)
        risk_level = result.get("risk_level", "yellow")
        if risk_level not in ("green", "yellow", "red"):
            risk_level = "yellow"
        return {
            "risk_level": risk_level,
            "explanation": result.get("explanation") or "需要人工确认",
            "suggestion": result.get("suggestion") or "请人工审核",
            "matched_rule": result.get("matched_rule"),
        }

    def generate_final_report(
        self,
        evaluations: List[Dict[str, Any]],
        human_reviews: List[Dict[str, Any]] = None,
    ) -> str:
        report = build_structured_report(evaluations, human_reviews)
        try:
            summary_prompt = (
                "请根据下面的合同审查报告，用不超过 120 字写一段给法务的综述。"
                "不要重复条目列表。\n\n"
                + report
            )
            response = self.llm.invoke([
                SystemMessage(content="你是法务合同审查专家，只输出综述正文。"),
                HumanMessage(content=summary_prompt),
            ])
            summary = _message_text(response.content).strip()
            if summary:
                report += "\n\n## 模型综述\n" + summary
        except Exception:
            logger.exception("生成模型综述失败，保留结构化报告")
        return report


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def _parse_json_content(content: Any) -> Dict[str, Any]:
    text = _message_text(content).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("模型没有返回 JSON")
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("模型返回的 JSON 不是对象")
    return parsed


llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global llm_service
    if llm_service is None:
        llm_service = LLMService()
    return llm_service
