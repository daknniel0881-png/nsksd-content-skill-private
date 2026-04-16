# 更新日志

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
