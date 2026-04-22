# Playbook：配图生成

> 场景：为 NSKSD 公众号文章生成封面图和内文配图。

---

## 场景说明（V10.1）

每篇文章需要：
- **公众号封面图 1 张（900×383）** — 公众号消息列表展示位、文章顶部头图
- **小红书/视频封面 1 张（1242×1660）** — 跨端发布小红书/视频号/抖音时必出
- **内文配图至少 3 张、标配 5 张、上限 8 张** — 内嵌于正文，辅助说明关键概念

配图风格：Bento Grid 扁平化，**中文优先（硬门控）**，贴合 NSKSD 健康科普主题。

**三条硬规矩**（V10.1 新增，不遵守直接退回重生成）：
1. 尺寸错 → `image_size_check.py` exit 1 → 不发布
2. 数量不足 3 张 → 同上
3. 图内文字英文主导 → 重写提示词，强制中文

---

## 步骤

### 1. 生成封面图

```bash
# 调用 xhs-image-creator Skill（Bento Grid 风格）
# 传入文章核心要点，由 Skill 出图
```

**公众号封面（900×383）提示词模板：**

```
Bento Grid style infographic for WeChat official account header.
CANVAS SIZE: 900 x 383 pixels, aspect ratio 2.35:1 (STRICT).
Background: clean off-white or parchment.
Main topic: [文章核心主题，中文]
Key data point: [最重要的数字，如 "1062 人研究"]
Color palette: 10-30-60 rule, single accent color.
Flat design, subtle shadows. No Japanese imagery. Professional medical/health tone.

TEXT RULES (STRICT):
- All text MUST be in Simplified Chinese.
- English allowed only for brand names (NSKSD, Nattokinase) and units in parentheses after Chinese.
- NO English-only text, NO mixed English-dominant layout.
```

**小红书/视频封面（1242×1660 竖版）提示词模板：**

```
Bento Grid vertical cover for Xiaohongshu / short video platform.
CANVAS SIZE: 1242 x 1660 pixels, aspect ratio 3:4 vertical (STRICT).
Composition: large Chinese headline on top 1/3, 2-3 supporting cards below.
Headline font size ≥ 120px in final image for mobile legibility.
Background: off-white parchment. Flat design. 10-30-60 color ratio.

TEXT RULES (STRICT):
- All text MUST be in Simplified Chinese.
- Headline (中文大字): [封面主标题]
- Subheadline (中文副标题): [副标题]
- English only for brand names / units in parentheses.
```

### 2. 生成内文配图

内文配图数量：**硬下限 3 张**，标配 5 张，最多 8 张，按以下分布：

| 位置 | 内容 | 建议数量 |
|------|------|----------|
| 开篇 | 数据可视化（核心研究数字）| 1 张（必出） |
| 中段 | 机制说明图（产品作用路径）| 1-3 张（必出至少 1） |
| 案例段 | 人物/场景插图 | 1-2 张 |
| 结尾 | 产品/品牌图 | 1 张（必出） |

**硬下限解释**：不到 3 张 → `image_size_check.py` exit 1 → 不发布。

### 3. Markdown 转 HTML 时保持 width=auto

**关键**：图片宽度一律不写固定像素。

转 HTML 后检查：
```bash
# 验证没有固定宽度
grep -n 'width="[0-9]' article.html && echo "发现固定宽度，需要修复"

# 修复脚本
python3 -c "
import re, sys
html = open(sys.argv[1]).read()
html = re.sub(r'(<img[^>]*)width=\"[0-9]+\"', r'\1width=\"auto\"', html)
html = re.sub(r'(<img[^>]*)style=\"[^\"]*width\s*:\s*[0-9]+[^\"]*\"', r'\1', html)
open(sys.argv[1], 'w').write(html)
print('已修复 width 属性')
" article.html
```

---

## 尺寸规范（V10.1 硬门控）

| 类型 | 尺寸（宽×高） | 比例 | 格式 | 用途 |
|------|--------------|------|------|------|
| **公众号封面图** | **900 × 383** | ~2.35:1 | JPG/PNG | 公众号头图位、消息列表展示 |
| **小红书/视频封面** | **1242 × 1660** | ~3:4 竖版 | JPG/PNG | 小红书笔记、视频号/抖音封面 |
| 内文配图 | 1280×720 起（自适应）| 16:9 或正方形均可 | PNG | 正文嵌入 |
| 飞书文档图 | 不限、width=auto | - | PNG | 飞书保底文档 |

> 校验工具：`python3 scripts/image_size_check.py artifacts/<SID>/step4-images/`
> 命中违规 exit 1 → watcher 退回重生成 → 不发布。

---

## 素材来源规范

| 来源 | 可用 | 说明 |
|------|------|------|
| AI 生成（xhs-image-creator）| 是 | 首选，风格统一 |
| 官方提供的产品图 | 是 | 需确认版权 |
| 网络图片 | 否 | 版权风险，禁止直接使用 |
| 学术论文截图 | 有条件可用 | 需标注来源，仅用于数据可视化参考 |

---

## 风格规范（Bento Grid）

**布局：**
- 画面切割为 5-7 个区域，区域间有间隙
- 参考便当盒或思维导图式布局
- 不死板，可以适当打破界限

**视觉：**
- 背景：纯净米白或羊皮纸色，留白 >= 20%
- 每区域 1-2 个主要图标或插画元素
- 保留手绘风格箭头和装饰线

**配色（10-30-60 原则）：**
- 60% 背景色（米白）
- 30% 中性衔接色（浅灰/浅棕）
- 10% 点缀色（品牌蓝或健康绿，唯一视觉高光）

**中文优先：**
- 所有图内文字中文为主
- 标题、标签、说明文字全部用中文
- 专有名词可保留英文并附中文说明（如 NSKSD 纳豆激酶）

---

## 常见错误

### 生成的图片出现英文文字

**原因**：提示词里没有强调中文优先。

**修复**：在提示词中明确加入 `All text in Chinese. No English except brand names.`

### 封面图尺寸不对

**原因**：公众号封面必须 **900×383（~2.35:1）**；小红书封面必须 **1242×1660（~3:4 竖版）**。

**修复**：
- 公众号封面提示词里写 `CANVAS SIZE: 900 x 383 pixels, aspect ratio 2.35:1 (STRICT)`
- 小红书封面提示词里写 `CANVAS SIZE: 1242 x 1660 pixels, aspect ratio 3:4 vertical (STRICT)`
- 生成后用 Pillow 精确裁剪到目标尺寸（不要只缩放，避免变形）
- 用 `scripts/image_size_check.py` 校验

### 内文图片在微信端过小

**原因**：图片在 HTML 中有 `width` 固定值小于显示区域。

**修复**：执行上方的 width=auto 修复脚本。

---

## 验证方法

1. 用浏览器打开 HTML 文件，检查图片是否正常显示
2. 用微信开发者工具预览（有条件的话），确认移动端显示效果
3. 确认图片没有版权水印

---

## 回查兜底

配图失败时：
1. 检查 xhs-image-creator Skill 是否可用
2. 文章可以不带封面图推送到公众号（会使用默认封面）
3. 内文图片缺失时，用文字描述替代，在 `[待曲率确认]` 标注补图位置
