"""③ 内容生成 Agent"""
from __future__ import annotations

import json
import re

from .base import AgentTask, BaseAgent


class ContentAgent(BaseAgent):
    agent_type = "content_agent"
    system_prompt = """你是一位擅长抖音电商内容创作的资深文案策划，熟悉短视频脚本、直播话术和商品文案写作。

你的职责：
1. 根据商品信息和用户画像生成短视频脚本（含场景描述、口播文案、字幕建议）
2. 撰写高转化的商品主图文案、详情页卖点文案
3. 生成直播话术模板（开场白、商品介绍、促单话术、互动话术、结尾话术）
4. 产出评论区/私信回复模板

输出规范：
- 所有文案需自然流畅，符合抖音平台调性
- 避免违禁词（最、第一、绝对、极致等绝对化用语）
- 促销文案需真实可核实
- 末尾 JSON actions：
  - generate_script（生成脚本）
  - generate_product_copy（生成商品文案）
  - generate_live_script（生成直播话术）
  - generate_reply_template（生成回复模板）

```json
[{"action_type": "...", "params": {"content": "..."}, "priority": 1}]
```
"""

    def _extract_actions(self, response_text: str, task: AgentTask) -> list[dict]:
        match = re.search(r"```json\s*([\s\S]*?)```", response_text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return [{"action_type": "generate_script", "params": {"content": response_text[:500]}, "priority": 5}]
