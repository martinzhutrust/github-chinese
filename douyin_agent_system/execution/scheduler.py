"""执行层 — 任务调度器（定时自动化）"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Coroutine

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    job_id: str
    name: str
    interval_seconds: int
    handler: Callable[[], Coroutine]
    last_run: datetime | None = None
    run_count: int = 0
    enabled: bool = True


class Scheduler:
    """简易定时调度器 — 驱动定时自动化任务（日报/数据刷新等）"""

    def __init__(self):
        self._jobs: dict[str, ScheduledJob] = {}
        self._running = False

    def register(self, name: str, interval_seconds: int, handler: Callable[[], Coroutine]) -> str:
        job_id = str(uuid.uuid4())[:8]
        self._jobs[job_id] = ScheduledJob(
            job_id=job_id,
            name=name,
            interval_seconds=interval_seconds,
            handler=handler,
        )
        logger.info("注册定时任务: %s (间隔 %ds)", name, interval_seconds)
        return job_id

    def unregister(self, job_id: str):
        self._jobs.pop(job_id, None)

    async def start(self):
        self._running = True
        logger.info("调度器启动，共 %d 个任务", len(self._jobs))
        await asyncio.gather(*(self._run_job(job) for job in self._jobs.values()))

    async def stop(self):
        self._running = False

    async def _run_job(self, job: ScheduledJob):
        while self._running and job.enabled:
            try:
                logger.debug("执行定时任务: %s", job.name)
                await job.handler()
                job.last_run = datetime.utcnow()
                job.run_count += 1
            except Exception as exc:
                logger.exception("定时任务 %s 异常: %s", job.name, exc)
            await asyncio.sleep(job.interval_seconds)


def register_default_jobs(scheduler: Scheduler, orchestrator, pipeline, shop_id: str):
    """注册系统默认定时任务"""

    async def daily_report():
        snapshot = await pipeline.fetch_all(shop_id)
        context = {k.value: v.payload for k, v in snapshot.items()}
        await orchestrator.dispatch(
            shop_id=shop_id,
            task_type="analysis",
            instruction="生成今日经营日报，包含 GMV、订单、转化率、ROI 等核心指标的日环比分析，并给出明日重点动作建议。",
            context=context,
            priority=3,
        )

    async def ads_health_check():
        from perception.data_sources import DataSourceType
        ads_event = await pipeline.fetch_source(shop_id, DataSourceType.ADS)
        context = {"ads": ads_event.payload}
        await orchestrator.dispatch(
            shop_id=shop_id,
            task_type="ads",
            instruction="检查当前所有投放计划的健康状态，对 ROI 低于 2 的计划给出调整建议。",
            context=context,
            priority=2,
        )

    async def stock_check():
        from perception.data_sources import DataSourceType
        product_event = await pipeline.fetch_source(shop_id, DataSourceType.PRODUCT)
        context = {"product": product_event.payload}
        await orchestrator.dispatch(
            shop_id=shop_id,
            task_type="product",
            instruction="检查所有商品库存水位，对库存不足 7 天的商品生成补货和限购建议。",
            context=context,
            priority=1,
        )

    scheduler.register("每日经营日报",   interval_seconds=86400, handler=daily_report)
    scheduler.register("投放健康巡检",   interval_seconds=3600,  handler=ads_health_check)
    scheduler.register("库存水位检查",   interval_seconds=1800,  handler=stock_check)
