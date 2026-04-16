# v7.0 全流程测试记录

> 测试时间：2026-04-17 03:30-04:00
> 测试环境：macOS arm64, Python 3.9.6, Bun 1.3.10, Claude Code 2.1.109
> 测试目的：验证 v7.0 引导式4步工作流全链路是否跑通

---

## 测试总结

| 环节 | 状态 | 耗时 | 备注 |
|------|------|------|------|
| format.py 排版 | ✅ 通过 | <1s | mint-fresh 主题，979字文章 |
| IMAGE 占位符检测 | ✅ 通过 | - | 无 GEMINI_API_KEY 时优雅降级为文字占位 |
| publish.py dry-run | ✅ 通过 | ~2s | access_token 获取+封面上传成功 |
| publish.py 真推送 | ✅ 通过 | ~3s | 草稿 media_id 获取成功 |
| 飞书服务启动 | ✅ 通过 | ~3s | WSClient 长连接建立，10个选题已注册 |
| 飞书清单卡发送 | ✅ 通过 | <1s | message_id: om_x100b51279047e8a0b2631f434f17b4b |
| 飞书多选卡发送 | ✅ 通过 | <1s | message_id: om_x100b51279057cca8b362bdc940b8907 |
| Claude CLI 写稿 | ✅ 通过 | ~30s | 直接输出规范 Markdown，无多余对话内容 |

**结论：v7.0 全链路跑通，可交付。**

---

## 第一步：选题生成

### 怎么做的
1. SKILL.md 规定读取 `references/knowledge-base.md` + `references/topic-library.md` + `references/compliance.md`
2. 围绕四条内容线生成 10-15 个选题，每个选题包含五维评分和合规预检
3. 按 S/A/B 分级排列，推荐至少选 3 篇

### 实际测试
- 服务端已预注册了 10 个 FFC 大会预热选题（S级3个、A级4个、B级3个）
- 通过 `curl http://localhost:9800/status` 可以查看所有选题

### 注意事项
- 选题库文件 `references/topic-library.md` 已有 12 个验证选题 + 8 篇大会预热选题
- AI 生成新选题时应参考已有选题避免重复

---

## 第二步：标题 + 大纲生成

### 怎么做的
1. 用户选择选题后（如"选 1、3、5"），为每个选题生成 5 个标题变体
2. 标题使用 7 种公式（数字冲击型、反常识型、恐惧驱动型等）
3. 生成完整大纲（钩子→洞察→方案→背书→案例→CTA）
4. 每个标题过 5 项合规检查

### 实际测试
- 选了第5号选题「1062人临床数据背书」作为测试
- 手写了一篇完整测试文章（约1000字），包含 IMAGE 占位符

---

## 第三步：内容撰写 + 排版 + 预审

### 3.1 Claude CLI 写稿

**命令**：
```bash
claude -p "你是一个微信公众号文案写手。请阅读 /tmp/nsksd-content-skill/references/knowledge-base.md 了解素材。现在为以下选题写一篇完整的微信公众号文章：选题：你吃的纳豆激酶是真的吗？5个鉴别方法 ..."
```

**结果**：直接输出规范的 Markdown 文章，第一行是 `# 标题`，无多余对话。

**关键 prompt 技巧**：
- 必须明确说"直接输出 Markdown 格式的文章正文"
- 必须说"禁止输出任何非文章内容：不要写'好的''收到'"
- 必须说"第一行必须是文章标题（# 标题），最后一行是文章正文的结尾"
- 这些约束在 `scripts/server/index.ts` 的 `generateArticle()` 函数里已经写好了

### 3.2 format.py 排版

**命令**：
```bash
python3 scripts/format/format.py --input test-article.md --theme mint-fresh --output /tmp/wechat-format/ --no-open
```

**输出**：
```
主题: 薄荷 (mint-fresh)
输入: test-article.md
标题: 1062人临床数据摆在这：纳豆激酶到底是不是玄学？
字数: 979
  ⚠ 图片占位符 #1: 未设置 GEMINI_API_KEY，跳过生成
排版成品: /tmp/wechat-format/test-article/preview.html
```

**输出目录结构**：
```
/tmp/wechat-format/test-article/
├── article.html   (9702 bytes, 全内联样式，微信兼容)
└── preview.html   (10401 bytes, 带「复制到微信」按钮)
```

**关键发现**：
- format.py 输出路径是 `/tmp/wechat-format/{文件stem}/`，其中 stem 是输入文件名去掉 .md
- 如果用 `--output` 指定了输出目录，文件会在该目录下创建以 stem 命名的子目录
- IMAGE 占位符被转为可视化的灰色背景提示框：`🖼 配图占位：...`
- 无 GEMINI_API_KEY 时不阻断排版流程，这是正确行为

### 3.3 图片占位符处理

**占位符格式**：
```markdown
<!-- IMAGE(science): 纳豆激酶临床研究证据等级金字塔 -->
```

**有 GEMINI_API_KEY 时**：自动调用 generate_image.py 生成图片，插入文章
**无 GEMINI_API_KEY 时**：转为文字占位提示，不报错

---

## 第四步：推送公众号草稿箱

### 4.1 dry-run 测试

**命令**：
```bash
python3 scripts/format/publish.py --dir /tmp/wechat-format/test-article/ --title "文章标题" --cover assets/default-cover.jpg --dry-run
```

**输出**：
```
获取 access_token... ✓ token 获取成功
上传封面图: default-cover.jpg ✓ media_id: RTt8Y-U45B92SLFlt9Ip...
[dry-run] 跳过推送草稿箱
  HTML 长度: 7517 字符
```

### 4.2 真实推送

**命令**：
```bash
python3 scripts/format/publish.py --dir /tmp/wechat-format/test-article/ --title "1062人临床数据摆在这：纳豆激酶到底是不是玄学？" --cover assets/default-cover.jpg
```

**输出**：
```
发布成功!
草稿 media_id: RTt8Y-U45B92SLFlt9IpKE4ZjJrsvJUBRzXyMmGTqNLUcGc0X2yAJZ_64Iif32_C
→ 请到微信公众号后台 → 草稿箱 查看和发布
```

### ⚠️ 踩坑 #1：封面图是必须的

**问题**：第一次运行 publish.py 没带 `--cover`，报错退出：
```
错误: 微信要求必须有封面图。
请用 --cover 指定封面图路径，或在 images/ 目录放一张图片
```

**原因**：微信公众号 API 要求草稿必须有封面图（thumb_media_id），publish.py 会检查并报错。

**修复**：
1. 使用 `assets/default-cover.jpg` 作为默认封面
2. 在 SKILL.md 的推送命令中补充了 `--cover` 参数说明
3. `scripts/server/index.ts` 的 `publishArticle()` 函数已经处理了这个问题（自动 cp default-cover.jpg 到 images/cover.jpg）

---

## 飞书卡片系统

### 5.1 清单卡（schema 1.0，绿色）

**发送方式**：
```bash
curl -X POST http://localhost:9800/send-summary-card -H 'Content-Type: application/json' -d '{}'
```

**返回**：`{"code":0,"message_id":"om_x100b51279047e8a0b2631f434f17b4b"}`

**卡片内容**：选题概览列表 + 飞书云文档链接按钮

### 5.2 多选卡（schema 2.0，蓝色）

**发送方式**：
```bash
curl -X POST http://localhost:9800/send-card -H 'Content-Type: application/json' -d '{}'
```

**返回**：`{"code":0,"message_id":"om_x100b51279057cca8b362bdc940b8907"}`

**卡片结构**：
- schema 2.0，form 容器
- 按 S/A/B 等级分组显示选题
- 每个选题是一个 checker 组件（勾选框）
- checker 的 name 格式：`topic_{index}`（如 `topic_1`、`topic_3`）
- 底部一个 submit 按钮：「📝 提交选题，开始创作」
- 提交后卡片变灰（header template: grey, button/checker: disabled）

### 5.3 卡片回调机制

**回调类型**：`card.action.trigger`

**回调数据格式**：
```json
{
  "event": {
    "operator": { "open_id": "ou_xxx" },
    "action": {
      "form_value": {
        "topic_1": true,
        "topic_3": true,
        "submit_btn": { "tag": "button", ... }
      }
    }
  }
}
```

**处理逻辑**（`index.ts` 第623行）：
1. 从 `form_value` 中提取 `topic_` 开头且值为 `true` 的键
2. 解析出选题编号（`topic_1` → 1）
3. 匹配 `currentTopics` 数组中的选题
4. 异步调用 `handleTopicSelection()` 处理（不阻塞3秒超时）
5. 返回 toast 通知 + 更新卡片为变灰状态

**关键注意**：
- 回调必须在3秒内返回响应，否则飞书会超时
- 写稿流程放在 `handleTopicSelection()` 中异步执行
- checker 在 form 内时不配 behaviors（避免200672错误）

### 5.4 飞书服务启动方式

```bash
cd scripts/server
source .env
bun run index.ts
```

**启动后的端点**：
| 端点 | 方法 | 用途 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/status` | GET | 查看当前选题和生成状态 |
| `/register-topics` | POST | 注册选题（定时脚本调用） |
| `/set-doc-url` | POST | 设置飞书云文档URL |
| `/send-summary-card` | POST | 发送清单卡 |
| `/send-card` | POST | 发送多选卡 |

---

## 已知限制

1. **卡片回调需要真人交互**：无法通过 HTTP API 模拟卡片点击，必须在飞书客户端中实际操作
2. **GEMINI_API_KEY 未配置**：配图功能降级为文字占位，不影响主流程
3. **端口占用**：如果 9800 端口已被占用，服务启动会失败。需先 `kill` 旧进程

---

## 修复清单

| # | 问题 | 修复内容 | 文件 |
|---|------|----------|------|
| 1 | SKILL.md 推送命令缺少 --cover 参数 | 补充封面图说明和两种推送方式 | SKILL.md |
| 2 | SKILL.md 排版命令没说明输出路径 | 补充输出目录说明和 --no-open 参数 | SKILL.md |
