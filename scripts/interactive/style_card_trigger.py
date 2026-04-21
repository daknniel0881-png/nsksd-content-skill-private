#!/usr/bin/env python3
"""排版风格卡触发器（V9.3 新增）

职责：
- 判断用户回复是否在要求"换排版 / 换主题 / 重选 / 不好看"
- 命中就返回 True，由 master-orchestrator 发起"主题多选卡"重选流程

触发正则（曲率 2026-04-21 授权）：
    换.{0,3}(排版|风格|样式|主题) | 重.{0,3}(选|排) | 不好看 | 换个(样|风)

故意保守：宁可漏召回（让用户多说一句），也不误触发打断正常交互。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

STYLE_RETRY_PATTERN = re.compile(
    r"换.{0,3}(排版|风格|样式|主题)"
    r"|重.{0,3}(选|排)"
    r"|不好看"
    r"|换个(样|风)"
)


@dataclass
class TriggerResult:
    matched: bool
    reason: str = ""


def is_style_retry(user_text: str) -> TriggerResult:
    """True 表示用户在要求换排版风格"""
    if not user_text:
        return TriggerResult(False, "empty")
    m = STYLE_RETRY_PATTERN.search(user_text)
    if m:
        return TriggerResult(True, f"matched={m.group(0)!r}")
    return TriggerResult(False, "no_match")


if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:])
    r = is_style_retry(text)
    print(f"matched={r.matched} reason={r.reason}")
    sys.exit(0 if r.matched else 1)
