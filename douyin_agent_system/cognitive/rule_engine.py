"""认知层 — 规则引擎"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class RuleSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class RuleMatch:
    rule_id: str
    severity: RuleSeverity
    message: str
    suggested_action: str
    data: dict[str, Any]


class Rule:
    def __init__(
        self,
        rule_id: str,
        description: str,
        condition: Callable[[dict], bool],
        severity: RuleSeverity,
        message_template: str,
        action: str,
    ):
        self.rule_id = rule_id
        self.description = description
        self.condition = condition
        self.severity = severity
        self.message_template = message_template
        self.action = action

    def evaluate(self, context: dict[str, Any]) -> RuleMatch | None:
        try:
            if self.condition(context):
                return RuleMatch(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    message=self.message_template.format(**context),
                    suggested_action=self.action,
                    data=context,
                )
        except (KeyError, TypeError):
            pass
        return None


class RuleEngine:
    """规则引擎 — 对感知层数据进行规则匹配，输出告警和建议动作"""

    def __init__(self):
        self._rules: list[Rule] = []
        self._register_builtin_rules()

    def add_rule(self, rule: Rule):
        self._rules.append(rule)

    def evaluate(self, context: dict[str, Any]) -> list[RuleMatch]:
        matches: list[RuleMatch] = []
        for rule in self._rules:
            match = rule.evaluate(context)
            if match:
                matches.append(match)
        return sorted(matches, key=lambda m: {"critical": 0, "warning": 1, "info": 2}[m.severity])

    def _register_builtin_rules(self):
        rules = [
            # ── 经营指标规则 ───────────────────────────────────
            Rule(
                "cvr_low",
                "转化率过低",
                lambda c: c.get("conversion_rate", 1) < 0.015,
                RuleSeverity.WARNING,
                "当前转化率 {conversion_rate:.2%}，低于行业基准 1.5%",
                "触发经营分析Agent：诊断转化漏斗，建议优化商品主图/详情页/直播间话术",
            ),
            Rule(
                "roi_loss",
                "投放 ROI 亏损",
                lambda c: c.get("roi", 99) < 2.0,
                RuleSeverity.CRITICAL,
                "投放 ROI 为 {roi:.1f}，低于保本线 2.0",
                "触发投放优化Agent：暂停亏损计划，调整出价策略",
            ),
            Rule(
                "roi_healthy",
                "ROI 优秀，可扩量",
                lambda c: c.get("roi", 0) > 5.0,
                RuleSeverity.INFO,
                "投放 ROI 达 {roi:.1f}，处于优秀区间",
                "触发投放优化Agent：建议扩预算 20%",
            ),
            # ── 库存规则 ──────────────────────────────────────
            Rule(
                "stock_critical",
                "库存严重不足",
                lambda c: c.get("stock_days", 99) < 3,
                RuleSeverity.CRITICAL,
                "商品库存仅剩 {stock_days:.1f} 天销量，面临断货风险",
                "触发商品运营Agent：紧急补货预警，限购或临时下架",
            ),
            Rule(
                "stock_warning",
                "库存预警",
                lambda c: 3 <= c.get("stock_days", 99) < 7,
                RuleSeverity.WARNING,
                "商品库存剩余 {stock_days:.1f} 天销量",
                "触发商品运营Agent：启动补货流程",
            ),
            # ── 直播规则 ──────────────────────────────────────
            Rule(
                "gpm_low",
                "直播 GPM 过低",
                lambda c: c.get("gpm", 9999) < 1000 and c.get("is_live", False),
                RuleSeverity.WARNING,
                "直播间 GPM 为 {gpm:.0f}，低于健康阈值 1000",
                "触发直播运营Agent：调整选品结构，强化促单话术",
            ),
            Rule(
                "live_peak",
                "直播在线人数峰值",
                lambda c: c.get("online_viewers", 0) > 5000 and c.get("is_live", False),
                RuleSeverity.INFO,
                "直播间当前在线 {online_viewers} 人，处于流量高峰",
                "触发直播运营Agent + 投放优化Agent：同步放量投放，强化主推品逼单",
            ),
            # ── 评论/客服规则 ─────────────────────────────────
            Rule(
                "response_slow",
                "客服响应超时",
                lambda c: c.get("avg_response_time_minutes", 0) > 15,
                RuleSeverity.WARNING,
                "平均客服响应时长 {avg_response_time_minutes:.0f} 分钟，超出建议值 15 分钟",
                "推送任务：提醒客服团队优先处理待回复消息",
            ),
            Rule(
                "negative_sentiment",
                "负面评论占比过高",
                lambda c: c.get("negative_rate", 0) > 0.15,
                RuleSeverity.WARNING,
                "负面评论占比 {negative_rate:.1%}，超出预警阈值 15%",
                "触发内容生成Agent：生成评论回复模板；触发商家问答Agent：分析差评原因",
            ),
        ]
        for r in rules:
            self.add_rule(r)
