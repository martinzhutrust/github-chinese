"""认知层 — 知识库"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class KnowledgeBaseType(str, Enum):
    PLATFORM_RULES = "platform_rules"       # 抖音平台规则库
    LAIKE_OPERATIONS = "laike_operations"   # 来客后台操作知识库
    INDUSTRY = "industry"                   # 行业经营知识库
    PRODUCT = "product"                     # 商品知识库
    ADS_STRATEGY = "ads_strategy"           # 投放策略知识库
    LIVESTREAM_OPS = "livestream_ops"       # 直播运营知识库


@dataclass
class KnowledgeEntry:
    kb_type: KnowledgeBaseType
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    priority: int = 0   # 越高越优先


class KnowledgeBase:
    """内存知识库（生产环境可替换为向量数据库检索）"""

    def __init__(self):
        self._entries: dict[KnowledgeBaseType, list[KnowledgeEntry]] = {
            kb: [] for kb in KnowledgeBaseType
        }
        self._bootstrap()

    def add(self, entry: KnowledgeEntry):
        self._entries[entry.kb_type].append(entry)

    def query(self, kb_type: KnowledgeBaseType, keywords: list[str] = None, top_k: int = 5) -> list[KnowledgeEntry]:
        candidates = self._entries[kb_type]
        if not keywords:
            return sorted(candidates, key=lambda e: -e.priority)[:top_k]
        scored: list[tuple[int, KnowledgeEntry]] = []
        for entry in candidates:
            score = sum(kw in entry.content or kw in entry.title or kw in entry.tags for kw in keywords)
            if score > 0:
                scored.append((score + entry.priority, entry))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:top_k]]

    def get_context(self, kb_types: list[KnowledgeBaseType], keywords: list[str] = None) -> str:
        """聚合多个知识库的上下文，供 Agent 调用"""
        sections: list[str] = []
        for kb_type in kb_types:
            entries = self.query(kb_type, keywords)
            if entries:
                block = f"## {kb_type.value}\n" + "\n".join(
                    f"- **{e.title}**: {e.content}" for e in entries
                )
                sections.append(block)
        return "\n\n".join(sections)

    # ── 预置知识条目 ─────────────────────────────────────────
    def _bootstrap(self):
        entries = [
            # 平台规则
            KnowledgeEntry(KnowledgeBaseType.PLATFORM_RULES, "商品违规判定",
                "禁止虚假宣传、违禁词使用（绝对化用语）、未经授权品牌词。违规将导致商品下架、保证金扣除。",
                tags=["违规", "商品", "下架"], priority=10),
            KnowledgeEntry(KnowledgeBaseType.PLATFORM_RULES, "直播违禁行为",
                "禁止在直播中展示医疗器械未经审批内容、夸大产品效果、引导场外交易。",
                tags=["直播", "违禁", "合规"], priority=10),
            KnowledgeEntry(KnowledgeBaseType.PLATFORM_RULES, "退款/退货规则",
                "7天无理由退换货适用于大多数品类，特殊品类（内衣、食品开封）需单独标注。",
                tags=["退款", "退货", "售后"], priority=8),
            KnowledgeEntry(KnowledgeBaseType.PLATFORM_RULES, "保证金规则",
                "不同类目保证金不同（500~50000元），违规扣罚上限为保证金余额。",
                tags=["保证金", "扣款"], priority=7),

            # 来客后台操作
            KnowledgeEntry(KnowledgeBaseType.LAIKE_OPERATIONS, "数据看板说明",
                "来客后台首页展示 GMV、订单量、访客数、转化率四大核心指标。可按自然日/自定义区间筛选。",
                tags=["看板", "GMV", "数据"], priority=9),
            KnowledgeEntry(KnowledgeBaseType.LAIKE_OPERATIONS, "商品管理操作",
                "在【商品管理-商品列表】可批量修改价格、库存、上下架状态。单次批量操作上限 100 条。",
                tags=["商品管理", "批量", "价格"], priority=8),
            KnowledgeEntry(KnowledgeBaseType.LAIKE_OPERATIONS, "活动报名入口",
                "在【营销中心-平台活动】报名当前可参与活动，报名截止前 48 小时关闭报名通道。",
                tags=["活动", "报名", "营销"], priority=7),

            # 行业经营
            KnowledgeEntry(KnowledgeBaseType.INDUSTRY, "美妆行业转化率基准",
                "抖音美妆类目平均转化率 1.8%~3.5%，直播带货转化率 2.5%~6%，低于 1.5% 需重点优化。",
                tags=["美妆", "转化率", "基准"], priority=8),
            KnowledgeEntry(KnowledgeBaseType.INDUSTRY, "大促节点规律",
                "618、双11、年货节是全年三大爆发节点，建议提前 15 天备货，提前 7 天启动投放预热。",
                tags=["大促", "618", "双11", "节点"], priority=9),
            KnowledgeEntry(KnowledgeBaseType.INDUSTRY, "ROI 健康阈值",
                "纯投放 ROI < 2 为亏损线，3~5 为健康区间，> 5 可加大预算。直播间 GPM > 2000 为良好。",
                tags=["ROI", "GPM", "健康值"], priority=10),

            # 商品知识
            KnowledgeEntry(KnowledgeBaseType.PRODUCT, "库存预警策略",
                "当库存 ÷ 日均销量 < 7（天）时触发补货预警；< 3 天时自动下架或限购。",
                tags=["库存", "预警", "补货"], priority=9),
            KnowledgeEntry(KnowledgeBaseType.PRODUCT, "定价策略",
                "锚点价（划线价）应为真实历史售价，不可随意虚高。活动价建议为日常价的 8~9 折。",
                tags=["定价", "锚点价", "活动价"], priority=8),

            # 投放策略
            KnowledgeEntry(KnowledgeBaseType.ADS_STRATEGY, "计划冷启动规则",
                "新建广告计划需要 3~7 天冷启动期，此期间不建议频繁调整出价（调幅不超过 ±10%）。",
                tags=["冷启动", "计划", "出价"], priority=9),
            KnowledgeEntry(KnowledgeBaseType.ADS_STRATEGY, "ROI 目标出价",
                "ROI 目标出价适合已积累转化数据（≥50 转化）的计划；新计划优先选择转化量目标。",
                tags=["ROI", "出价", "转化"], priority=8),
            KnowledgeEntry(KnowledgeBaseType.ADS_STRATEGY, "预算分配原则",
                "跑量期预算建议为出价的 30~50 倍；稳定期可按实际消耗调整，单次调幅不超过 20%。",
                tags=["预算", "分配", "跑量"], priority=8),

            # 直播运营
            KnowledgeEntry(KnowledgeBaseType.LIVESTREAM_OPS, "直播节奏建议",
                "每 20~30 分钟为一个节奏波次：引流品（低价）→ 主推品→ 利润品→ 互动留存，循环进行。",
                tags=["节奏", "选品", "引流"], priority=9),
            KnowledgeEntry(KnowledgeBaseType.LIVESTREAM_OPS, "流量承接策略",
                "自然流量高峰期（20:00~22:00）配合投放放量，确保直播间在线人数持续增长。",
                tags=["流量", "投放", "黄金时段"], priority=8),
            KnowledgeEntry(KnowledgeBaseType.LIVESTREAM_OPS, "GPM 提升方法",
                "优化选品结构（主推客单价 200~500 元品）、强化逼单话术、限时限量制造紧迫感。",
                tags=["GPM", "客单价", "话术"], priority=9),
        ]
        for e in entries:
            self.add(e)
