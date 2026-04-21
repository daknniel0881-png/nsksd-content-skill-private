#!/usr/bin/env python3
"""style_card_trigger 正则覆盖"""

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from style_card_trigger import is_style_retry


class TestStyleTrigger(unittest.TestCase):
    def test_positive_cases(self):
        cases = [
            "换个排版",
            "换一下风格",
            "换主题",
            "换个样式",
            "重选一个",
            "重排一下",
            "这个不好看",
            "换个样",
            "不好看啊",
            "帮我换个主题吧",
        ]
        for c in cases:
            with self.subTest(text=c):
                self.assertTrue(is_style_retry(c).matched, f"should match: {c}")

    def test_negative_cases(self):
        cases = [
            "",
            "挺好看的",
            "就这个主题挺好",
            "发布吧",
            "标题再改改",  # 改标题不是改排版
            "内容可以",
            "继续",
        ]
        for c in cases:
            with self.subTest(text=c):
                self.assertFalse(is_style_retry(c).matched, f"should NOT match: {c}")


if __name__ == "__main__":
    unittest.main()
