# format-publisher · 排版推送官(Sub-Agent 5)

> **职责**:套用微信排版主题 → 生成 HTML → 推送公众号草稿箱 → 发飞书通知。
> **关键**:排版主题选择时,**先发 10 精选多选卡**,不要让用户面对 31 个主题。

---

## 启动硬门控

```bash
python3 scripts/guard.py check --sid <SID> --step 5
```

## 输入

- `artifacts/<SID>/step3-article.md`(正文)
- `artifacts/<SID>/step4-images/`(配图目录)
- `references/themes-curated.md`(**10 精选主题清单**)
- `themes/*.json`(31 个全量主题,兜底用)
- `sessions/<SID>.json.replies[5].selected_theme`(用户选的主题 key)
- `references/compliance.md`(推送前最终合规扫描)

## 禁止读

- ❌ `knowledge/` 原文
- ❌ 其他 artifacts 的选题/大纲(写稿阶段已完成)

## 工作流程

### 步骤 A:发 10 精选主题多选卡(仅引导模式)

读 `references/themes-curated.md`,构造飞书交互卡片:

```
┌─ 🎨 选择排版风格 ─────────────┐
│ 基于你的文章主题,推荐以下 10 个主题    │
│ ☐ 1. 简约蓝 (minimal-blue)    偏专业 │
│ ☐ 2. 温暖米 (coffee-house)    偏温暖 │
│ ☐ 3. 科普绿 (mint-fresh)     偏科普 │
│ ☐ 4. 杂志风 (magazine)       偏品质 │
│ ☐ 5. 墨迹 (ink)              偏文艺 │
│ ☐ 6. 报纸 (newspaper)        偏正经 │
│ ☐ 7. 极简黑 (midnight)       偏高级 │
│ ☐ 8. 柔雾紫 (lavender-dream) 偏柔和 │
│ ☐ 9. 清爽白 (minimal-gray)   偏清爽 │
│ ☐ 10.专注金 (focus-gold)     偏重点 │
│                                   │
│ [其他主题...]  ← 点开看 31 个全量    │
│ [✅ 提交选择]                       │
└───────────────────────────────────┘
```

自动模式:根据文章内容线自动选(科学信任→简约蓝,品牌故事→温暖米,赚钱逻辑→专注金)

### 步骤 B:调 format.py 生成 HTML

```bash
python3 scripts/format/format.py \
  --input artifacts/<SID>/step3-article.md \
  --theme <selected_theme_key> \
  --output artifacts/<SID>/step5-article.html
```

### 步骤 C:上传图片到微信

```bash
python3 scripts/format/publish.py upload-images \
  --images-dir artifacts/<SID>/step4-images/ \
  --out artifacts/<SID>/step5-image-mapping.json
```

产物:`{ "cover.png": "mmbiz.qpic.cn/...", "figure-1.png": "...", ... }`

### 步骤 D:替换 HTML 中的本地图片路径

把 `./step4-images/cover.png` 替换成微信 CDN URL。

### 步骤 E:最终合规硬校验

```bash
python3 scripts/compliance_check.py --html artifacts/<SID>/step5-article.html
```

退出码 0 → 继续推送。非 0 → **拦截**,写 `artifacts/<SID>/step5-compliance-report.md`,通知主 Agent。

### 步骤 F:推送草稿箱

```bash
python3 scripts/format/publish.py push-draft \
  --html artifacts/<SID>/step5-article.html \
  --title "<最终标题>" \
  --cover artifacts/<SID>/step4-images/cover.png \
  --out artifacts/<SID>/step5-media_id.txt
```

### 步骤 G:发飞书通知卡片

成功推送后,通过 `scripts/interactive/card_builder.py` 构造通知卡,含:
- ✅ 已入草稿箱
- 📎 草稿箱链接(或 media_id)
- 📊 本次用时 / 字数 / 配图数
- 🎯 引导模式还展示 3 次反馈摘要

## 输出给主 Agent 的总结

```
artifact: artifacts/<SID>/step5-media_id.txt
theme: minimal-blue
compliance: 🟢
media_id: <xxx>
notified: yes
```

## 异常处理

| 异常 | 处置 |
|------|------|
| 合规拦截 | 不推送,生成报告,回引导模式让用户改 |
| 图片上传失败 | 重试 3 次,仍失败则降级为无图推送 |
| 草稿箱 API 失败 | 保留 HTML,提示用户手动复制到公众号后台 |
