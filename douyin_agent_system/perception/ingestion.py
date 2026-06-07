"""感知层 — 数据接入管道"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable, Coroutine

from .data_sources import (
    AdsDataSource,
    BaseDataSource,
    CommentServiceSource,
    DataSourceType,
    EcommerceDataSource,
    LaikeAPISource,
    LiveStreamDataSource,
    ProductDataSource,
    RawDataEvent,
)

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """统一数据接入管道 — 聚合所有感知层数据源"""

    def __init__(
        self,
        laike_api_base: str = "",
        laike_api_key: str = "",
        douyin_app_id: str = "",
        douyin_app_secret: str = "",
    ):
        self._sources: dict[DataSourceType, BaseDataSource] = {
            DataSourceType.LAIKE_API: LaikeAPISource(laike_api_base, laike_api_key),
            DataSourceType.ECOMMERCE: EcommerceDataSource(douyin_app_id, douyin_app_secret),
            DataSourceType.ADS: AdsDataSource(),
            DataSourceType.PRODUCT: ProductDataSource(),
            DataSourceType.LIVESTREAM: LiveStreamDataSource(),
            DataSourceType.COMMENT_SERVICE: CommentServiceSource(),
        }
        self._handlers: list[Callable[[RawDataEvent], Coroutine]] = []

    def register_handler(self, handler: Callable[[RawDataEvent], Coroutine]):
        """注册数据事件处理器（认知层、Agent 层可注册）"""
        self._handlers.append(handler)

    async def fetch_all(self, shop_id: str) -> dict[DataSourceType, RawDataEvent]:
        """并发拉取所有数据源的快照数据"""
        tasks = {
            src_type: source.fetch(shop_id)
            for src_type, source in self._sources.items()
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        snapshot: dict[DataSourceType, RawDataEvent] = {}
        for (src_type, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                logger.error("数据源 %s 拉取失败: %s", src_type, result)
            else:
                snapshot[src_type] = result
        return snapshot

    async def fetch_source(self, shop_id: str, source_type: DataSourceType) -> RawDataEvent:
        return await self._sources[source_type].fetch(shop_id)

    async def _dispatch(self, event: RawDataEvent):
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as exc:
                logger.exception("事件处理器异常: %s", exc)

    async def start_streaming(self, shop_id: str, source_types: list[DataSourceType] | None = None):
        """启动实时数据流，将事件广播给所有注册处理器"""
        targets = source_types or list(self._sources.keys())
        streams = [
            self._sources[t].stream(shop_id)
            for t in targets
            if t in self._sources
        ]

        async def consume(stream):
            async for event in stream:
                await self._dispatch(event)

        await asyncio.gather(*(consume(s) for s in streams))
