"""执行层 — 自动化动作"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ActionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ActionRecord:
    action_id: str
    action_type: str
    shop_id: str
    params: dict[str, Any]
    source_agent: str
    status: ActionStatus = ActionStatus.PENDING
    result: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    executed_at: datetime | None = None


class ActionExecutor:
    """执行层动作执行器 — 对接来客后台 API 执行自动化动作"""

    def __init__(self, laike_api_base: str = "", laike_api_key: str = "", dry_run: bool = False):
        self.api_base = laike_api_base
        self.api_key = laike_api_key
        self.dry_run = dry_run   # True 时只打印，不真实执行
        self._handlers: dict[str, Any] = self._register_handlers()

    # ── 动作注册 ─────────────────────────────────────────────
    def _register_handlers(self) -> dict:
        return {
            # 投放相关
            "adjust_bid": self._adjust_bid,
            "adjust_budget": self._adjust_budget,
            "pause_plan": self._pause_plan,
            "create_plan": self._create_plan,
            "expand_audience": self._expand_audience,
            # 商品相关
            "update_price": self._update_price,
            "update_stock_alert": self._update_stock_alert,
            "set_activity": self._set_activity,
            "delist_product": self._delist_product,
            "restock_alert": self._restock_alert,
            # 直播相关
            "switch_product": self._switch_product,
            "trigger_coupon": self._trigger_coupon,
            "adjust_live_price": self._adjust_live_price,
            "send_live_notice": self._send_live_notice,
            "request_traffic_boost": self._request_traffic_boost,
            # 报告/通知
            "generate_report": self._generate_report,
            "push_task": self._push_task,
            "send_policy_alert": self._send_policy_alert,
            "create_compliance_checklist": self._create_compliance_checklist,
            # 内容
            "generate_script": self._generate_script,
            "generate_product_copy": self._generate_product_copy,
            "generate_live_script": self._generate_live_script,
            "generate_reply_template": self._generate_reply_template,
        }

    async def execute(self, record: ActionRecord) -> ActionRecord:
        handler = self._handlers.get(record.action_type)
        if not handler:
            logger.warning("未知动作类型: %s", record.action_type)
            record.status = ActionStatus.SKIPPED
            return record

        record.status = ActionStatus.RUNNING
        record.executed_at = datetime.utcnow()
        try:
            result = await handler(record.shop_id, record.params)
            record.status = ActionStatus.SUCCESS
            record.result = result
            logger.info("[执行成功] %s | shop=%s | params=%s", record.action_type, record.shop_id, record.params)
        except Exception as exc:
            record.status = ActionStatus.FAILED
            record.result = {"error": str(exc)}
            logger.error("[执行失败] %s | %s", record.action_type, exc)
        return record

    # ── 各动作实现（接来客后台 API） ──────────────────────────

    async def _adjust_bid(self, shop_id: str, params: dict) -> dict:
        plan_id = params["plan_id"]
        direction = params["direction"]  # up/down
        percent = params.get("percent", 10)
        if self.dry_run:
            logger.info("[DryRun] 调整出价: 计划=%s 方向=%s 幅度=%s%%", plan_id, direction, percent)
            return {"dry_run": True}
        # 实际：httpx.post(f"{self.api_base}/ads/plan/bid", json={...})
        return {"plan_id": plan_id, "adjusted": True}

    async def _adjust_budget(self, shop_id: str, params: dict) -> dict:
        if self.dry_run:
            logger.info("[DryRun] 调整预算: %s", params)
            return {"dry_run": True}
        return {"adjusted": True}

    async def _pause_plan(self, shop_id: str, params: dict) -> dict:
        if self.dry_run:
            logger.info("[DryRun] 暂停计划: %s 原因: %s", params.get("plan_id"), params.get("reason"))
            return {"dry_run": True}
        return {"paused": True}

    async def _create_plan(self, shop_id: str, params: dict) -> dict:
        if self.dry_run:
            logger.info("[DryRun] 创建广告计划: %s", params)
            return {"dry_run": True}
        return {"plan_id": "new_plan_xxx", "created": True}

    async def _expand_audience(self, shop_id: str, params: dict) -> dict:
        if self.dry_run:
            logger.info("[DryRun] 扩人群: %s", params)
            return {"dry_run": True}
        return {"expanded": True}

    async def _update_price(self, shop_id: str, params: dict) -> dict:
        sku_id = params["sku_id"]
        new_price = params["new_price"]
        price_type = params.get("price_type", "sale_price")
        if self.dry_run:
            logger.info("[DryRun] 更新价格: SKU=%s 新价格=%.2f 类型=%s", sku_id, new_price, price_type)
            return {"dry_run": True}
        return {"sku_id": sku_id, "updated": True}

    async def _update_stock_alert(self, shop_id: str, params: dict) -> dict:
        if self.dry_run:
            logger.info("[DryRun] 设置库存预警: %s", params)
            return {"dry_run": True}
        return {"updated": True}

    async def _set_activity(self, shop_id: str, params: dict) -> dict:
        if self.dry_run:
            logger.info("[DryRun] 配置活动: 类型=%s SKUs=%s 折扣=%s",
                        params.get("activity_type"), params.get("sku_ids"), params.get("discount"))
            return {"dry_run": True}
        return {"activity_id": "act_xxx", "created": True}

    async def _delist_product(self, shop_id: str, params: dict) -> dict:
        if self.dry_run:
            logger.info("[DryRun] 下架商品: %s 原因: %s", params.get("sku_id"), params.get("reason"))
            return {"dry_run": True}
        return {"delisted": True}

    async def _restock_alert(self, shop_id: str, params: dict) -> dict:
        msg = f"🔔 补货提醒：SKU {params.get('sku_id')} 建议补货 {params.get('suggested_quantity')} 件"
        logger.info(msg)
        return {"notification_sent": True, "message": msg}

    async def _switch_product(self, shop_id: str, params: dict) -> dict:
        if self.dry_run:
            logger.info("[DryRun] 直播切品: SKU=%s 原因=%s", params.get("sku_id"), params.get("reason"))
            return {"dry_run": True}
        return {"switched": True}

    async def _trigger_coupon(self, shop_id: str, params: dict) -> dict:
        if self.dry_run:
            logger.info("[DryRun] 发优惠券: 面值=%s 数量=%s", params.get("amount"), params.get("quantity"))
            return {"dry_run": True}
        return {"coupon_id": "cpn_xxx", "issued": True}

    async def _adjust_live_price(self, shop_id: str, params: dict) -> dict:
        if self.dry_run:
            logger.info("[DryRun] 调整直播间价: SKU=%s 价格=%.2f", params.get("sku_id"), params.get("price", 0))
            return {"dry_run": True}
        return {"updated": True}

    async def _send_live_notice(self, shop_id: str, params: dict) -> dict:
        logger.info("📢 直播间通知: %s", params.get("message"))
        return {"sent": True}

    async def _request_traffic_boost(self, shop_id: str, params: dict) -> dict:
        logger.info("🚀 申请流量扶持: shop=%s", shop_id)
        return {"requested": True}

    async def _generate_report(self, shop_id: str, params: dict) -> dict:
        report_type = params.get("report_type", "daily")
        logger.info("📄 生成%s报告: shop=%s", report_type, shop_id)
        return {"report_type": report_type, "status": "generated"}

    async def _push_task(self, shop_id: str, params: dict) -> dict:
        logger.info("📬 推送任务: %s → %s", params.get("task_name"), shop_id)
        return {"pushed": True}

    async def _send_policy_alert(self, shop_id: str, params: dict) -> dict:
        logger.info("⚠️ 政策变更推送: %s", params.get("policy_name"))
        return {"sent": True}

    async def _create_compliance_checklist(self, shop_id: str, params: dict) -> dict:
        logger.info("✅ 生成合规自查清单: shop=%s", shop_id)
        return {"checklist_created": True}

    async def _generate_script(self, shop_id: str, params: dict) -> dict:
        logger.info("✍️ 生成脚本内容 (长度=%d字)", len(params.get("content", "")))
        return {"content_saved": True}

    async def _generate_product_copy(self, shop_id: str, params: dict) -> dict:
        logger.info("🏷️ 生成商品文案")
        return {"content_saved": True}

    async def _generate_live_script(self, shop_id: str, params: dict) -> dict:
        logger.info("🎬 生成直播话术")
        return {"content_saved": True}

    async def _generate_reply_template(self, shop_id: str, params: dict) -> dict:
        logger.info("💬 生成回复模板")
        return {"content_saved": True}
