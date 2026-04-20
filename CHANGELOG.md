# 更新日志

## v8.4（2026-04-20）

**日本表述弱化 · 国际关系敏感期合规升级**

### 背景

客户反馈：当前国际关系敏感，用户对"日本"关键词存在情绪抵触，影响内容传播和转化。所有对外传播内容必须弱化日本概念，但不否认产品事实（仍然是海外原研、国际合作）。

### 核心变更

- **新增"日本表述弱化"硬约束**：禁用关键词 `日本/日式/日系/东瀛/和风/中日/日企/日资/日货/日产`
- **标准替代词表**：
  - "日本生物科学研究所" → "原研方 / 国际合作研发机构 / 海外专业研究机构"
  - "日本进口" → "国际原料 / 原研标准 / 进口原料"
  - "日本纳豆激酶" → "NSKSD纳豆激酶 / 原研级纳豆激酶"
  - "日本做过 XX 研究" → "一项 XX 人的临床研究 / 国际研究"
  - "中日论坛" → "国际学术论坛"
- **叙事切换**：从"异域光环"改为"科学循证"主场叙事——强调 1062 人临床、浙大 RCT、中国专家共识、中国循证医学数据
- **豁免场景**：产品包装 / 法律标签 / 学术论文原文引用 / 内部合规档案（保留事实表述，不对外传播）
- **合规文档三连更新**：三处规则同步落地，format-publisher 合规硬扫会拦截违规

### 修改文件

- `SKILL.md` — description 升级 + v8.4 升级说明 + 产品描述弱化日本表述
- `references/compliance.md` — 新增"第九章 日本表述弱化规则"（替换表 / 豁免场景 / 叙事策略 / 合规扫描关键词）
- `references/compliance-checklist.md` — 新增"第三B章 日本表述弱化检查"（5 项强制检查）
- `references/science-popular-style.md` — 新增"第八章 日本表述弱化"硬约束 + 修正 3 处示例
- `references/knowledge-base.md` — 6 处企业/产品/研究描述弱化
- `references/topic-library.md` — 2 处选题/标题公式改写
- `CHANGELOG.md` — 本条
- `README.md` — 版本号升级到 v8.4

### 不改动文件

- `knowledge/` 下的所有原始素材（央媒报道归档、企业资料原件）**保持原貌**，这是溯源依据，不能动
- 只改"生产规则层"（告诉系统"写新内容时怎么避开"）

### 设计决策

1. **为什么只改规则层不改知识库？**
   - 知识库是事实来源，改了会失真
   - 合规审查的 5 步验证法要求数据可溯源，原始素材必须保留
   - 规则层（references/）负责在生产阶段做"翻译转换"

2. **为什么叫"弱化"而不是"删除"？**
   - 产品是真实的海外原研合作，硬删会变成虚假宣传（另一个合规雷）
   - 弱化 = 表述改中性词，事实保留 = 合法且安全
   - 面向消费者讲"原研级 / 科学循证"，面向监管讲"海外原研事实"

3. **为什么不做关键词机械替换脚本？**
   - 语境决定替换方式："日本做过研究" 和 "日本 89.4% 的人吃纳豆" 替换逻辑不同
   - 写作 Agent 读规则文档学语义，比硬替换更稳
   - 合规硬扫兜底，把机械错漏挡在推送前

---

## v8.3（2026-04-20）

**单入口 + 模式持久化 + 定时 Step 1 + 配图升级**

### 核心变更

- **单入口 `/nsksd`**：取代 v8.2 的双入口，启动时按 `config.json` 中保存的 `default_mode` 自动跑
- **模式持久化**：新增 `scripts/mode_manager.py`，支持 `get/set/reset/show`，选择后写入 `config.json` 固化，不再每次问
- **口头切换即刻生效**：用户说"切换到引导模式/全自动模式"→ 主 Agent 调 `mode_manager.py set` 持久化，本次及后续都生效
- **定时任务改为只跑 Step 1**：LaunchAgent 每天 10:00 触发，**只生成选题 + 云文档 A + 推多选卡**，不再一口气跑到草稿箱（用户不在场时风险太大）
- **配图数量升级**：封面 1 张 + 内文 **5 张起步，上限 8 张**（原 2-3 张）。升级原因：单图内文视觉密度不够，公众号打开率偏低
- **双入口命令保留**：`/nsksd-auto` / `/nsksd-guided` 作为"切换并运行"快捷方式，兼容老用户

### 新增文件

- `scripts/mode_manager.py` — 模式管理 CLI（读写 `config.json` 的 `default_mode` 字段）

### 修改文件

- `config.json.example` — 新增 `default_mode` + `image_count.{cover,inline_min,inline_max}`
- `SKILL.md` — 单入口章节 + v8.3 升级说明 + 定时任务行为说明
- `agents/master-orchestrator.md` — 启动流程改为先读 mode + 识别切换意图
- `agents/image-designer.md` — 配图数改为 1+5~1+8
- `scripts/guard.py` — `new-session` 的 `--mode` 参数可选，缺省时自动读 `config.json`
- `scripts/run_nsksd_daily.sh` — 只保留 Step 1（选题 + 云文档 + 推卡 + 启动监听），删除后续自动推送
- `scripts/com.nsksd.daily-topics.plist` — 无变化（10:00 触发已正确）
- `README.md` — 重写，反映 v8.3 设计
- `CHANGELOG.md` — 本条

### 设计决策记录

1. **为什么定时任务只跑 Step 1？**
   - 10 点时用户大概率不在电脑前，封面效果、排版主题、合规边界都需要人眼确认
   - 跑到草稿箱风险大：万一配图不合适、标题踩雷，直接进了草稿也得重来
   - 改为"10 点把选题备好，等人来勾" → auto 模式也变成"半自动起点"，更可控
   - 勾完后 auto 会一路跑完，guided 会每步停下

2. **为什么模式持久化不让用户每次选？**
   - 同一个运营/客户基本只有一种工作习惯，每次问打断心流
   - 持久化后默认体验 = "/nsksd 直接开始"，切换成本 = "一句话"
   - 可恢复默认（`reset`），不锁死

3. **为什么配图升到 5-8？**
   - 公众号长文单图密度不足：读者滑动到文章中段容易流失
   - 5 张起步保证"每 300-500 字一张图"的节奏
   - 上限 8 张避免信息过载

---

## v8.2（2026-04-15）

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
- `agents/master-orchestrator.md` — 主调度 Agent
- `agents/topic-scout.md` — 选题侦察员
- `agents/title-outliner.md` — 标题大纲员
- `agents/article-writer.md` — 全文撰稿员
- `agents/image-designer.md` — 配图设计师
- `agents/format-publisher.md` — 排版推送员

**`scripts/` 新增**
- `scripts/guard.py` — 流程硬校验门控
- `scripts/topic_history.py` — 30 天滚动去重
- `scripts/interactive/docs_publisher.py` — 云文档 A/B/C 预审自动发布

**`references/` 新增**
- `references/science-popular-style.md` — 科普大白话写作规范
- `references/themes-curated.md` — 10 精选主题 + 自动映射

### 飞书卡片回调

- 长连接（WebSocket）基于 `lark_oapi.ws.Client`
- 卡片 schema 2.0 + `form` 容器 + `form_action_type: "submit"`
- 回调 3 秒内响应，写稿走异步避免超时

---

## v8.1（2026-04-10）

**飞书卡片长连接回调稳定版**

- WSClient 稳定回调
- 卡片灰底锁定
- `sessions/<SID>.json` 会话状态落盘

## v8.0（2026-04-01）

**重写为多 Agent 架构**

- 从单 Agent 工作流重写为多 Agent 调度
- 引入 artifacts 目录分步落盘
- 拆分 agents/ references/ scripts/ 三层
