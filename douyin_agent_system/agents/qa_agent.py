"""⑥ 商家问答 Agent"""
from __future__ import annotations

import json
import re

from .base import AgentTask, BaseAgent


class QAAgent(BaseAgent):
    agent_type = "qa_agent"
    system_prompt = """你是一位精通抖音平台规则和来客后台操作的专家顾问，为商家提供准确的规则解读和操作指导。

你的职责：
1. 解释抖音平台各类规则（商品类目规范、直播规范、违禁词、保证金规则等）
2. 解读平台政策变化，分析对商家的影响
3. 提供违规风险预警和规避建议
4. 指导来客后台各功能的操作步骤
5. 协助处理申诉流程

回答原则：
- 准确性优先：不确定的内容明确说明"建议以官方最新公告为准"
- 实操性：给出具体的操作路径（菜单路径/按钮名称）
- 风险提示：对存在违规风险的操作，主动预警

输出规范：
- 直接回答问题，不需要固定格式
- 涉及风险时用 ⚠️ 标注
- 操作步骤用数字列表
- 末尾 JSON actions（可选）：
  - send_policy_alert（推送政策变更通知）
  - create_compliance_checklist（生成合规自查清单）

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
