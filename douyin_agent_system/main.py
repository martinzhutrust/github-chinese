"""抖音来客后台智能体系统 — 主入口"""
from __future__ import annotations

import asyncio
import logging
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from api.routes import router
from perception import IngestionPipeline
from agents import Orchestrator
from execution.scheduler import Scheduler, register_default_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="抖音来客后台四层智能体协作系统（感知层 / 认知层 / 智能体层 / 执行层）",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup():
    logger.info("🚀 %s v%s 启动中...", settings.app_name, settings.app_version)
    logger.info("模型: %s", settings.claude_model)
    if not settings.anthropic_api_key:
        logger.warning("⚠️  ANTHROPIC_API_KEY 未配置，Agent 调用将失败")


# ── CLI 演示模式 ──────────────────────────────────────────────
async def demo(shop_id: str = "shop_demo_001"):
    """直接运行 main.py 时执行演示流程"""
    logger.info("=" * 60)
    logger.info("📦 演示模式启动 | 商家: %s", shop_id)
    logger.info("=" * 60)

    pipeline = IngestionPipeline(
        laike_api_base=settings.laike_api_base,
        laike_api_key=settings.laike_api_key,
    )
    orchestrator = Orchestrator(
        api_key=settings.anthropic_api_key,
        model=settings.claude_model,
    )

    # Step 1: 感知层 — 并发拉取所有数据
    logger.info("\n【Step 1】感知层 — 并发拉取数据快照...")
    snapshot = await pipeline.fetch_all(shop_id)
    context = {k.value: v.payload for k, v in snapshot.items()}
    logger.info("  已接入 %d 个数据源", len(snapshot))
    for src_type, event in snapshot.items():
        logger.info("  ✓ %s: %d 个字段", src_type.value, len(event.payload))

    # Step 2: 认知层 — 规则引擎匹配
    logger.info("\n【Step 2】认知层 — 规则引擎分析...")
    from cognitive.rule_engine import RuleEngine
    engine = RuleEngine()
    flat_ctx = {}
    for v in context.values():
        flat_ctx.update(v)
    # 补充计算字段
    product_data = context.get("product", {})
    if product_data.get("low_stock_skus"):
        sku = product_data["low_stock_skus"][0]
        flat_ctx["stock_days"] = sku["stock"] / max(sku["daily_sales"], 1)
    flat_ctx["negative_rate"] = context.get("comment_service", {}).get("sentiment", {}).get("negative", 0)

    rule_matches = engine.evaluate(flat_ctx)
    logger.info("  命中规则 %d 条:", len(rule_matches))
    for m in rule_matches:
        icon = "🔴" if m.severity == "critical" else "🟡" if m.severity == "warning" else "🔵"
        logger.info("  %s [%s] %s", icon, m.rule_id, m.message)

    # Step 3: 智能体层 — 多 Agent 并发分析
    logger.info("\n【Step 3】智能体层 — 多 Agent 并发分析...")
    if not settings.anthropic_api_key:
        logger.warning("  ⚠️  跳过 Agent 调用（未配置 ANTHROPIC_API_KEY）")
        logger.info("  提示：在 .env 中设置 ANTHROPIC_API_KEY=sk-ant-... 后重新运行")
    else:
        tasks = [
            {"task_type": "analysis", "instruction": "分析当前经营数据，给出今日经营诊断和核心问题。", "priority": 1},
            {"task_type": "ads", "instruction": "评估当前投放计划健康度，给出出价和预算调整建议。", "priority": 2},
            {"task_type": "livestream", "instruction": "根据当前直播数据，给出实时运营策略建议。", "priority": 1},
        ]
        results = await orchestrator.dispatch_multi(shop_id, tasks, context)
        logger.info("  %d 个 Agent 完成分析", len(results))
        for r in results:
            status = "✓" if r.success else "✗"
            logger.info("  %s %s — 建议动作 %d 条", status, r.agent_type, len(r.actions))

        # Step 4: 执行层 — 动作仲裁
        logger.info("\n【Step 4】执行层 — 动作仲裁与执行...")
        arbitrated = orchestrator.arbitrate_actions(results)
        logger.info("  仲裁后动作 %d 条", len(arbitrated))
        from execution.actions import ActionExecutor, ActionRecord
        import uuid
        executor = ActionExecutor(dry_run=True)
        for action in arbitrated[:3]:   # 演示只执行前 3 条
            record = ActionRecord(
                action_id=str(uuid.uuid4()),
                action_type=action.get("action_type", ""),
                shop_id=shop_id,
                params=action.get("params", {}),
                source_agent=action.get("_source_agent", ""),
            )
            record = await executor.execute(record)
            logger.info("  动作 %-25s → %s", record.action_type, record.status)

    logger.info("\n" + "=" * 60)
    logger.info("演示完成！运行 `uvicorn main:app --reload` 启动 HTTP 服务")
    logger.info("API 文档：http://localhost:8000/docs")
    logger.info("=" * 60)


if __name__ == "__main__":
    if "--server" in sys.argv:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        asyncio.run(demo())
