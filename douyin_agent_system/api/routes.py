"""FastAPI 路由层"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import Settings, get_settings
from perception import IngestionPipeline, DataSourceType
from agents import Orchestrator
from execution.actions import ActionExecutor, ActionRecord
from cognitive.knowledge_base import KnowledgeBase, KnowledgeBaseType
from cognitive.rule_engine import RuleEngine

router = APIRouter(prefix="/api/v1")


# ── 依赖注入 ──────────────────────────────────────────────────
def get_pipeline(settings: Settings = Depends(get_settings)) -> IngestionPipeline:
    return IngestionPipeline(
        laike_api_base=settings.laike_api_base,
        laike_api_key=settings.laike_api_key,
        douyin_app_id=settings.douyin_shop_app_id,
        douyin_app_secret=settings.douyin_shop_app_secret,
    )


def get_orchestrator(settings: Settings = Depends(get_settings)) -> Orchestrator:
    return Orchestrator(api_key=settings.anthropic_api_key, model=settings.claude_model)


def get_executor(settings: Settings = Depends(get_settings)) -> ActionExecutor:
    return ActionExecutor(
        laike_api_base=settings.laike_api_base,
        laike_api_key=settings.laike_api_key,
        dry_run=not settings.laike_api_key,  # 无 key 时自动 dry_run
    )


# ── 请求/响应模型 ─────────────────────────────────────────────
class SnapshotResponse(BaseModel):
    shop_id: str
    data: dict[str, Any]


class AgentRequest(BaseModel):
    shop_id: str
    task_type: str   # analysis / ads / content / livestream / product / qa
    instruction: str
    extra_context: dict[str, Any] = {}


class MultiAgentRequest(BaseModel):
    shop_id: str
    tasks: list[dict[str, Any]]


class KnowledgeQueryRequest(BaseModel):
    kb_type: str
    keywords: list[str] = []
    top_k: int = 5


class RuleEvalRequest(BaseModel):
    context: dict[str, Any]


# ── 路由定义 ──────────────────────────────────────────────────

@router.get("/health")
async def health():
    return {"status": "ok", "service": "抖音来客后台智能体系统"}


# 感知层：获取所有数据快照
@router.get("/shops/{shop_id}/snapshot", response_model=SnapshotResponse)
async def get_snapshot(shop_id: str, pipeline: IngestionPipeline = Depends(get_pipeline)):
    snapshot = await pipeline.fetch_all(shop_id)
    return SnapshotResponse(
        shop_id=shop_id,
        data={k.value: v.payload for k, v in snapshot.items()},
    )


# 感知层：获取单个数据源
@router.get("/shops/{shop_id}/data/{source_type}")
async def get_source_data(
    shop_id: str,
    source_type: str,
    pipeline: IngestionPipeline = Depends(get_pipeline),
):
    try:
        src = DataSourceType(source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"未知数据源类型: {source_type}")
    event = await pipeline.fetch_source(shop_id, src)
    return {"shop_id": shop_id, "source": source_type, "data": event.payload}


# 认知层：知识库查询
@router.post("/knowledge/query")
async def query_knowledge(req: KnowledgeQueryRequest):
    kb = KnowledgeBase()
    try:
        kb_type = KnowledgeBaseType(req.kb_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"未知知识库类型: {req.kb_type}")
    entries = kb.query(kb_type, req.keywords, req.top_k)
    return {
        "kb_type": req.kb_type,
        "results": [{"title": e.title, "content": e.content, "tags": e.tags} for e in entries],
    }


# 认知层：规则引擎评估
@router.post("/rules/evaluate")
async def evaluate_rules(req: RuleEvalRequest):
    engine = RuleEngine()
    matches = engine.evaluate(req.context)
    return {
        "matches": [
            {
                "rule_id": m.rule_id,
                "severity": m.severity,
                "message": m.message,
                "suggested_action": m.suggested_action,
            }
            for m in matches
        ]
    }


# 智能体层：单 Agent 调用
@router.post("/agents/dispatch")
async def dispatch_agent(
    req: AgentRequest,
    pipeline: IngestionPipeline = Depends(get_pipeline),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    snapshot = await pipeline.fetch_all(req.shop_id)
    context = {k.value: v.payload for k, v in snapshot.items()}
    context.update(req.extra_context)
    result = await orchestrator.dispatch(
        shop_id=req.shop_id,
        task_type=req.task_type,
        instruction=req.instruction,
        context=context,
    )
    return {
        "task_id": result.task_id,
        "agent": result.agent_type,
        "success": result.success,
        "analysis": result.analysis,
        "actions": result.actions,
    }


# 智能体层：多 Agent 并发调用
@router.post("/agents/dispatch-multi")
async def dispatch_multi_agents(
    req: MultiAgentRequest,
    pipeline: IngestionPipeline = Depends(get_pipeline),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    executor: ActionExecutor = Depends(get_executor),
):
    snapshot = await pipeline.fetch_all(req.shop_id)
    shared_context = {k.value: v.payload for k, v in snapshot.items()}
    results = await orchestrator.dispatch_multi(req.shop_id, req.tasks, shared_context)
    arbitrated_actions = orchestrator.arbitrate_actions(results)

    # 执行仲裁后的动作
    executed = []
    for action in arbitrated_actions:
        record = ActionRecord(
            action_id=str(uuid.uuid4()),
            action_type=action.get("action_type", ""),
            shop_id=req.shop_id,
            params=action.get("params", {}),
            source_agent=action.get("_source_agent", ""),
        )
        record = await executor.execute(record)
        executed.append({"action_type": record.action_type, "status": record.status, "result": record.result})

    return {
        "shop_id": req.shop_id,
        "agents_executed": len(results),
        "actions_arbitrated": len(arbitrated_actions),
        "execution_results": executed,
        "agent_analyses": [
            {"agent": r.agent_type, "success": r.success, "summary": r.analysis[:300]}
            for r in results
        ],
    }


# 执行层：手动触发单个动作
@router.post("/actions/execute")
async def execute_action(
    shop_id: str,
    action_type: str,
    params: dict[str, Any],
    executor: ActionExecutor = Depends(get_executor),
):
    record = ActionRecord(
        action_id=str(uuid.uuid4()),
        action_type=action_type,
        shop_id=shop_id,
        params=params,
        source_agent="manual",
    )
    record = await executor.execute(record)
    return {"action_id": record.action_id, "status": record.status, "result": record.result}
