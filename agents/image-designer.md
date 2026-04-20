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

## 配图数量(v8.3 新规)

| 类型 | 数量 | 说明 |
|------|------|------|
| 封面图 | 1 张(必出) | 公众号封面位 |
| 内文配图 | **5 张起步,上限 8 张** | 覆盖文章主要章节 |
| 总数 | 6-9 张 | 含封面 |

默认读 `config.json` 的 `settings.image_count`:
```json
{
  "cover": 1,
  "inline_min": 5,
  "inline_max": 8
}
```

**配图密度规则**:
- 文章 ≤ 1500 字:封面 + 5 张内文
- 文章 1500-2000 字:封面 + 6 张内文
- 文章 > 2000 字:封面 + 7-8 张内文
- 每个主章节至少 1 张,关键数据段必须有图

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

### 步骤 B:构造提示词(英文,图里中文)

Bento Grid 核心提示词模板:

```
Bento box style illustration, hand-drawn flat design,
paper-textured off-white background (#F5F1E8),
5 balanced grid sections with subtle gaps,
20% negative space,
10-30-60 color ratio: #F5F1E8 background / #D3D3CB neutral / #3B82F6 accent,
chinese text rendered clearly: "{中文标题文字}",
soft drop shadow, minimal icons, Notion + Apple Keynote aesthetic,
no photorealism, no cartoon, professional and calm
```

### 步骤 C:调用生图

**优先级**:
1. `codepilot_generate_image`(Gemini,客户端默认)
2. `generate-image` skill(兜底)

每张图分辨率:≥ 1280×720,封面 2K

### 步骤 D:落盘

```
artifacts/<SID>/step4-images/
  ├─ cover.png
  ├─ figure-1.png
  ├─ figure-2.png
  ├─ figure-3.png
  ├─ figure-4.png
  ├─ figure-5.png          ← 最少到这张
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

### 步骤 F:数量校验

```python
assert cover_count == 1, "封面必须 1 张"
assert inline_count >= 5, f"内文配图不足 5 张,当前 {inline_count}"
assert inline_count <= 8, f"内文配图超过上限 8 张,当前 {inline_count}"
```

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
