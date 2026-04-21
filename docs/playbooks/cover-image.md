# Playbook：配图生成

> 场景：为 NSKSD 公众号文章生成封面图和内文配图。

---

## 场景说明

每篇文章需要：
- 封面图 1 张（900x500，用于公众号列表页展示）
- 内文配图 5-8 张（内嵌于正文，辅助说明关键概念）

配图风格：Bento Grid 扁平化，中文优先，贴合 NSKSD 健康科普主题。

---

## 步骤

### 1. 生成封面图

```bash
# 调用 xhs-image-creator Skill（Bento Grid 风格）
# 传入文章核心要点，由 Skill 出图
```

**封面图提示词模板：**

```
Bento Grid style infographic for health article.
Background: clean off-white or parchment.
Main topic: [文章核心主题，中文]
Key data point: [最重要的数字，如"1062人研究"]
Color palette: 10-30-60 rule, single accent color.
Chinese text priority. Flat design, subtle shadows.
Size: 900x500px.
No Japanese imagery. Professional medical/health tone.
```

### 2. 生成内文配图

内文配图数量：5 张起步，最多 8 张，按以下分布：

| 位置 | 内容 | 建议数量 |
|------|------|----------|
| 开篇 | 数据可视化（核心研究数字）| 1 张 |
| 中段 | 机制说明图（产品作用路径）| 2-3 张 |
| 案例段 | 人物/场景插图 | 1-2 张 |
| 结尾 | 产品/品牌图 | 1 张 |

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

## 尺寸规范

| 类型 | 尺寸 | 格式 | 用途 |
|------|------|------|------|
| 封面图 | 900x500 | JPG/PNG | 公众号列表展示 |
| 内文配图 | 750x500 或自适应 | PNG | 正文嵌入 |
| 飞书文档图 | 不限，width=auto | PNG | 飞书保底文档 |

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

### 封面图比例不对（公众号显示变形）

**原因**：生成尺寸不是 900x500（16:9 近似比例）。

**修复**：指定 `--size 900x500` 或在提示词中写 `Aspect ratio: 9:5`

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
