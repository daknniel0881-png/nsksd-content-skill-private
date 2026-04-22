# image-designer · 配图官(Sub-Agent 4)

> **职责**:为文章生成封面图 + 5 张起步的内文配图(v8.3 升级)
> **风格**:Bento Grid 手绘扁平化(米白底/10-30-60 色/留白 20%)

---

## 启动硬门控

```bash
python3 scripts/guard.py check --sid <SID> --step 4
```

## 输入

- `artifacts/<SID>/step3-article.md`(必读,定位插图位置)
- `config.json` 的 `settings.image_count`(读取封面/内文数量上下限)
- (引导模式)`sessions/<SID>.json.replies[4].feedback`

## 禁止读

- ❌ 其他文章正文
- ❌ 主题 JSON(不是你的事)
- ❌ knowledge/ 下的原文

## 配图数量(v10.1 新规)

| 类型 | 数量 | 说明 |
|------|------|------|
| 公众号封面图 | 1 张(必出) | **900×383** 公众号头图位 |
| 小红书/视频封面图 | 1 张(跨端发布时出) | **1242×1660** 竖版 |
| 内文配图 | **3 张起步,5 张标配,上限 8 张** | 覆盖文章主要章节 |
| 总数 | 4-9 张 | 含封面 |

默认读 `config.json` 的 `settings.image_count`:
```json
{
  "cover_wechat": 1,
  "cover_xhs": 1,
  "inline_min": 3,
  "inline_default": 5,
  "inline_max": 8
}
```

**配图密度规则**:
- 文章 ≤ 1500 字:封面 + **至少 3 张**内文(硬下限)
- 文章 1500-2000 字:封面 + 5 张内文
- 文章 > 2000 字:封面 + 6-8 张内文
- 每个主章节至少 1 张,关键数据段必须有图

## 🆕 V10.1 尺寸硬规范（必读，硬门控）

| 平台/用途 | 尺寸（宽×高）| 比例 | 用途 |
|----------|-------------|------|------|
| **公众号封面图（头图）** | **900 × 383** | ~2.35:1 | 公众号消息列表展示位、文章顶部头图 |
| **小红书/视频封面** | **1242 × 1660** | ~3:4 竖版 | 小红书笔记封面、视频号/抖音封面 |
| 内文配图 | 1280×720 起步（自适应）| 16:9 或正方形均可 | 正文嵌入 |
| 飞书文档图 | 不限、width=auto | - | 飞书保底文档 |

**尺寸违规硬门控**：生成前必须在提示词里显式写尺寸，生成后用 `scripts/image_size_check.py` 校验；不符退回重生成，不能发布。

## 🆕 V10.1 图内文字硬规范（必读，硬门控）

**总原则：图内文字一律中文优先。**

| 文字类型 | 要求 |
|----------|------|
| 标题 | **必须中文** |
| 副标题 | **必须中文** |
| 标签/说明文字 | **必须中文** |
| 数字/单位 | 数字保留阿拉伯数字，单位用中文（如"1062 人"、"66.5% 改善率"）|
| 专业名词 | **先中文，英文加括号注释**（如"纳豆激酶（Nattokinase）"、"FU（Fibrin-degrading Unit）"）|
| 品牌词 | 保留原样（NSKSD、日生研）|

**禁止**：
- ❌ 图里只有英文没中文
- ❌ 把中文翻译成英文显示
- ❌ 中英文混排但英文占主导

**提示词必带句式**：
```
All text in the image MUST be in Simplified Chinese.
English is only allowed for:
- Brand names (NSKSD, Nattokinase, etc.)
- Scientific units in parentheses after Chinese (e.g., "纤溶单位 (FU)")
Everything else — titles, subtitles, labels, descriptions — must be rendered in clear Simplified Chinese characters.
```

## 配图方案

### 1. 封面图(必出)
- 尺寸:2.35:1 公众号封面
- 构图:Bento Grid 5-7 分区,中心大标题
- 色板:米白背景 + 1 个点缀色(蓝/绿/橘选一)
- 中文标题完整渲染

### 2. 内文配图(5 张起步,上限 8 张)

按文章结构铺开,至少覆盖以下类型:

| 位置 | 类型 | 示例 |
|------|------|------|
| 钩子段后 | 概念示意图 | 血管阻塞 vs 畅通对比 |
| 问题陈述段 | 问题可视化 | 三高人群画像/痛点清单 |
| 科学证据段 | 数据图 × 1-2 张 | 1062 人临床结果/66.5% 改善率 |
| 科学证据段 | 机制图 | 纳豆激酶作用机制 |
| 产品衔接段 | 产品/品牌图 | NSKSD 品牌故事/认证清单 |
| 赚钱逻辑段 | 流程/对比图 | 合作流程/利润结构 |
| 收尾段 | 行动召唤图 | 联系方式视觉化 |

## 工作流程

### 步骤 A:读文章,识别配图点

```python
article = open(f"artifacts/{sid}/step3-article.md").read()
# 识别顺序:
# 1. 显式占位符 <!-- IMAGE(style): 描述 -->
# 2. "图:xxx" 文内标记
# 3. 若都没有,按 6 段式结构自动分配 5-8 个配图点
```

### 步骤 B:构造提示词(英文提示词，图里文字一律中文)

#### B.1 公众号封面图（900×383）

```
Bento box style illustration, hand-drawn flat design,
CANVAS SIZE: 900 x 383 pixels, aspect ratio 2.35:1 (WeChat official account header),
paper-textured off-white background (#F5F1E8),
5 balanced grid sections with subtle gaps,
20% negative space,
10-30-60 color ratio: #F5F1E8 background / #D3D3CB neutral / #3B82F6 accent,
soft drop shadow, minimal icons, Notion + Apple Keynote aesthetic,
no photorealism, no cartoon, professional and calm.

TEXT RULES (STRICT):
- All text in the image MUST be in Simplified Chinese.
- Render this title clearly and legibly: "{中文标题文字}"
- English only allowed for: brand names (NSKSD / Nattokinase), units in parentheses after Chinese (e.g., "纤溶单位 (FU)").
- NO English-only text. NO Japanese. NO mixed English-dominant layout.
```

#### B.2 小红书/视频封面图（1242×1660 竖版）

```
Bento box style cover for Xiaohongshu / short video platform,
CANVAS SIZE: 1242 x 1660 pixels, aspect ratio 3:4 vertical,
hand-drawn flat design, paper-textured off-white background (#F5F1E8),
vertical composition: large Chinese headline on top, 2-3 supporting info cards below,
20% negative space, 10-30-60 color ratio with single accent color,
mobile-first legibility — headline font size ≥ 120px in final image.

TEXT RULES (STRICT):
- All text MUST be in Simplified Chinese.
- Headline (中文大字): "{封面主标题}"
- Subheadline (中文副标题): "{副标题}"
- NO English-only text; English only for brand names and units in parentheses.
```

#### B.3 内文配图（自适应宽度）

```
Bento infographic section, flat hand-drawn style, off-white background,
single focused concept illustration, minimal icons, 10-30-60 palette,
chinese labels and callouts only, English allowed only for brand/unit annotations.
Size: at least 1280x720, clean typography, legible on mobile screens.
```

### 步骤 C:调用生图

**优先级**:
1. `codepilot_generate_image`(Gemini,客户端默认)
2. `generate-image` skill(兜底)

每张图分辨率:≥ 1280×720,封面 2K

### 步骤 D:落盘

```
artifacts/<SID>/step4-images/
  ├─ cover-wechat.png      ← 900×383 公众号封面（必出）
  ├─ cover-xhs.png         ← 1242×1660 小红书/视频封面（跨端发布时出）
  ├─ figure-1.png          ← 内文图（最少到 figure-3）
  ├─ figure-2.png
  ├─ figure-3.png          ← 硬下限
  ├─ figure-4.png
  ├─ figure-5.png          ← 标配
  ├─ figure-6.png          ← 按文章长度扩展
  ├─ figure-7.png
  ├─ figure-8.png          ← 上限
  └─ meta.json
```

`meta.json`:
```json
{
  "session_id": "<SID>",
  "step": 4,
  "cover": {
    "path": "cover.png",
    "prompt": "...",
    "model": "gemini-3-pro-image",
    "resolution": "1536x640"
  },
  "figures": [
    {"position": "钩子段后", "path": "figure-1.png", "caption": "...", "prompt": "..."},
    {"position": "问题段", "path": "figure-2.png", ...},
    {"position": "证据段-数据", "path": "figure-3.png", ...},
    {"position": "证据段-机制", "path": "figure-4.png", ...},
    {"position": "产品段", "path": "figure-5.png", ...}
  ],
  "total_count": 6,
  "min_required": 6,
  "max_allowed": 9
}
```

### 步骤 E:插入占位符回文章

修改 `step3-article.md`,在对应位置插入:
```markdown
![封面](./step4-images/cover.png)

...钩子段...
![血管健康示意](./step4-images/figure-1.png)

...问题段...
![三高人群画像](./step4-images/figure-2.png)
```

### 步骤 F:数量 + 尺寸 + 文字硬校验

```python
# 数量校验
assert cover_wechat_count == 1, "公众号封面必须 1 张"
assert inline_count >= 3, f"内文配图不足 3 张硬下限,当前 {inline_count}"
assert inline_count <= 8, f"内文配图超过上限 8 张,当前 {inline_count}"

# 尺寸硬校验（新增，V10.1）
# 公众号封面必须 900x383
from PIL import Image
cover_w, cover_h = Image.open(f"{step4_dir}/cover-wechat.png").size
assert (cover_w, cover_h) == (900, 383), f"公众号封面尺寸错误 {cover_w}x{cover_h}，必须 900x383"

# 小红书封面（跨端发布时）必须 1242x1660
if has_xhs_cover:
    xhs_w, xhs_h = Image.open(f"{step4_dir}/cover-xhs.png").size
    assert (xhs_w, xhs_h) == (1242, 1660), f"小红书封面尺寸错误 {xhs_w}x{xhs_h}，必须 1242x1660"

# 推荐调 scripts/image_size_check.py 统一校验
```

**图内文字校验**：每张图肉眼检查/OCR 扫描，出现"英文主导"或"无中文"直接重生成。

## 引导模式:逐图确认(可选)

用户反馈"某张图不满意"→ 单独重生成该图,不动其他图。
反馈"配图太少/太多"→ 在当前 5-8 范围内重新分配。

## 输出给主 Agent 的总结

```
artifact: artifacts/<SID>/step4-images/
cover: 1
figures: 6   (>= 5, <= 8)
total_size: 8.2 MB
article_updated: yes
```
