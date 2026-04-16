# 微信公众号推送草稿箱：完整操作手册

> 本文档是"把排版好的文章推送到公众号草稿箱"的完整操作手册。
> **每一步都写清楚了，不跳过任何细节。** 无论用什么模型，按这个手册操作都能跑通。

---

## 总览：推送草稿箱的完整流程

```
第1步：准备 Markdown 文章文件
    ↓
第2步：运行 format.py 排版（Markdown → 微信兼容HTML）
    ↓
第3步：准备封面图（必须有，微信强制要求）
    ↓
第4步：获取微信 access_token
    ↓
第5步：上传正文图片到微信CDN（如果文章有图片）
    ↓
第6步：上传封面图到微信永久素材库
    ↓
第7步：调用草稿箱API推送文章
    ↓
完成！去公众号后台草稿箱查看
```

你可以用 `publish.py` 一键完成第2-7步，也可以手动逐步执行。下面两种方式都写清楚。

---

## 方式一：一键推送（推荐）

### 前置条件

1. Python 3 已安装
2. 依赖已安装：`pip3 install markdown requests python-dotenv`
3. `config.json` 已配置（微信 AppID 和 AppSecret）
4. 微信公众号 IP 白名单已配置（见 [docs/onboarding.md](onboarding.md)）

### 操作步骤

**Step 1：准备 Markdown 文章**

文章必须是标准 Markdown 格式：
```markdown
# 文章标题

正文第一段...

## 小标题

正文内容...

**加粗关键词**

- 列表项1
- 列表项2
```

保存为 `.md` 文件，如 `/tmp/article.md`。

**Step 2：一键排版 + 推送**

```bash
cd /path/to/nsksd-content-skill

# 方式A：指定主题排版并推送
python3 scripts/format/publish.py \
  --input /tmp/article.md \
  --theme mint-fresh \
  --title "文章标题"

# 方式B：使用默认主题
python3 scripts/format/publish.py \
  --input /tmp/article.md \
  --title "文章标题"

# 方式C：指定封面图
python3 scripts/format/publish.py \
  --input /tmp/article.md \
  --theme mint-fresh \
  --title "文章标题" \
  --cover /path/to/cover.jpg

# 方式D：先排版不推送（dry-run测试）
python3 scripts/format/publish.py \
  --input /tmp/article.md \
  --theme mint-fresh \
  --title "文章标题" \
  --dry-run
```

**Step 3：检查输出**

成功时你会看到：
```
=== 第一步：排版 ===
  主题: mint-fresh
  输出: /tmp/wechat-format/文章标题/

=== 第二步：准备发布 ===
标题: 文章标题
作者: 你的作者名

获取 access_token...
  token 有效期: 7200 秒
✓ token 获取成功

上传封面图: cover.jpg
  ✓ media_id: xxxxxxxxxxxxxx...

推送到草稿箱...

========================================
  发布成功!
  草稿 media_id: xxxxxx
  → 请到微信公众号后台 → 草稿箱 查看和发布
========================================
```

**Step 4：去公众号后台查看**

1. 打开 https://mp.weixin.qq.com
2. 左侧菜单 → **「内容管理」** → **「草稿箱」**
3. 你会看到刚推送的文章
4. 点击文章可以预览、编辑、发布

---

## 方式二：手动逐步执行（用于调试或理解原理）

### Step 1：排版（Markdown → HTML）

```bash
cd /path/to/nsksd-content-skill

python3 scripts/format/format.py \
  --input /tmp/article.md \
  --theme mint-fresh \
  --output /tmp/wechat-format/ \
  --no-open
```

**这条命令做了什么**：
1. 读取 `/tmp/article.md`
2. 加载 `themes/mint-fresh.json` 主题配置
3. 将 Markdown 转换为微信兼容的 HTML（所有样式内联，不用 `<style>` 标签）
4. 输出到 `/tmp/wechat-format/文章标题/` 目录

**输出目录结构**：
```
/tmp/wechat-format/文章标题/
├── article.html      ← 微信兼容的纯HTML（这是要推送的内容）
├── preview.html      ← 带预览框架的HTML（可以在浏览器中看效果）
└── images/           ← 文章中的图片（如果有的话）
    ├── cover.jpg     ← 封面图
    └── img1.png      ← 正文图片
```

**验证排版效果**：
```bash
# 在浏览器中打开预览
open /tmp/wechat-format/文章标题/preview.html
```

### Step 2：准备封面图

微信公众号**强制要求**每篇文章必须有封面图（thumb_media_id），没有封面图推送会失败。

**封面图要求**：
- 格式：JPG 或 PNG
- 推荐尺寸：900×383 像素（2.35:1 比例）
- 文件大小：< 2MB

**封面图来源**（按优先级）：
1. 用 `--cover` 参数指定的图片
2. `images/` 目录下名称包含 `cover` 的图片
3. `images/` 目录下的第一张图片
4. `assets/default-cover.jpg`（Skill自带的默认封面）

如果你没有准备封面图，`publish.py` 会自动使用默认封面。

### Step 3：获取 access_token

```bash
# 替换为你的 AppID 和 AppSecret
curl "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=你的AppID&secret=你的AppSecret"
```

**成功返回**：
```json
{"access_token":"76_xxxxxxxxxxxxxxxxxx","expires_in":7200}
```

**失败返回及解决**：
```json
// IP白名单问题
{"errcode":40164,"errmsg":"invalid ip 1.2.3.4, not in whitelist rid: xxx"}
→ 解决：把错误信息中的 IP 添加到公众号后台的IP白名单中

// AppSecret错误
{"errcode":40001,"errmsg":"invalid credential, access_token is invalid or not latest"}
→ 解决：重新获取 AppSecret 并更新配置文件

// AppID格式错误
{"errcode":40013,"errmsg":"invalid appid"}
→ 解决：检查 AppID 是否复制完整
```

> access_token 有效期 7200 秒（2小时），过期后需要重新获取。`publish.py` 会自动处理。

### Step 4：上传封面图到永久素材库

封面图必须先上传到微信的永久素材库，获取 `media_id`。

```bash
# 替换 ACCESS_TOKEN 为 Step 3 获取的 token
curl -F "media=@/path/to/cover.jpg" \
  "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=ACCESS_TOKEN&type=image"
```

**成功返回**：
```json
{"media_id":"xxxxxxxxxxxxxxxxxx","url":"http://mmbiz.qpic.cn/...","item":[]}
```

**记下 `media_id`**，推送草稿箱时要用。

**常见错误**：
```json
// 图片格式不支持
{"errcode":40009,"errmsg":"invalid image size"}
→ 解决：确保图片是 jpg/png，大小 < 2MB

// 素材库满了
{"errcode":45028,"errmsg":"has reached max media count limit"}
→ 解决：去公众号后台删除不用的素材
```

### Step 5：上传正文图片到微信CDN（如果有图片）

如果文章 HTML 中包含本地图片或外部图片链接，需要先上传到微信CDN，否则图片在公众号中无法显示。

```bash
# 上传正文图片（注意：这个API和封面图的API不同）
curl -F "media=@/path/to/image.png" \
  "https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=ACCESS_TOKEN"
```

**成功返回**：
```json
{"url":"https://mmbiz.qpic.cn/mmbiz_png/xxxxxxx/0?wx_fmt=png"}
```

**把 HTML 中的图片路径替换为返回的 CDN URL**。

`publish.py` 会自动完成这一步：扫描 HTML 中所有 `<img src="...">` 标签，将本地图片和外部图片都上传到微信CDN并替换。

### Step 6：推送到草稿箱

```bash
curl -X POST "https://api.weixin.qq.com/cgi-bin/draft/add?access_token=ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "articles": [{
      "title": "文章标题",
      "author": "作者名",
      "content": "<p>这里是排版后的HTML内容...</p>",
      "thumb_media_id": "封面图的media_id",
      "content_source_url": "",
      "need_open_comment": 0,
      "only_fans_can_comment": 0
    }]
  }'
```

**成功返回**：
```json
{"media_id":"xxxxxxxxxx"}
```

这个 `media_id` 就是草稿箱中这篇文章的ID。

**常见错误**：
```json
// 没有封面图
{"errcode":45166,"errmsg":"content is empty or thumb_media_id is invalid"}
→ 解决：确保 thumb_media_id 是有效的永久素材ID

// HTML内容为空
{"errcode":44004,"errmsg":"empty content"}
→ 解决：检查 content 字段是否为空

// 内容过长
{"errcode":45167,"errmsg":"content size out of limit"}
→ 解决：文章内容（含HTML标签）不能超过20000字节，精简内容或减少样式

// 标题为空
{"errcode":44003,"errmsg":"empty title"}
→ 解决：确保 title 字段不为空
```

### Step 7：验证

1. 打开 https://mp.weixin.qq.com
2. 左侧菜单 → **「内容管理」** → **「草稿箱」**
3. 找到你的文章，点击预览
4. 检查排版效果、图片显示、标题是否正确

---

## publish.py 参数完整说明

```bash
python3 scripts/format/publish.py [参数]
```

| 参数 | 简写 | 说明 | 示例 |
|------|------|------|------|
| `--input` | `-i` | Markdown文件路径（自动排版+推送） | `--input article.md` |
| `--dir` | `-d` | format.py输出目录（跳过排版直接推送） | `--dir /tmp/wechat-format/标题/` |
| `--cover` | `-c` | 封面图路径 | `--cover cover.jpg` |
| `--title` | `-t` | 文章标题（不指定则从HTML提取） | `--title "标题"` |
| `--theme` | | 排版主题（仅--input模式） | `--theme mint-fresh` |
| `--author` | `-a` | 作者名（默认从config.json读取） | `--author "作者"` |
| `--dry-run` | | 模拟运行，不实际推送 | `--dry-run` |

> `--input` 和 `--dir` 二选一，不能同时使用。

---

## 凭据读取优先级

publish.py 读取微信凭据的优先级：

1. **环境变量**（最高）：`WECHAT_APP_ID` 和 `WECHAT_APP_SECRET`
2. **config.json**：`wechat.app_id` 和 `wechat.app_secret`

建议两处都配好，环境变量用于自动化脚本，config.json用于手动执行。

---

## 自动化流程中的推送（WSClient 服务）

当用户在飞书卡片中选择选题后，WSClient 服务会自动执行以下流程：

```
1. Claude CLI 生成文章 Markdown
2. 调用 format.py 排版（自动选主题）
3. 复制默认封面到 images/ 目录
4. 调用 publish.py 推送草稿箱（非交互模式）
5. 发送飞书通知卡片
```

**非交互模式**：当环境变量 `AUTO_PUBLISH=1` 或 stdin 不是终端时，publish.py 会跳过所有确认提示（如"部分图片上传失败，是否继续？"），直接继续推送。

---

## 故障排查速查表

| 症状 | 可能原因 | 解决方法 |
|------|----------|----------|
| `errcode=40164` IP不在白名单 | 出口IP变了 | `curl ifconfig.me` 查看当前IP，添加到白名单 |
| `errcode=40001` 凭据无效 | AppSecret 错误或过期 | 重新获取 AppSecret |
| 封面图上传失败 | 图片 > 2MB 或格式不对 | 压缩到 < 2MB，用 jpg/png |
| 正文图片不显示 | 图片未上传到微信CDN | 用 publish.py 自动上传，或手动上传 |
| HTML内容被截断 | 超过20000字节限制 | 精简内容或减少内联样式 |
| 排版效果和预览不同 | 微信编辑器会过滤部分CSS | 检查是否使用了微信不支持的属性 |
| `format.py` 报错 | 缺少 markdown 包 | `pip3 install markdown` |
| `publish.py` 报错找不到 config.json | 工作目录不对 | 在 Skill 根目录执行，或设置 SKILL_PATH |
| 草稿箱里看到乱码 | HTML编码问题 | 确保文件是 UTF-8 编码 |
| 文章推送后没有作者名 | config.json 未配置 author | 配置 `wechat.author` 字段 |
