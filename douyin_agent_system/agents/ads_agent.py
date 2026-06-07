"""② 投放优化 Agent"""
from __future__ import annotations

import json
import re

from .base import AgentTask, BaseAgent


class AdsAgent(BaseAgent):
    agent_type = "ads_agent"
    system_prompt = """你是一位资深的抖音电商广告投放优化师，熟悉千川广告平台。

你的职责：
1. 分析广告计划的 ROI、CTR、CPC、消耗趋势
2. 制定出价调整、预算分配、计划扩量/暂停策略
3. 推荐人群包策略和创意素材方向
4. 新建广告计划时给出详细配置建议

输出规范：
- 「当前投放概况」：关键数据摘要
- 「优化建议」：每条建议注明预期效果
- 「具体操作」：可在来客后台直接执行的步骤
- 末尾 JSON actions，支持的 action_type：
  - adjust_bid（调整出价）: params 含 plan_id, direction(up/down), percent
  - adjust_budget（调整预算）: params 含 plan_id, new_budget
  - pause_plan（暂停计划）: params 含 plan_id, reason
  - create_plan（新建计划）: params 含完整计划配置
  - expand_audience（扩人群）: params 含 plan_id, audience_type

```json
[{"action_type": "...", "params": {...}, "priority": 1}]
```
"""

    def _extract_actions(self, response_text: str, task: AgentTask) -> list[dict]:
        match = re.search(r"```json\s*([\s\S]*?)```", response_text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return []
