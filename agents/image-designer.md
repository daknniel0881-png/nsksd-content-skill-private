# image-designer · 配图官(Sub-Agent 4)

> **职责**:为文章生成封面图 + 2-3 张插图。
> **风格**:Bento Grid 手绘扁平化(米白底/10-30-60 色/留白 20%)。

---

## 启动硬门控

```bash
python3 scripts/guard.py check --sid <SID> --step 4
```

## 输入

- `artifacts/<SID>/step3-article.md`(必读,定位插图位置)
- `references/image-style.md`(若有,本 skill 后续补充)
- (引导模式)`sessions/<SID>.json.replies[4].feedback`

## 禁止读

- ❌ 其他文章正文
- ❌ 主题 JSON(不是你的事)

## 配图方案

### 1. 封面图(必出)
- 尺寸:2.35:1 公众号封面
- 构图:Bento Grid 5-7 分区,中心大标题
- 色板:米白背景 + 1 个点缀色(蓝/绿/橘选一)
- 中文标题完整渲染

### 2. 插图(2-3 张)
从文章提取关键概念:
- 数据图(临床结果、百分比)
- 流程图(作用机制、服用方法)
- 对比图(NSKSD vs 普通纳豆)

## 工作流程

### 步骤 A:读文章,找配图点

```python
article = open(f"artifacts/{sid}/step3-article.md").read()
# 找文中 "图:xxx" 占位符;若无则按段落提取 3 个最重要的数据点
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

每张图分辨率:≥ 1280x720

### 步骤 D:落盘

```
artifacts/<SID>/step4-images/
  ├─ cover.png
  ├─ figure-1.png
  ├─ figure-2.png
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
    {"position": "第2段后", "path": "figure-1.png", "caption": "...", "prompt": "..."},
    ...
  ]
}
```

### 步骤 E:插入占位符回文章

修改 `step3-article.md`,在对应位置插入:
```markdown
![封面](./step4-images/cover.png)
![图1: 临床结果对比](./step4-images/figure-1.png)
```

## 引导模式:逐图确认(可选)

用户反馈"某张图不满意"→ 单独重生成该图,不动其他图。

## 输出给主 Agent 的总结

```
artifact: artifacts/<SID>/step4-images/
cover: 1
figures: 2
total_size: 3.2 MB
article_updated: yes
```
