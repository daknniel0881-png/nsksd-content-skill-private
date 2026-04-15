# 公众号排版与发布

> 本文档详细说明排版系统的使用方法。主文件 SKILL.md 中的"阶段六"指向此处。

## 排版系统概览

本 Skill 内置完整的公众号排版系统，支持 31 个主题风格，全部自包含在 `themes/` 目录，不依赖外部 Skill。

排版流程：
```
文案（Markdown）→ AI结构化预处理（补标题、加粗、分段）→ 套用主题 → 生成微信兼容HTML → 推送草稿箱
```

## 排版脚本

| 脚本 | 用途 |
|------|------|
| `scripts/format/format.py` | Markdown → 微信兼容HTML（全部内联样式，不用 `<style>` 标签） |
| `scripts/format/publish.py` | HTML → 公众号草稿箱（微信API推送） |

## 排版主题（themes/ 目录，31个）

### 日生研推荐主题

| 推荐场景 | 主题 | 说明 |
|----------|------|------|
| **默认/日常** | `newspaper` | 报纸风，适合行业分析、科普长文 |
| **品牌故事** | `chinese` | 中国风，红色+楷体，适合企业历程、品牌文化 |
| **科学信任** | `elegant-navy` | 精致藏青，适合临床数据、专家观点 |
| **招商转化** | `focus-gold` | 聚焦金，适合商业分析、招商文案 |
| **健康科普** | `mint-fresh` | 薄荷绿，清新自然，适合健康科普 |
| **大会报道** | `magazine` | 杂志风，适合活动报道、产品评测 |
| **紧急/重磅** | `bold-navy` | 醒目藏青，适合重要公告 |

### 自动化流程中的主题映射

| 内容线 | 排版主题 | 风格 |
|--------|----------|------|
| 科学信任 | `mint-fresh` | 薄荷绿，清新，适合科普 |
| 健康科普 | `mint-fresh` | 同上 |
| 品牌故事 | `coffee-house` | 咖啡棕，温暖，适合叙事 |
| 招商转化 | `sunset-amber` | 日落琥珀，温暖有力，适合商业 |
| **兜底默认** | `mint-fresh` | 内容线未匹配时使用 |

### 全部主题列表

bauhaus、bold-blue/green/navy、bytedance、chinese、coffee-house、elegant-blue/green/navy、focus-blue/gold/red、github、ink、lavender-dream、magazine、midnight、minimal-blue/gold/gray/navy/red、mint-fresh、newspaper、sports、sspai、sunset-amber、terracotta、v5-sample、wechat-native

## 排版执行流程

### 手动排版

```bash
# 1. 排版（指定主题，输出到 /tmp/wechat-format/）
python3 scripts/format/format.py --input article.md --theme newspaper --output /tmp/wechat-format/
# 输出目录结构：/tmp/wechat-format/{标题}/{文件名}/article.html + images/

# 2. 预览（打开 preview.html，带「复制到微信」按钮）
open /tmp/wechat-format/{标题}/{文件名}/preview.html

# 3. 推送到草稿箱（--dir 指向排版输出目录）
python3 scripts/format/publish.py --dir /tmp/wechat-format/{标题}/{文件名}/ --title "文章标题" --cover images/cover.jpg

# 或者一步到位：--input 直接传 Markdown，自动排版+推送
python3 scripts/format/publish.py --input article.md --theme newspaper --title "文章标题"
```

### publish.py 参数说明

| 参数 | 说明 |
|------|------|
| `--dir / -d` | format.py 的输出目录（含 article.html 和 images/） |
| `--input / -i` | Markdown 文件路径（自动调用 format.py 排版后发布） |
| `--cover / -c` | 封面图片路径（不指定则从 images/ 目录自动选取） |
| `--title / -t` | 文章标题（默认从 HTML 提取） |
| `--theme` | 排版主题（仅 --input 模式有效） |
| `--author / -a` | 作者名（默认从 config.json 读取） |
| `--dry-run` | 模拟运行，不实际推送 |

## AI结构化预处理（排版前自动执行）

读取文案后检测 Markdown 结构完整度，如果缺少标题/加粗/列表等格式标记，自动补充：

1. **加标题**：识别逻辑段落转换点，插入 `##` 标题
2. **分段落**：确保段落间有空行，长段落在语义转换处拆分
3. **加列表**：识别并列/枚举内容，加列表标记
4. **加强调**：关键词、产品名、核心概念加 `**加粗**`
5. **清理格式**：去除多余空行、修正缩进、统一标点
6. **不改措辞**：只加结构标记，不调语序、不增删内容

## 干净草稿要求（铁律）

推送到公众号草稿箱的内容必须是**可以直接发布的干净文章**，禁止包含以下内容：
- 评分、分级标记（S级/A级/🟢/🟡等）
- "本文由AI生成"等暴露AI身份的声明
- 合规检查结果、审查报告
- "免责声明""温馨提示"等模板化尾注
- 素材来源清单、参考文献列表

文末如需提醒读者注意健康，用一句自然的话融入正文收尾即可（如"具体情况还是得问医生"），不要单独起一段做声明。

排版格式要求：段与段之间空一行，保持简洁干净。分割线（如咖啡色主题的分割线）可以保留，增强阅读节奏感。

## 微信公众号排版技术要点

- 所有样式必须内联（`style="..."`），微信编辑器会过滤 `<style>` 标签和 CSS class
- 不支持 JavaScript
- 图片必须先上传到微信素材库获取 media_id
- 封面图尺寸建议 900×383 或 2.35:1 比例
- format.py 已自动处理所有内联化，无需手动调整
