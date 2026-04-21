#!/usr/bin/env python3
"""credentials.py 单元测试

覆盖目标：
- mask() 边界（None / 空串 / 短串 / 正常长串）
- check_credentials() 各种 config 状态
- mask_in_text() 多 secret 替换
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib import credentials


class TestMask(unittest.TestCase):
    def test_mask_none(self):
        self.assertEqual(credentials.mask(None), "<empty>")

    def test_mask_empty(self):
        self.assertEqual(credentials.mask(""), "<empty>")

    def test_mask_short(self):
        # 长度 <= 2*keep 全部遮掉，避免泄漏
        self.assertEqual(credentials.mask("abc"), "****")
        self.assertEqual(credentials.mask("12345678"), "****")

    def test_mask_long(self):
        self.assertEqual(credentials.mask("wxabcdefghijklmnop1234"), "wxab****1234")

    def test_mask_in_text(self):
        secret = "wxSuperSecret12345"
        text = f"errmsg appid=wx123 secret={secret} done"
        out = credentials.mask_in_text(text, [secret])
        self.assertNotIn(secret, out)
        self.assertIn("wxSu****2345", out)


class TestCheckCredentials(unittest.TestCase):
    def _with_config(self, cfg):
        status = credentials.check_credentials(config=cfg)
        return status

    def setUp(self):
        # 清掉环境变量避免污染
        for k in ("WECHAT_APP_ID", "WECHAT_APP_SECRET",
                  "FEISHU_APP_ID", "FEISHU_APP_SECRET"):
            os.environ.pop(k, None)

    def test_empty_config(self):
        s = self._with_config({})
        self.assertFalse(s.wechat_ready)
        self.assertFalse(s.feishu_ready)
        self.assertTrue(s.should_fallback)

    def test_placeholder_config(self):
        cfg = {
            "wechat": {"app_id": "YOUR_WECHAT_APP_ID", "app_secret": "YOUR_SECRET"},
            "feishu": {"app_id": "YOUR_X", "app_secret": "YOUR_Y"},
        }
        s = self._with_config(cfg)
        self.assertFalse(s.wechat_ready)
        self.assertTrue(s.should_fallback)

    def test_full_config(self):
        cfg = {
            "wechat": {"app_id": "wxRealAppId1234", "app_secret": "realsecret567890"},
            "feishu": {"app_id": "cli_realfeishuapp", "app_secret": "fsrealsecret01"},
        }
        s = self._with_config(cfg)
        self.assertTrue(s.wechat_ready)
        self.assertTrue(s.feishu_ready)
        self.assertFalse(s.should_fallback)

    def test_env_override(self):
        os.environ["WECHAT_APP_ID"] = "wxFromEnv123456"
        os.environ["WECHAT_APP_SECRET"] = "envSecret7890ab"
        cfg = {"wechat": {"app_id": "YOUR_WECHAT_APP_ID", "app_secret": "YOUR_X"}}
        s = self._with_config(cfg)
        self.assertTrue(s.wechat_ready)


class TestCollectSecrets(unittest.TestCase):
    def test_collect_skips_placeholders(self):
        cfg = {
            "wechat": {"app_id": "YOUR_X", "app_secret": "realSecretFromCfg12345"},
        }
        secrets = credentials.collect_secrets_for_masking(config=cfg)
        self.assertIn("realSecretFromCfg12345", secrets)
        self.assertNotIn("YOUR_X", secrets)


if __name__ == "__main__":
    unittest.main()
