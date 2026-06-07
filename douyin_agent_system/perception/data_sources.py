"""感知层 — 数据接入"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataSourceType(str, Enum):
    LAIKE_API = "laike_api"           # 来客后台 API
    ECOMMERCE = "ecommerce"           # 抖音电商数据
    ADS = "ads"                       # 投放数据
    PRODUCT = "product"               # 商品数据
    LIVESTREAM = "livestream"         # 直播数据
    COMMENT_SERVICE = "comment_service"  # 评论/客服数据


class RawDataEvent(BaseModel):
    """来自感知层的原始数据事件"""
    source: DataSourceType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    shop_id: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseDataSource(ABC):
    """数据源基类"""

    source_type: DataSourceType

    @abstractmethod
    async def fetch(self, shop_id: str, **kwargs) -> RawDataEvent:
        ...

    @abstractmethod
    async def stream(self, shop_id: str):
        """实时数据流（用于直播、评论等场景）"""
        ...


# ── 来客后台 API ─────────────────────────────────────────────
class LaikeAPISource(BaseDataSource):
    source_type = DataSourceType.LAIKE_API

    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base
        self.api_key = api_key

    async def fetch(self, shop_id: str, endpoint: str = "/overview", **kwargs) -> RawDataEvent:
        # 实际场景替换为 httpx 调用
        mock_data = {
            "gmv": 128500.0,
            "orders": 342,
            "visitors": 15800,
            "conversion_rate": 0.0216,
            "avg_order_value": 375.7,
        }
        return RawDataEvent(source=self.source_type, shop_id=shop_id, payload=mock_data)

    async def stream(self, shop_id: str):
        while True:
            yield await self.fetch(shop_id)
            await asyncio.sleep(60)


# ── 抖音电商数据 ──────────────────────────────────────────────
class EcommerceDataSource(BaseDataSource):
    source_type = DataSourceType.ECOMMERCE

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret

    async def fetch(self, shop_id: str, date_range: tuple | None = None, **kwargs) -> RawDataEvent:
        mock_data = {
            "total_sales": 98700.0,
            "refund_rate": 0.032,
            "new_buyers": 218,
            "repurchase_rate": 0.28,
            "top_categories": ["美妆", "食品", "服饰"],
        }
        return RawDataEvent(source=self.source_type, shop_id=shop_id, payload=mock_data)

    async def stream(self, shop_id: str):
        while True:
            yield await self.fetch(shop_id)
            await asyncio.sleep(300)


# ── 投放数据 ─────────────────────────────────────────────────
class AdsDataSource(BaseDataSource):
    source_type = DataSourceType.ADS

    async def fetch(self, shop_id: str, **kwargs) -> RawDataEvent:
        mock_data = {
            "total_spend": 8500.0,
            "impressions": 580000,
            "clicks": 12400,
            "ctr": 0.0214,
            "cpc": 0.69,
            "roi": 3.8,
            "active_plans": [
                {"plan_id": "p001", "name": "品牌词", "spend": 2100, "roi": 5.2},
                {"plan_id": "p002", "name": "竞品词", "spend": 1800, "roi": 3.1},
                {"plan_id": "p003", "name": "兴趣人群", "spend": 4600, "roi": 3.2},
            ],
        }
        return RawDataEvent(source=self.source_type, shop_id=shop_id, payload=mock_data)

    async def stream(self, shop_id: str):
        while True:
            yield await self.fetch(shop_id)
            await asyncio.sleep(60)


# ── 商品数据 ─────────────────────────────────────────────────
class ProductDataSource(BaseDataSource):
    source_type = DataSourceType.PRODUCT

    async def fetch(self, shop_id: str, **kwargs) -> RawDataEvent:
        mock_data = {
            "total_skus": 156,
            "low_stock_skus": [
                {"sku_id": "sku_001", "name": "精华液 30ml", "stock": 12, "daily_sales": 28},
                {"sku_id": "sku_009", "name": "面膜 10片", "stock": 5, "daily_sales": 40},
            ],
            "top_sellers": [
                {"sku_id": "sku_003", "name": "水乳套装", "sales_7d": 480, "revenue_7d": 72000},
            ],
            "price_violations": [],
        }
        return RawDataEvent(source=self.source_type, shop_id=shop_id, payload=mock_data)

    async def stream(self, shop_id: str):
        while True:
            yield await self.fetch(shop_id)
            await asyncio.sleep(600)


# ── 直播数据 ─────────────────────────────────────────────────
class LiveStreamDataSource(BaseDataSource):
    source_type = DataSourceType.LIVESTREAM

    async def fetch(self, shop_id: str, **kwargs) -> RawDataEvent:
        mock_data = {
            "is_live": True,
            "room_id": "room_88812345",
            "online_viewers": 3240,
            "peak_viewers": 5100,
            "likes": 128000,
            "products_shown": 8,
            "gpm": 2850.0,          # 千次观看成交额
            "add_cart_rate": 0.092,
            "duration_minutes": 95,
        }
        return RawDataEvent(source=self.source_type, shop_id=shop_id, payload=mock_data)

    async def stream(self, shop_id: str):
        while True:
            yield await self.fetch(shop_id)
            await asyncio.sleep(10)   # 直播数据 10 秒刷新


# ── 评论/客服数据 ─────────────────────────────────────────────
class CommentServiceSource(BaseDataSource):
    source_type = DataSourceType.COMMENT_SERVICE

    async def fetch(self, shop_id: str, **kwargs) -> RawDataEvent:
        mock_data = {
            "pending_comments": 42,
            "avg_response_time_minutes": 8.5,
            "sentiment": {"positive": 0.72, "neutral": 0.18, "negative": 0.10},
            "hot_issues": ["发货慢", "尺码偏大", "包装破损"],
            "pending_refunds": 7,
        }
        return RawDataEvent(source=self.source_type, shop_id=shop_id, payload=mock_data)

    async def stream(self, shop_id: str):
        while True:
            yield await self.fetch(shop_id)
            await asyncio.sleep(30)
