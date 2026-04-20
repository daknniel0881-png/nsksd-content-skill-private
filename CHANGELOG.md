# 更新日志

## v8.2（2026-04-20）

**多 Agent 调度架构 + 双入口 + 30 天去重 + 客户侧通用化**

### 核心变更

- **双入口命令**：`/nsksd-auto`（全自动）+ `/nsksd-guided`（引导式），取代原单一 `/nsksd`
- **主 Agent 去人名化**：`master-orchestrator` 作为通用主调度 Agent，无绑定任何真人昵称，客户侧可直接让自己的 Main Agent 接管
- **5 个子 Agent 严格串行**：topic-scout → title-outliner → article-writer → image-designer → format-publisher
- **guard.py 硬校验门控**：基于退出码控制流程，禁止 Agent 跳步（取代原 🛑 markdown 软提醒）
- **30 天滚动去重**：三维指纹（title_hash + angle + data_points 交集 ≥ 2）
- **写作风格去人化**：article-writer 不再引用任何个人写作风格，统一走科普大白话
- **10 主题精选**：从 31 个主题精选 10 个做飞书多选卡，剩余 21 个作为"其他主题"兜底
- **云文档 A/B/C 三次预审**：选题/标题大纲/全文+配图+排版 三个节点自动生成飞书云文档

### 新增目录与文件

**`agents/` 目录（6 个 Agent 角色提示词）**
- `agents/master-orchestrator.md` — 主调度 Agent，只读 SKILL.md + session.json + 当前 step artifact，禁止全量读 knowledge/references
- `agents/topic-scout.md` — 选题侦察员：生成 20 候选 → 查 30 天指纹 → 输出 10 个 S/A/B 级
- `agents/title-outliner.md` — 标题大纲员：每个选题 5 变体 + 6 段式大纲
- `agents/article-writer.md` — 全文撰稿员：1500-2500 字科普大白话
- `agents/image-designer.md` — 配图设计师：Bento Grid 风格封面 + 2-3 张配图
- `agents/format-publisher.md` — 排版推送员：主题选择 → format.py → 合规硬扫 → 推送草稿箱

**`scripts/` 新增**
- `scripts/guard.py` — 流程硬校验门控，支持 `new-session / check / confirm / mark-ready / status`
- `scripts/topic_history.py` — 30 天滚动去重，三维指纹 API + CLI
- `scripts/interactive/docs_publisher.py` — 云文档 A/B/C 预审自动发布

**`references/` 新增**
- `references/science-popular-style.md` — 科普大白话写作规范（字数/禁用词/禁用句式/破折号感叹号限额/6 段式结构/自查清单）
- `references/themes-curated.md` — 10 精选主题 + AUTO_THEME_BY_LINE 内容线到主题的自动映射

### 会话状态与产物目录

- `scripts/interactive/sessions/<SID>.json` — 会话状态单一真相（mode/current_step/steps[].status/replies/docs）
- `artifacts/<SID>/` — 每一步的产物：step1-topics.json / step2-titles.json / step3-article.md / step4-images/ / step5-media_id.txt
- `logs/topic-history.jsonl` — 30 天滚动去重指纹库

### 去除 / 迁移

- 删除 SKILL.md 中「阿良」「季老师」「海斌」「曲率」等人名绑定
- 删除 article-writer 对 `quyu-writing-style` 等个人写作风格的引用
- 删除 SKILL.md 中「🛑 等待用户确认」markdown 软提醒，改为 guard.py 硬门控 + 飞书反馈卡

### 飞书卡片回调（v8.1 稳定版 → v8.2 并入）

- 长连接（WebSocket）基于 `lark_oapi.ws.Client` + `register_p2_card_action_trigger`
- 卡片 schema 2.0 + `form` 容器 + `form_action_type: "submit"` + `required: false`
- 回调 3 秒内响应，写稿走异步，避免飞书超时
- 灰底锁定卡保留原标题与正文，按钮替换为"已提交"

### SKILL.md 重写

- 从「单入口 4 步工作流」重写为「双入口 + 多 Agent 调度架构」
- 新增章节：v8.2 核心升级 / 使用方式（双入口）/ 多 Agent 调度架构 / 脚本工具栏 / 30 天去重 / 云文档 A/B/C / 写作风格 / 排版主题 10 精选
- 精简合规章节（详情迁到 references）

---

## v7.3（2026-04-17）

**傻瓜式自动化：Agent 自动获取凭据，用户零配置**

### 核心理念升级
- 从「教人手动获取 ID」→「Agent 自动获取，只在必要时问用户」
- 飞书凭据全自动（App ID / App Secret / Open ID 从 lark-cli 提取）
- 微信凭据问一次（无 CLI 工具，首次需用户提供）
- IP 白名单半自动（Agent 查 IP，提醒用户加白名单）

### 新增文件
- `docs/credentials-auto-setup.md` — **Agent 专用**凭据自动配置指引，面向 AI 阅读的完整流程文档
  - 自动化程度一览表（哪些能自动、哪些要问用户）
  - lark-cli 检测 → 配置提取 → Open ID 解析 → Chat ID 搜索的完整命令
  - 微信凭据获取话术模板
  - 自动写入 .env / config.json 的代码模板
  - 验证流程（飞书测试消息 + 微信 token 检查）
  - 故障排查表
- `scripts/setup-credentials.sh` — 一键交互式配置脚本（备选方案）
  - 自动检测 lark-cli / bun / python3 依赖
  - 自动从 lark-cli 配置文件提取飞书凭据
  - 自动解析 Open ID
  - 交互式输入微信凭据（仅需一次）
  - 自动安装依赖
  - 自动发送飞书测试消息 + 验证微信 token

### SKILL.md 重写
- 「凭据配置速查」→ 「凭据自动配置」：从130行人工教程压缩到50行自动化指引
- 新增触发机制：Agent 检测到 `.env` 含占位符时自动读取 `docs/credentials-auto-setup.md` 执行配置
- 文档索引新增 `credentials-auto-setup.md`，标记为「凭据未配置时 Agent 必读」

---

## v7.2（2026-04-17）

**凭据零硬编码 + 动态配置指引**

### 安全清理：移除所有硬编码凭据
- `scripts/server/.env` 移除硬编码的飞书 App ID/Secret、Open ID、微信 App ID/Secret，恢复为模板占位符
- `config.json` 移除硬编码的微信凭据、Obsidian 路径、作者名，恢复为模板
- `scripts/server/index.ts` 移除硬编码 CHAT_ID（`oc_xxx`），改为从 `.env` 读取，不配置则自动通过 Open ID 发私聊
- `scripts/format/publish.py` 移除硬编码 IP 网段提示，改为动态查询指引

### 新增 SKILL.md「凭据配置速查」章节
- 完整凭据一览表：列出所有需要配置的 ID/Secret 及其配置位置
- 飞书 App ID / App Secret 获取方法（4步）
- 飞书 Open ID 获取方法（4种方式：发消息、lark-cli、API、管理后台）
- 飞书 Chat ID 获取方法（群聊场景，可选）
- 微信 App ID / App Secret 获取方法
- 微信 IP 白名单配置与验证方法
- 配置文件填写示例和验证步骤

### 代码改进
- `index.ts` 新增 `sendTextAuto()` 函数，根据 CHAT_ID 是否配置自动选择群聊/私聊
- `index.ts` `sendText()` 支持 `idType` 参数（`chat_id` / `open_id`）
- `.env.example` 补充 CHAT_ID 配置项和获取方式说明

---

## v7.1（2026-04-17）

**全流程测试通过 + 操作步骤内联 SKILL.md + 本地Skill同步**

### 全流程测试验证
- 测试环境：macOS arm64, Python 3.9.6, Bun 1.3.10, Claude Code 2.1.109
- format.py 排版：✅ mint-fresh 主题，生成 article.html（9.7KB）+ preview.html（10.4KB）
- IMAGE 占位符：✅ 无 GEMINI_API_KEY 时优雅降级为文字提示，不阻断流程
- publish.py dry-run：✅ access_token 获取成功，封面图上传成功
- publish.py 真推送：✅ 草稿 media_id 获取成功，文章进入公众号草稿箱
- 飞书服务 WSClient：✅ 长连接建立，10个选题已注册
- 飞书清单卡：✅ 发送成功（schema 1.0，绿色）
- 飞书多选卡：✅ 发送成功（schema 2.0，蓝色，form+checker+submit）
- Claude CLI 写稿：✅ 直接输出规范 Markdown，无多余对话内容

### SKILL.md 操作步骤内联
- 「飞书卡片推送系统」新增：服务启动命令、6个HTTP端点表、多选卡回调机制详解（form_value格式、3秒超时约束、checker命名规则、卡片变灰实现）、文本消息备选方案
- 「公众号排版与发布」新增：4步完整操作流程（写文章→排版→推送→验证）、踩坑记录表（5个常见错误及解决方案）、publish.py内部执行流程、format.py参数速查表
- 第四步推送命令补充 `--cover` 封面图参数（必须项）和两种推送方式
- 第三步排版命令补充输出路径说明和 `--no-open` 参数

### 踩坑修复
- publish.py 必须指定 `--cover` 封面图，不指定报错退出 → SKILL.md 已补充说明
- format.py 输出路径为 `/tmp/wechat-format/{文件stem}/` → SKILL.md 已补充说明

### 新增文档
- `docs/test-run-log.md` — 全流程测试记录，含每个环节的具体命令、输出、踩坑

### 本地Skill同步
- 同步 `/tmp/nsksd-content-skill/` → `~/.claude/skills/nsksd-content/`

## v7.0（2026-04-17）

**引导式4步工作流 + AI配图 + 傻瓜级文档**

### 🔄 核心架构升级：引导式工作流
- SKILL.md 从5个独立子命令重写为**引导式4步工作流**
- 每一步都有 `🛑 等待用户确认` 关卡，禁止跳步，禁止一口气跑完
- 第一步：选题生成（10-15个选题，S/A/B分级，至少推荐3个） → 等用户选择
- 第二步：标题（5个变体）+ 大纲生成 → 等用户确认
- 第三步：全文撰写 + 排版 + 飞书云文档预审 → 等用户审核
- 第四步：推送公众号草稿箱 + 飞书完成通知

### 🖼 AI配图能力（Gemini 3 Pro Image）
- 新增 `scripts/format/generate_image.py` — 基于 Gemini 3 Pro Image API 的配图生成工具
- 5种配图风格模板：science（科学信任）、brand（品牌故事）、health（健康科普）、business（招商转化）、cover（封面图）
- 内容线自动映射配图风格（科学信任→薄荷绿数据可视化，品牌故事→咖啡棕温暖专业）
- format.py 新增 `process_image_placeholders()` — 排版时自动检测 `<!-- IMAGE(style): 描述 -->` 占位符并生成插图
- 无 GEMINI_API_KEY 时优雅降级，不阻断排版流程
- 默认2K分辨率，适合公众号显示

### 📖 傻瓜级操作文档（3份新增）
- 新增 `docs/onboarding.md` — 新手引导，手把手教配置飞书机器人（7步）和微信公众号（3步），含权限标识符、事件订阅、IP白名单排查
- 新增 `docs/wechat-publish-step-by-step.md` — 微信发布完整7步手册，每个API端点都有curl示例和成功/失败响应，错误码对照表
- 新增 `docs/feishu-cards-step-by-step.md` — 飞书卡片完整手册，5种卡片类型、4种发送方式、完整JSON结构、schema 1.0/2.0对比、回调机制

### 📝 文档更新
- `docs/formatting.md` 新增"配图能力"章节，文档化占位符格式和5种风格
- `docs/setup.md` 新增 onboarding.md 链接、python-dotenv 和 google-genai 依赖
- `README.md` 全面更新：概述改为引导式4步工作流，新增AI配图和傻瓜级文档特点，使用方法改为4步流程图和典型交互示例

## v6.0（2026-04-15）

**模块化文档拆分 + 敏感信息清理 + Skill独立性**

- SKILL.md 从 668 行精简到 497 行，保留阶段 1-5 核心 AI 工作流
- 新增 `docs/formatting.md` — 排版系统、31 个主题、publish.py 参数、干净草稿要求
- 新增 `docs/feishu-cards.md` — 两张卡片设计（清单卡+多选卡）、回调机制、WSClient 服务
- 新增 `docs/scheduling.md` — Mac LaunchAgent + Windows Task Scheduler 配置及故障排查
- 新增 `docs/setup.md` — 首次安装全流程指南（凭据获取、依赖检查、目录结构）
- `run_nsksd_daily.sh` 移除硬编码 API 密钥，改为从 `.env` 读取，缺失时报错退出
- 新增 `.env.example` 和 `config.json.example` 模板文件
- plist/xml 硬编码路径添加 `<!-- EDIT -->` 注释标记，方便用户替换
- 符号链接改为相对路径（`../themes`、`../templates`），clone 后直接可用
- `FORMAT_OUTPUT_DIR` 改为可通过环境变量配置
- 新增 `scripts/setup.sh` 一键配置脚本（检查依赖、创建配置、安装 Node 包）
- 确认零外部 Skill 依赖：排版、发布、主题全部自包含

## v5.0（2026-04-15）

**双卡片推送 + 干净草稿要求 + 完整自动化流程**

- 恢复两张飞书卡片设计：清单卡（schema 1.0，绿色，带云文档链接）+ 多选卡（schema 2.0，蓝色，form+checker）
- Claude CLI prompt 加入干净草稿铁律：禁止评分、声明、免责尾注、AI 痕迹
- 段落之间空一行，保持简洁干净的排版节奏
- publish.py 非交互模式修复（`sys.stdin.isatty()` 检查）
- 新增 `.gitignore` 排除敏感凭据和日志
- 新增定时任务配置文件：LaunchAgent plist + Task Scheduler xml
- 新增默认封面图（`assets/default-cover.jpg`）

## v4.0（2026-04-15）

**融入31个公众号排版主题 + 卡片交互优化 + 10选题体系**

- 内置完整公众号排版系统：`format.py`（Markdown→HTML）+ `publish.py`（HTML→草稿箱）
- 31 个排版主题（`themes/` 目录），覆盖科学信任、品牌故事、招商转化等场景
- 飞书卡片升级为 schema 2.0：form 容器 + checker 勾选 + 提交按钮
- 提交后卡片自动变灰（header grey + checker/button disabled）
- 内容线 → 排版主题自动映射（科学信任→mint-fresh，品牌故事→coffee-house，招商转化→sunset-amber）
- 10 个预置选题，含五维评分和合规分级

## v3.0（2026-04-15）

**自动化选题系统（WSClient长连接 + 飞书卡片 + Claude CLI写稿）**

- 基于飞书 SDK WSClient 长连接模式，不需要公网 IP 或内网穿透
- 每日定时脚本：Claude CLI 生成选题 → 飞书云文档 → 飞书卡片推送
- 卡片回调触发自动写稿：Claude CLI 写稿 → format.py 排版 → publish.py 推送草稿箱
- 本地 HTTP 管理端口（9800）：发卡片、注册选题、健康检查

## v2.0（2026-04-15）

**完整合规审查机制融入全流程**

- 新增完整合规审查机制（法律法规+平台规则+处罚案例）
- 合规从"只在复审阶段做"升级为"贯穿全流程四个阶段"
- 新增 20 项合规检查清单（`compliance-checklist.md`）
- 新增独立合规检查命令（`/nsksd 合规检查`）
- 选题阶段新增 5 项合规预检 + 安全分级（🟢🟡🔴）
- 评分体系从四维度升级为五维度（新增合规安全度）

## v1.0（2026-04-15）

**初始版本**

- 五阶段内容工厂工作流：选题→标题→大纲→撰写→复审
- 77 份知识库原文件（核心文档 7 份、2025 新闻 20 份、历史新闻 49 份、大会策划 1 份）
- 12 个已验证选题 + 8 篇大会预热选题 + 7 种标题公式
- 写作风格规范：村口大爷原则、结论先行、口语化为王
