---
name: nsksd-content
description: 日生研NSKSD纳豆激酶自媒体内容工厂Skill（v8.4）。当用户提到日生研、NSKSD、纳豆激酶的公众号选题、文章撰写、内容创作、招商文案、标题优化、大会宣传时，必须使用此Skill。v8.4 新增"日本表述弱化"硬约束（国际关系敏感期合规升级）。v8.3 能力保留：单入口 `/nsksd` + 模式持久化（auto/guided）+ 每天 10 点定时推 Step 1 选题卡 + 封面 1 张 + 内文 5-8 张配图 + 5 子 Agent 串行 + guard.py 硬校验门控 + 30 天去重 + 飞书卡片长连接回调。
---

# 日生研NSKSD纳豆激酶 · 自媒体内容工厂（v8.4）

> 品牌：日生研生命科学（浙江）有限公司
> 产品：NSKSD纳豆激酶（海外原研方 / 国际合作研发机构生产，日生研为中国总代理）
> 目标：通过自媒体内容吸引美容院老板、养生馆老板、社区门店老板成为分销商
> 内容策略：不直接卖货，通过行业洞察、科学背书、赚钱逻辑建立信任

---

## v8.4 核心升级（本版）

**日本表述弱化 · 合规硬约束**（国际关系敏感期应对）：

1. **强制替换**：所有对外内容禁止出现 `日本/日式/日系/东瀛/和风/中日/日企/日资/日货/日产` 等关键词
2. **标准替代**：
   - "日本生物科学研究所" → "原研方 / 国际合作研发机构"
   - "日本进口" → "国际原料 / 原研标准"
   - "日本纳豆激酶" → "NSKSD纳豆激酶 / 原研级纳豆激酶"
   - "日本做过 XX 研究" → "国际上做过 XX 研究 / 一项 XX 人的临床研究"
3. **叙事切换**：从"异域光环"改为"科学循证"主场叙事——突出 1062 人临床、浙大 RCT、中国专家共识
4. **豁免场景**：产品包装/法律标签/学术论文原文引用保留事实表述（面向监管/法务/学术溯源）
5. **guard 扫描**：`format-publisher` 的合规硬扫新增日本关键词检测，命中即拦截推送
6. **合规文档三连更新**：`compliance.md` 新增第九章、`compliance-checklist.md` 新增第三B章、`science-popular-style.md` 新增第八章

## v8.3 核心升级

1. **单入口 + 模式持久化**：主命令 `/nsksd`，首次启动让用户选模式（默认 `auto`），选择结果写入 `config.json` 并固化。之后每次 `/nsksd` 自动按保存模式跑。
2. **口头切换，即刻生效**：用户说"切换到引导模式 / 用全自动 / reset" → 通过 `scripts/mode_manager.py` 持久化切换，不需要改命令
3. **每天 10 点定时推 Step 1**：LaunchAgent 在 10:00 触发 `run_nsksd_daily.sh` → **只跑 Step 1**（生成 10 选题 + 云文档 A + 推多选卡到飞书）→ 用户勾选后再进入后续流程
4. **配图升级**：封面 1 张 + 内文 5 张起步，上限 8 张（原 2-3 张）
5. **双入口命令保留**：`/nsksd-auto` / `/nsksd-guided` 作为"切换并立即运行"的快捷方式，兼容老用法

## v8.2 延续能力

- 主 Agent `master-orchestrator` 去人名化，可被客户侧 Main Agent 接管
- 5 个子 Agent 严格串行：topic-scout → title-outliner → article-writer → image-designer → format-publisher
- `guard.py` 退出码硬门控
- 30 天三维指纹去重（title_hash + angle + data_points 交集 ≥ 2）
- 云文档 A/B/C 三次预审
- 科普大白话写作风格（`references/science-popular-style.md`）
- 10 主题精选多选卡 + 21 主题兜底

---

## 使用方式（v8.3）

### 主命令：`/nsksd`（按保存模式自动跑）

```
用户触发 /nsksd
  ↓
master-orchestrator 读 scripts/mode_manager.py get
  ├─ 首次运行（无 config.json）→ 创建并写入 default_mode: auto
  └─ 已有配置 → 直接读出 effective_mode
  ↓
告知用户："当前模式：auto/guided。切换说'切换到 xxx 模式'。"
  ↓
guard.py new-session（不带 --mode，自动读 config）→ SID
  ↓
按模式分支跑（见下）
```

### 模式切换（口头指令，持久化）

| 用户说 | 调用 | 行为 |
|--------|------|------|
| "切换到引导模式" / "用 guided" | `mode_manager.py set --mode guided` | 本次+默认都切成 guided |
| "切换到全自动" / "用 auto" | `mode_manager.py set --mode auto` | 本次+默认都切成 auto |
| "恢复默认" / "reset" | `mode_manager.py reset` | 恢复出厂默认（auto） |
| "当前什么模式？" | `mode_manager.py show` | 返回当前 + 默认 |

### 快捷入口（兼容老用法）

- `/nsksd-auto` ≡ `mode_manager.py set --mode auto` → `/nsksd`
- `/nsksd-guided` ≡ `mode_manager.py set --mode guided` → `/nsksd`

### 定时任务（每天 10:00 自动）

```
LaunchAgent com.nsksd.daily-topics (10:00 北京时间)
  ↓
run_nsksd_daily.sh
  ↓
【固定只跑 Step 1】不分 auto/guided
  ├─ 生成 10 个选题
  ├─ 创建飞书云文档 A（选题预审）
  ├─ 启动 WSClient 监听服务
  └─ 推送飞书多选卡（10 选题 + 10 排版主题）
  ↓
等用户勾选 → 后续流程按保存的 effective_mode 继续走
  ├─ auto：勾完一键跑到草稿箱
  └─ guided：每步云文档 B/C + 反馈卡
```

**设计考量**：10 点时用户大概率不在电脑前，直接跑完到草稿箱风险大（配图、主题可能不满意）；所以定时任务只做"选题准备 + 推卡"，等用户勾选后再启动后续。这样 auto 模式也变成"半自动起点"，更可控。

---

## 模式详细流程

### A. 全自动模式（`auto`，默认）

```
master-orchestrator (mode=auto)
  ├─ guard.py new-session  (读 config)
  ├─ dispatch(topic-scout) → artifacts/step1-topics.json
  ├─ 发飞书多选卡 → 等用户勾选
  ├─ guard.py confirm --step 1 --selected "1,3,5"
  ├─ dispatch(title-outliner) → step2-titles.json
  ├─ dispatch(article-writer) → step3-article.md
  ├─ dispatch(image-designer) → step4-images/（封面+5-8 张）
  ├─ dispatch(format-publisher) → 合规硬扫 → 推送草稿箱
  └─ 飞书通知：已入草稿箱 + 链接
```

### B. 引导打磨模式（`guided`）

每步结束都停下，发飞书**输入框卡片**等反馈：

```
master-orchestrator (mode=guided)
  ├─ Step 1: topic-scout → 云文档 A + 多选卡 → 🛑 等勾选+反馈
  ├─ Step 2: title-outliner → 云文档 B + 反馈卡 → 🛑 等确认
  │           └─ 若有修改意见：带 feedback 重跑（最多 3 次）
  ├─ Step 3: article-writer → step3-article.md → 🛑 等确认
  ├─ Step 4: image-designer → step4-images/（封面+5-8 张） → 🛑 等确认
  ├─ Step 5: format-publisher
  │           ├─ 推"排版主题多选卡"→ 等勾选
  │           ├─ 生成云文档 C（全文+配图+排版预审）
  │           └─ 推"最终确认卡"→ 等推送确认
  └─ 推送草稿箱 + 飞书通知
```

---

## 多 Agent 调度架构

### 角色分工（`agents/` 目录）

| Agent | 文件 | 职责 | 产出 artifact |
|-------|------|------|---------------|
| master-orchestrator | `agents/master-orchestrator.md` | 主调度：读模式 + 串行派发子 Agent + guard 校验 | `sessions/<SID>.json` |
| topic-scout | `agents/topic-scout.md` | 读知识库 + 查 30 天指纹 → 生成 20 候选 → 输出 10 个 S/A/B 级选题 | `step1-topics.json` |
| title-outliner | `agents/title-outliner.md` | 为选中选题生成 5 标题变体 + 6 段式大纲 | `step2-titles.json` |
| article-writer | `agents/article-writer.md` | 按科普大白话风格写 1500-2500 字全文 | `step3-article.md` |
| image-designer | `agents/image-designer.md` | **Bento Grid 封面 1 + 内文 5-8 张**配图 | `step4-images/meta.json` |
| format-publisher | `agents/format-publisher.md` | 主题选择 → format.py 排版 → 合规硬扫 → 推送草稿箱 | `step5-media_id.txt` |

### 主 Agent 约束（客户可接管）

> ⚠️ `master-orchestrator` 去人名化、可被客户侧 Main Agent 接管。
> 它只读 `SKILL.md` + `config.json` + `sessions/<SID>.json` + 对应 step 的 artifact 元数据。**禁止**全量读取 `knowledge/` 或 `references/` 下的长文档。
> 详细权限边界见 `agents/master-orchestrator.md`。

### 串行约束（guard.py 强制）

每个子 Agent 启动前**必须**执行：

```bash
python3 scripts/guard.py check --sid <SID> --step <N>
# 退出码 0 才能继续；非 0 直接终止（上一步未 confirmed）
```

---

## 脚本工具栏（`scripts/`）

| 脚本 | 用途 | 常用命令 |
|------|------|---------|
| `mode_manager.py` | **模式持久化（v8.3 新增）** | `get` / `set --mode <auto\|guided>` / `reset` / `show` |
| `guard.py` | 流程硬校验门控 | `new-session [--mode ...]` / `check --sid X --step N` / `confirm` / `mark-ready` / `status` |
| `topic_history.py` | 30 天滚动去重 | `check-duplicate --title "..." --angle "..."` / `register` / `cleanup` |
| `interactive/docs_publisher.py` | 云文档 A/B/C 预审发布 | `--step <1\|2\|5> --sid X` |
| `run_nsksd_daily.sh` | **定时任务脚本（v8.3 改为只跑 Step 1）** | 由 LaunchAgent 在 10:00 触发 |
| `com.nsksd.daily-topics.plist` | **macOS LaunchAgent（v8.3 定时）** | `launchctl load ~/Library/LaunchAgents/com.nsksd.daily-topics.plist` |
| `server/` | 飞书 WSClient 长连接 | `bun run index.ts` |

---

## 配置文件 `config.json`

```json
{
  "default_mode": "auto",          // v8.3 新增：持久化的默认模式
  "image_count": {                  // v8.3 新增：配图数量配置
    "cover": 1,
    "inline_min": 5,
    "inline_max": 8
  },
  "publish": {
    "account": "nsksd_official",
    "draft_box": true
  },
  "feishu": {
    "target_open_id": "ou_xxx",
    "app_id": "cli_xxx",
    "app_secret": "xxx"
  }
}
```

首次运行自动从 `config.json.example` 拷贝生成。

---

## 30 天滚动去重（三维指纹）

- **title_hash**：title 规范化后 MD5
- **angle**：核心角度关键词归一化
- **data_points**：论据数据点集合，交集 ≥ 2 视为重复

满足任一维度视为重复，topic-scout 自动剔除并补充。

## 云文档 A/B/C 三次预审

| 步 | 云文档 | 内容 | 时机 |
|----|--------|------|------|
| 1 | A · 选题预审 | 10 选题 + S/A/B 评级 + 五维评分 | auto & guided 都生成 |
| 2 | B · 标题大纲预审 | 选中选题的 5 标题 + 完整大纲 + 评估 | 仅 guided |
| 5 | C · 全文+配图+排版预审 | 撰稿正文 + 配图缩略图 + 选中主题渲染预览 | 仅 guided |

## 配图规范（v8.3 升级）

- **封面**：1 张 Bento Grid 风格，1080×1350（3:4 竖版）
- **内文**：**5 张起步，上限 8 张**，横版 1200×900 或方版 1080×1080
- 统一走 `generate-image` skill，风格参考 CLAUDE.md 中"曲率专用生图提示词"
- 详细规格见 `agents/image-designer.md`

## 写作风格

`references/science-popular-style.md` — 科普大白话
- 字数 1500-2500
- 6 段式结构（钩子 / 现象 / 科学 / 故事 / 机制 / 落地）
- 禁用词 + 禁用句式清单
- 破折号/感叹号限额
- 自查清单

## 合规硬扫（format-publisher 内置）

- 功效词白名单（不出现"治疗/治愈/根治/药"等医疗绝对化表述）
- 数据引用必须带来源
- 招商话术合规清单
- 违规则拦截推送，错误写入云文档 C 末尾

---

## 客户交付与客户侧接管

### 客户侧 Main Agent 接管

客户公司的 Main Agent 可以直接让 `master-orchestrator` 作为子 Agent 被调度：

1. 读 `SKILL.md` + `agents/master-orchestrator.md` 了解协议
2. 客户 Main Agent 发送 `/nsksd` 等价指令
3. 等待 `sessions/<SID>.json` 的 current_step 变化和 replies 回填

### 安装步骤

```bash
# 1. clone skill
git clone https://github.com/daknniel0881-png/nsksd-content-skill-private.git \
  ~/.claude/skills/nsksd-content

# 2. 复制 config
cd ~/.claude/skills/nsksd-content
cp config.json.example config.json
cp scripts/server/.env.example scripts/server/.env
# 编辑 .env 填入飞书凭据

# 3. 安装 LaunchAgent（10 点定时）
# 先编辑 plist 把路径换成实际路径
cp scripts/com.nsksd.daily-topics.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.nsksd.daily-topics.plist

# 4. 设定默认模式（可选，默认 auto）
python3 scripts/mode_manager.py set --mode auto --as-default

# 5. 手动首次运行验证
/nsksd
```

---

## 版本历史

- v8.4（2026-04-20）：日本表述弱化硬约束（国际关系敏感期合规升级）
- v8.3（2026-04-20）：单入口 + 模式持久化 + 定时 Step 1 + 配图 5-8 张
- v8.2（2026-04-15）：多 Agent 调度 + guard 硬门控 + 30 天去重 + 双入口
- v8.1（2026-04-10）：飞书卡片长连接回调稳定版
- v8.0（2026-04-01）：重写为多 Agent 架构

详细 Changelog 见 `CHANGELOG.md`。
