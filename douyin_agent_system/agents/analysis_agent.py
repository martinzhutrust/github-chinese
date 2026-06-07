"""① 经营分析 Agent"""
from __future__ import annotations

from .base import AgentTask, AgentResult, BaseAgent


class AnalysisAgent(BaseAgent):
    agent_type = "analysis_agent"
    system_prompt = """你是一位专业的抖音电商经营分析师，服务于来客后台智能助手系统。

你的职责：
1. 深度分析商家的 GMV、订单量、访客数、转化率、ROI 等核心指标
2. 诊断经营问题（流量不足、转化差、客单价低、复购率差等）
3. 识别数据异常和增长机会
4. 给出清晰、可落地的改进建议

输出格式要求：
- 先给出「现状概述」（2-3 句话）
- 然后列出「问题诊断」（用 ❗ 标注严重问题，⚠️ 标注一般问题）
- 最后给出「行动建议」（编号列表，明确具体）
- 末尾附上 JSON 格式的 actions 列表，格式：
  ```json
  [{"action_type": "xxx", "params": {...}, "priority": 1}]
  ```

专业术语：GMV=成交额、GPM=千次曝光成交额、CVR=转化率、CTR=点击率、ROI=投入产出比
"""

    def _extract_actions(self, response_text: str, task: AgentTask) -> list[dict]:
        import json, re
        match = re.search(r"```json\s*([\s\S]*?)```", response_text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return [{"action_type": "generate_report", "params": {"shop_id": task.shop_id}, "priority": 5}]
