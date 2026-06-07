"""智能体层 — Agent 基类"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import anthropic
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AgentTask(BaseModel):
    task_id: str
    agent_type: str
    shop_id: str
    instruction: str                         # 自然语言指令
    context: dict[str, Any]                 # 感知层快照 + 规则匹配结果
    priority: int = 5                        # 1(最高) ~ 10(最低)


class AgentResult(BaseModel):
    task_id: str
    agent_type: str
    success: bool
    analysis: str                            # Agent 的分析/建议
    actions: list[dict[str, Any]]           # 建议执行的动作
    raw_response: str = ""


class BaseAgent(ABC):
    """所有 Agent 的基类，封装 Claude API 调用"""

    agent_type: str
    system_prompt: str

    def __init__(self, api_key: str, model: str = "claude-opus-4-8", max_tokens: int = 4096):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def run(self, task: AgentTask) -> AgentResult:
        user_message = self._build_user_message(task)
        logger.info("[%s] 开始处理任务 %s", self.agent_type, task.task_id)
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=self.system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            raw = response.content[0].text
            actions = self._extract_actions(raw, task)
            return AgentResult(
                task_id=task.task_id,
                agent_type=self.agent_type,
                success=True,
                analysis=raw,
                actions=actions,
                raw_response=raw,
            )
        except Exception as exc:
            logger.exception("[%s] 任务 %s 失败: %s", self.agent_type, task.task_id, exc)
            return AgentResult(
                task_id=task.task_id,
                agent_type=self.agent_type,
                success=False,
                analysis=f"Agent 执行异常: {exc}",
                actions=[],
            )

    def _build_user_message(self, task: AgentTask) -> str:
        context_str = self._format_context(task.context)
        return (
            f"## 商家 ID: {task.shop_id}\n\n"
            f"## 当前数据快照\n{context_str}\n\n"
            f"## 任务指令\n{task.instruction}"
        )

    @staticmethod
    def _format_context(ctx: dict[str, Any]) -> str:
        import json
        return json.dumps(ctx, ensure_ascii=False, indent=2)

    @abstractmethod
    def _extract_actions(self, response_text: str, task: AgentTask) -> list[dict[str, Any]]:
        """从 Claude 响应中解析出结构化动作列表"""
        ...
