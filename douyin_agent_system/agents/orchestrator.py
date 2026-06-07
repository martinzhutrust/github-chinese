"""智能体层 — 调度协调器 Orchestrator"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from .analysis_agent import AnalysisAgent
from .ads_agent import AdsAgent
from .base import AgentResult, AgentTask
from .content_agent import ContentAgent
from .livestream_agent import LiveStreamAgent
from .product_agent import ProductAgent
from .qa_agent import QAAgent

logger = logging.getLogger(__name__)

# 任务类型 → Agent 类型映射
TASK_ROUTING: dict[str, str] = {
    "analysis": "analysis_agent",
    "data_insight": "analysis_agent",
    "ads": "ads_agent",
    "ad_optimize": "ads_agent",
    "content": "content_agent",
    "copywriting": "content_agent",
    "script": "content_agent",
    "livestream": "livestream_agent",
    "live": "livestream_agent",
    "product": "product_agent",
    "pricing": "product_agent",
    "inventory": "product_agent",
    "qa": "qa_agent",
    "question": "qa_agent",
    "rule": "qa_agent",
    "policy": "qa_agent",
}


class Orchestrator:
    """
    调度协调器 — 负责：
    1. 任务路由（将任务分发给正确的 Agent）
    2. 上下文共享（所有 Agent 共享感知层快照）
    3. 多 Agent 并发执行
    4. 结果聚合
    5. 冲突仲裁（多 Agent 建议动作冲突时优先级裁决）
    """

    def __init__(self, api_key: str, model: str = "claude-opus-4-8"):
        self._agents: dict[str, Any] = {
            "analysis_agent": AnalysisAgent(api_key, model),
            "ads_agent": AdsAgent(api_key, model),
            "content_agent": ContentAgent(api_key, model),
            "livestream_agent": LiveStreamAgent(api_key, model),
            "product_agent": ProductAgent(api_key, model),
            "qa_agent": QAAgent(api_key, model),
        }

    def route(self, task_type: str) -> str:
        """根据任务类型返回对应 Agent 名称"""
        agent_type = TASK_ROUTING.get(task_type.lower())
        if not agent_type:
            # 默认路由到经营分析
            logger.warning("未知任务类型 %s，路由到 analysis_agent", task_type)
            agent_type = "analysis_agent"
        return agent_type

    async def dispatch(
        self,
        shop_id: str,
        task_type: str,
        instruction: str,
        context: dict[str, Any],
        priority: int = 5,
    ) -> AgentResult:
        """分发单任务到对应 Agent"""
        agent_type = self.route(task_type)
        task = AgentTask(
            task_id=str(uuid.uuid4()),
            agent_type=agent_type,
            shop_id=shop_id,
            instruction=instruction,
            context=context,
            priority=priority,
        )
        agent = self._agents[agent_type]
        return await agent.run(task)

    async def dispatch_multi(
        self,
        shop_id: str,
        tasks: list[dict[str, Any]],
        shared_context: dict[str, Any],
    ) -> list[AgentResult]:
        """
        并发分发多个任务，共享感知层上下文。
        tasks 格式：[{"task_type": "ads", "instruction": "...", "priority": 1}, ...]
        """
        coroutines = [
            self.dispatch(
                shop_id=shop_id,
                task_type=t["task_type"],
                instruction=t["instruction"],
                context={**shared_context, **t.get("extra_context", {})},
                priority=t.get("priority", 5),
            )
            for t in tasks
        ]
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        cleaned: list[AgentResult] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error("任务 %d 执行失败: %s", i, r)
            else:
                cleaned.append(r)
        return cleaned

    def arbitrate_actions(self, results: list[AgentResult]) -> list[dict[str, Any]]:
        """
        冲突仲裁 — 合并多个 Agent 的动作列表，解决冲突：
        - 同一 SKU 的价格调整：取优先级最高的 Agent 的建议
        - 同一投放计划的出价：以投放 Agent 为准
        - 其余动作按优先级排序
        """
        all_actions: list[dict[str, Any]] = []
        for result in results:
            for action in result.actions:
                action["_source_agent"] = result.agent_type
            all_actions.extend(result.actions)

        seen_keys: set[str] = set()
        arbitrated: list[dict[str, Any]] = []

        # 优先级排序（数字越小越优先）
        all_actions.sort(key=lambda a: a.get("priority", 5))

        for action in all_actions:
            conflict_key = self._conflict_key(action)
            if conflict_key and conflict_key in seen_keys:
                logger.info("仲裁跳过冲突动作: %s (已有更高优先级动作)", action.get("action_type"))
                continue
            if conflict_key:
                seen_keys.add(conflict_key)
            arbitrated.append(action)

        return arbitrated

    @staticmethod
    def _conflict_key(action: dict[str, Any]) -> str | None:
        action_type = action.get("action_type", "")
        params = action.get("params", {})
        if action_type == "update_price":
            return f"price_{params.get('sku_id')}"
        if action_type == "adjust_bid":
            return f"bid_{params.get('plan_id')}"
        if action_type == "adjust_budget":
            return f"budget_{params.get('plan_id')}"
        return None
