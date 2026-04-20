# 排版主题精选 10 个(多选卡专用)

> 用于引导模式第 5 步的"排版风格选择"卡片。
> 31 个全量主题保留在 `themes/` 目录,用户点"其他主题"可查看完整清单。

---

## 精选逻辑

从 31 个主题里挑出最适合日生研内容的 10 个,覆盖三种调性:
- **偏科普**(专业、清爽、易读)
- **偏温暖**(亲和、信任、生活化)
- **偏简约**(高级、品质、留白)

每个主题都和日生研目标读者(40-60 岁三高人群 + 社区门店老板)匹配过。

---

## 10 精选清单

| # | key | 中文名 | 调性 | 主色 | 适用内容类型 |
|---|-----|--------|------|------|-----|
| 1 | `minimal-blue` | 简约蓝 | 偏科普 · 专业感 | #3B82F6 | 临床研究、科学原理 |
| 2 | `coffee-house` | 咖啡馆 | 偏温暖 · 生活化 | #8B4513 | 品牌故事、用户案例 |
| 3 | `mint-fresh` | 薄荷清爽 | 偏科普 · 亲和 | #10B981 | 科普解惑、健康常识 |
| 4 | `magazine` | 杂志风 | 偏品质 · 权威 | #1F2937 | 深度长文、行业洞察 |
| 5 | `ink` | 水墨 | 偏文艺 · 高级 | #374151 | 品牌调性、传统文化 |
| 6 | `newspaper` | 报纸 | 偏正经 · 严肃 | #111827 | 政策解读、合规内容 |
| 7 | `midnight` | 午夜黑 | 偏高级 · 极简 | #030712 | 产品发布、重点公告 |
| 8 | `lavender-dream` | 柔雾紫 | 偏柔和 · 女性向 | #A78BFA | 美容院场景、女性健康 |
| 9 | `minimal-gray` | 极简灰 | 偏清爽 · 中性 | #6B7280 | 日常科普、短内容 |
| 10 | `focus-gold` | 专注金 | 偏重点 · 招商 | #F59E0B | 分销招商、赚钱逻辑 |

---

## 多选卡构造示例(引导模式)

```json
{
  "title": "🎨 第 5 步 · 选择排版风格",
  "subtitle": "基于文章内容类型推荐 10 个主题,也可查看全部 31 个",
  "recommend_auto": "minimal-blue",
  "options": [
    {"key": "minimal-blue", "label": "1. 简约蓝", "hint": "偏科普 · 临床类推荐"},
    {"key": "coffee-house", "label": "2. 咖啡馆", "hint": "偏温暖 · 故事类推荐"},
    {"key": "mint-fresh", "label": "3. 薄荷清爽", "hint": "偏科普 · 健康常识"},
    {"key": "magazine", "label": "4. 杂志风", "hint": "偏权威 · 深度长文"},
    {"key": "ink", "label": "5. 水墨", "hint": "偏高级 · 品牌调性"},
    {"key": "newspaper", "label": "6. 报纸", "hint": "偏严肃 · 政策合规"},
    {"key": "midnight", "label": "7. 午夜黑", "hint": "偏高级 · 产品发布"},
    {"key": "lavender-dream", "label": "8. 柔雾紫", "hint": "偏柔和 · 女性场景"},
    {"key": "minimal-gray", "label": "9. 极简灰", "hint": "偏清爽 · 短内容"},
    {"key": "focus-gold", "label": "10. 专注金", "hint": "偏重点 · 招商分销"}
  ],
  "escape_hatch": {
    "label": "🔍 查看全部 31 个主题",
    "action": "show_full_theme_list"
  }
}
```

---

## 自动模式的主题映射(内容线 → 主题)

```python
AUTO_THEME_BY_LINE = {
    "科学信任":   "minimal-blue",
    "临床证据":   "minimal-blue",
    "行业洞察":   "magazine",
    "品牌故事":   "coffee-house",
    "赚钱逻辑":   "focus-gold",
    "科普解惑":   "mint-fresh",
    "政策解读":   "newspaper",
    "女性健康":   "lavender-dream",
    "日常科普":   "minimal-gray",
    "重点公告":   "midnight",
}
```

若 `line` 不在表里,默认用 `minimal-blue`。

---

## 31 个全量主题(兜底,点"其他"展开)

`themes/` 下所有 JSON:
bauhaus / bold-blue / bold-green / bold-navy / bytedance / chinese / coffee-house / elegant-blue / elegant-green / elegant-navy / focus-blue / focus-gold / focus-red / github / ink / lavender-dream / magazine / midnight / minimal-blue / minimal-gold / minimal-gray / minimal-navy / minimal-red / mint-fresh / newspaper / sports / sspai / sun

展开时用普通文本列表,不再做多选,用户输入 key 即可。
