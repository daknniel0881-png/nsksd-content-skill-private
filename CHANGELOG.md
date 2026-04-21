# 更新日志

## [V9.4] - 2026-04-21

### 解耦
- 彻底与 wechat-autopublish skill 解耦，nsksd 完全独立运行
- 新增 references/nsksd-writing-style.md（大白话+专业，不带个人签名句）
- 清 4 处 quyu-writing-style 残留引用（trigger_watcher.sh / lark_ws_listener.py / send_notify.py）

### 新增
- docs/playbooks/ 做事说明书矩阵（7 个文件）：wechat-publish / feishu-card / feishu-doc / cover-image / data-verification / style-card + README 总索引
- scripts/setup_cli.py CLI 引导首次安装填凭证（chmod 600）
- config.example.json 完整模板，含 preferred_theme 字段和中文行内注释

### 变更
- trigger_watcher.sh Step5 改走 nsksd_publish.py（不再调 wechat-autopublish）
- run_nsksd_daily.sh 提示词去版本话术，接入热点文件，补严禁捏造数据条款
- SKILL.md V9.1 → V9.4，新增"遇到问题翻说明书"索引段

### 安全
- 5 处硬编码凭证已清空（V9.3 继承）：config.json / run_nsksd_daily.sh / lark_ws_listener.py / send_notify.py

---

## V9.1（2026-04-21）

**自动装 bun+lark CLI / 飞书乱码防护 / 选题库分块归档 / 4.16 PDF 入库**

### 背景

曲率四点反馈：
1. 飞书推送依赖 bun，客户电脑没装需要手动折腾——要求自动装
2. 飞书 CLI 授权也要无感——拿到 APP_ID/SECRET 自动完成
3. 下载了 `4.16-"颠覆性"认知对泛血管病防治影响与实践.pdf`，要原文入库 + 拆解选题点 + 图表识别
4. 选题库除了 S/A/B 分层，需要**分块归档**（健康行业/纳豆激酶研究/健康管理 等外部搜索），按月建子文件夹；招商场景（养生馆/美容院）必须**多角度**，严禁单一"卖产品→利润增长"
5. 飞书多选卡片偶发乱码，要代码级防护

### 核心变更

**1. bun + 飞书 CLI 自动安装授权**（痛点 1+2）
- `scripts/setup.sh`：bun 缺失自动 `curl -fsSL https://bun.sh/install | bash`，写 `.zshrc` PATH
- `scripts/setup.ps1`：Windows 走 `irm bun.sh/install.ps1 | iex`
- 两个脚本均自动 `bun install -g @larksuiteoapi/lark-cli`，npm fallback
- 新增 Step 3.6：读 `.env` 的 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`，自动 `lark config set` 或 `lark login`
- 新增 `docs/lark-cli-setup.md`：为什么装 / 自动流程 / 手动命令 / 常见错误表 / 品牌名硬约束（日生研三字）

**2. 飞书多选卡片乱码防护**（痛点 5）
- 新增 `scripts/server/utils/text-sanitizer.ts`
  - `sanitizeForFeishu(input, maxBytes=500)`：BOM / 零宽字符 / CRLF→LF / 控制字符 / HTML 尖括号 / UTF-8 安全字节裁剪
  - `truncateByBytes`：回退至 UTF-8 起始字节（`(bytes[end] & 0xc0) === 0x80`）防止切坏多字节
  - `safeStringify`：deepClean + JSON.stringify
  - `sanitizeOptionValue`：option.value 特殊字符（引号/反斜杠/控制字符）→下划线
  - `FEISHU_JSON_HEADERS`：强制 `Content-Type: application/json; charset=utf-8`
  - `buildOption(text, value)`：标准化 option 结构
- 新增 `scripts/server/utils/text-sanitizer.test.ts`：13 个 test 覆盖 BOM / 零宽 / CRLF / 控制字符 / HTML 转义 / null-undefined / emoji / 短文本原样 / 字节裁剪 / safeStringify / option 引号 / buildOption / 脏输入清洗
- **测试结果：bun test 13 pass, 0 fail, 19 expect() calls in 16ms** ✅

**3. 选题库分块重构**（痛点 4）
- 新增 `references/topic-library/README.md`：6 模块定义表 + 关键词映射 + 归档规则 + 与六维坐标系分层关系 + 附录 A 单条资讯 MD 模板
- 新增 6 个模块目录 + `2026-04/` 月度子文件夹：
  - M1 `industry-news` · 健康行业热点
  - M2 `nattokinase-research` · 纳豆激酶研究
  - M3 `health-management` · 健康管理
  - M4 `cases-stories` · 真实案例
  - M5 `policy-regulation` · 政策监管
  - M6 `partner-channels` · 招商场景
- **M6 8 角度硬约束**：店主专业形象升级 / 客户健康咨询能力 / 会员裂变粘性 / 产品组合设计 / 合规风险规避 / 跨品类联动 / 社群运营 / 门店动线话术
- 新增 `references/topic-library/M6-partner-channels/2026-04/example.md`：5 个 F 公式示例选题（F2 欲言又止 / F3 反常识 / F4 权威背书 / F6 类比 / F1 反差）
- 新增 `scripts/topic-crawler.ts`（bun+TS）：按 KEYWORDS 关键词池抓取，`bun scripts/topic-crawler.ts --module M2` 或 `--all`；搜索后端当前 stub，TODO 接 `exa_web_search` / `web_search_prime`
- `references/topic-selection-rules.md` 新增 V9.1 分块说明：资讯模块=原料池 / 坐标系=成品分布约束

**4. 4.16 PDF 入库**（痛点 3）
- 归档目录：`references/research-papers/2026-04-16-pan-vascular-disease/`
  - `original.pdf` · 原文 22MB / 82 页
  - `full-text.md` · 全文提取（分 8 批读取）
  - `topic-mining.md` · **25 条选题**（M1×8 / M2×2 / M4×7 / M5×3 / M6×5，S 级 6 / A 级 13 / B 级 6）
  - `key-data.md` · **47 项关键数据**（流行病学 7 / 分子特性 5 / 剂量效应 5 / 临床研究 11 / 炎症指标 3 / 权威背书 4 / 标题锚点 12）
  - `figures/page-*.png` · 96 张页面图（pdftoppm 150dpi 导出）
  - `README.md` · 产出索引
- 前 5 优先选题：
  1. T01 浙大 1062 人 RCT，认知衰退降 65%（M1/S，F1+F5）
  2. T02 纳豆激酶 vs 辛伐他汀 26 周颈动脉数据（M1/S，F4+F9）
  3. T03 三大选品标准——有人体临床 / 活性 FU / 权威背书（M6/S，F7+F8）
  4. T04 50% 心梗发生在 LDL 正常人群，炎症漏检（M4/S，F1+F2）
  5. T05 NSKSD 杭州一院 4 项核心数据（M1/S，F5+F1）
- 待曲率确认：T23（纳豆食物 vs 补剂）缺精确克重数据，发文前补查

### 受影响文件
- `scripts/setup.sh`、`scripts/setup.ps1`（Edit）
- `docs/lark-cli-setup.md`（新增）
- `scripts/server/utils/text-sanitizer.ts`、`text-sanitizer.test.ts`（新增）
- `references/topic-library/README.md`（新增）
- `references/topic-library/M{1-5}-*/2026-04/.gitkeep`（新增 5 个）
- `references/topic-library/M6-partner-channels/2026-04/example.md`（新增）
- `scripts/topic-crawler.ts`（新增）
- `references/topic-selection-rules.md`（Edit 加 V9.1 补充）
- `SKILL.md`（Edit 升级描述 + V9.1 章节）

---

## V9.0（2026-04-21）

**选题去重根治 + 标题手册 + 公众号爆款语料库 + 内部路由表 + 一键引导**

### 背景

客户反馈三大痛点：
1. **每天推送选题重复**——30 天指纹去重仍不够，同维度扎堆、同关键词反复命中
2. **引导界面链接缺失**——飞书/微信开放平台路径只有文字，不直达
3. **定时任务要手动配**——Mac/Windows 都要用户自己操作

同时曲率批量挑选了 25 篇阅读量破千/破万的公众号文章（含纳豆激酶/心脑血管领域），需要抓取原文 + 提炼共性作为写作参考底座。

### 核心变更

**1. 选题去重三层机制**（解决重复问题）
- 新增 `references/topic-selection-rules.md`
- 六维坐标系：M1医学循证/M2大会热点/M3节气养生/M4用户痛点/M5政策监管/M6产品科普
- 每日 5 选题必须覆盖 ≥3 维度，同维度 ≤2 条
- Layer 1：30天指纹去重（保留）
- Layer 2：维度周配额（新增）
- Layer 3：20 个禁用词 30 天冷冻窗口（新增）
- `logs/topic-history.jsonl` 扩展 `dimension` + `frozen_keywords` 字段

**2. 标题专项手册**（提升 80% 打开率的核心杠杆）
- 新增 `references/title-playbook.md`
- 10 条爆款公式（F1-F10）
- 日生研场景示例矩阵（公式 × 卖点）
- 5 条雷区（广告法/绝对化/恐吓/虚假权威/日本表述）
- A/B 决策树 + 五维评分（≥85 才进候选池）

**3. 公众号爆款语料库**
- 抓取 25 篇破千/破万阅读量文章 → `references/wechat-benchmark/raw/`
- `titles-corpus.md`：真实标题清单
- `titles-pattern-analysis.md`：标题共性分析（21 篇样本，7 公式 + 5 雷区 + SOP）✅
- `content-pattern-analysis.md`：正文共性分析（21 篇样本，6 段骨架 + 论据密度 + SOP）✅

**4. 内部路由表**（参考曲率 dispatcher 架构）
- 新增 `config/routing-table.yaml`
- 8 条路由（选题/标题/正文/合规/配图/发布/飞书卡片/模式切换）
- 按 trigger 硬编码加载对应 MD，替代暴力全量 Read references/
- 单路由最多加载 8 个文件，防止上下文爆炸

**5. 引导界面一键直达**
- `SETUP-GUIDE.md` + `docs/onboarding.md` 补：
  - 飞书开放平台一键启动：https://open.feishu.cn/page/launcher?from=backend_oneclick
  - 微信开发平台：https://developers.weixin.qq.com/console/product/mp/
- 三步授权流：点直链 → 复制 AppID/Secret → 粘贴 config.json

**6. 定时任务自动安装（OS 自动检测）**
- `scripts/setup.sh`（Mac）：自动 launchctl load + 改每日 10:00
- 新增 `scripts/setup.ps1`（Windows）：schtasks 注册 NSKSD-Daily-Topics 每日 10:00
- 安装脚本开头 `uname -s` 分流，不再询问用户

### 新增文件

- `references/topic-selection-rules.md` — 六维坐标系+三层去重+20禁用词
- `references/title-playbook.md` — 10公式+5雷区+A/B决策树
- `references/wechat-benchmark/raw/01-XX.md` ~ `24-XX.md` — 25 篇公众号原文（含已有 01/02/04）
- `references/wechat-benchmark/titles-corpus.md` — 标题语料
- `references/wechat-benchmark/titles-pattern-analysis.md` — 标题共性 21 篇终版 ✅
- `references/wechat-benchmark/content-pattern-analysis.md` — 正文共性 21 篇终版 ✅
- `config/routing-table.yaml` — 内部路由表
- `scripts/setup.ps1` — Windows 一键安装

### 修改文件

- `SKILL.md` — 版本升 V9.0 + V9.0 升级章节 + 路由表章节
- `SETUP-GUIDE.md` — 补飞书/微信开放平台直链
- `docs/onboarding.md` — 快速直达表 + 三步授权流
- `scripts/setup.sh` — 新增 Step 3.5 自动注册 launchd 定时任务
- `CHANGELOG.md` — 本条
- `scripts/topic_history.py` — 扩展 dimension/frozen_keywords 字段支持（配合 V9.0 规则）

### 不改动文件

- `knowledge/` 下全部原始素材保留（客户数据，溯源依据）
- `references/compliance.md` 及 v8.4 日本表述弱化规则全部保留

### 设计决策

1. **为什么选题去重做三层而不是一层更严的指纹？**
   - 单纯加严指纹会误杀（同一主题换角度写完全合理）
   - 三层 = 指纹挡重复 + 配额挡扎堆 + 冷冻窗挡高频词反复命中，层层过滤
   - 每层理由不同：指纹 = 内容重复；配额 = 结构单调；冷冻 = 读者疲劳

2. **为什么标题单独抽 MD 不放在 style 文件里？**
   - 标题决定 80% 打开率，值得单独拎出来做专项工程
   - title-outliner Agent 每次跑只需读 title-playbook + benchmark/titles-* 三个文件，上下文精准
   - 语料和公式拆开，一个是事实数据、一个是方法论，分层清晰

3. **为什么做路由表而不是继续全量加载？**
   - 现有 references/ 已经 10+ 文件，再加 V9.0 新增的 3 个 + benchmark/ 一堆原文，全量加载上下文会爆
   - 路由表 = 按需加载，单路由 ≤8 文件
   - 同时给 master-orchestrator 一个"意图识别 → 精准加载"的标准动作

---

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
