---
name: nsksd-content
description: 日生研NSKSD纳豆激酶自媒体内容工厂Skill（v8.2）。当用户提到日生研、NSKSD、纳豆激酶的公众号选题、文章撰写、内容创作、招商文案、标题优化、大会宣传时，必须使用此Skill。提供 /nsksd-auto（全自动）与 /nsksd-guided（引导式）双入口，基于 5 个串行子 Agent + guard.py 硬校验门控 + 30 天滚动去重 + 飞书卡片长连接回调的多 Agent 调度架构。即使用户只说"帮日生研写篇文章"或"出几个纳豆激酶的选题"，也应触发此 Skill。
---

# 日生研NSKSD纳豆激酶 · 自媒体内容工厂（v8.2）

> 品牌：日生研生命科学（浙江）有限公司
> 产品：NSKSD纳豆激酶（日本生物科学研究所生产，日生研为中国总代理）
> 目标：通过自媒体内容吸引美容院老板、养生馆老板、社区门店老板成为分销商
> 内容策略：不直接卖货，通过行业洞察、科学背书、赚钱逻辑建立信任

---

## v8.2 核心升级

1. **双入口**：`/nsksd-auto`（全自动，多选卡一键到草稿）+ `/nsksd-guided`（引导式，每步飞书卡片确认）
2. **主 Agent 去人名化**：主调度 Agent 名字为 `master-orchestrator`，不再绑定任何真人昵称，可被客户侧 Main Agent 接管
3. **5 个子 Agent 严格串行**：topic-scout → title-outliner → article-writer → image-designer → format-publisher，每个子 Agent 必须等上一步 artifact 就绪
4. **guard.py 硬校验门控**：退出码控制流程，禁止 Agent 跳步
5. **30 天滚动去重**：三维指纹（title_hash + angle + data_points 交集 ≥ 2）
6. **写作风格改用科普大白话**：不再引用任何个人写作风格，统一走 `references/science-popular-style.md`
7. **10 主题精选多选卡**：从 31 个主题里挑 10 个做卡片，剩余 21 个作为"其他主题"兜底
8. **云文档 A/B/C 三次预审**：选题预审 → 标题大纲预审 → 全文+配图+排版预审

---

## 使用方式（双入口）

### `/nsksd-auto`（全自动模式）

> 适合：熟手、定时任务、追求效率
>
> 流程：一张多选卡 → 选题 → 全自动到草稿箱 → 飞书通知

```
用户触发 /nsksd-auto
  ↓
master-orchestrator 调 guard.py new-session --mode auto  → 得 SID
  ↓
topic-scout 生成 10 个选题 → artifacts/<SID>/step1-topics.json
  ↓
发送「多选卡」（10 选题 + 10 排版主题）到飞书，等用户勾选
  ↓
WSClient 回调 → session.replies[1] 落盘
  ↓
title-outliner → article-writer → image-designer → format-publisher
  ↓
推送草稿箱 + 发送完成通知
```

### `/nsksd-guided`（引导式模式）

> 适合：新员工、需要逐步把控内容的场景
>
> 流程：每步推送一张飞书卡片 + 云文档预审，用户在输入框写反馈，主 Agent 根据反馈重跑该步

```
用户触发 /nsksd-guided
  ↓
master-orchestrator 调 guard.py new-session --mode guided  → 得 SID
  ↓
Step 1: topic-scout → 云文档 A（选题预审）+ 多选卡  → 🛑 等用户勾选+反馈
  ↓
Step 2: title-outliner → 云文档 B（标题大纲预审）+ 反馈卡  → 🛑 等用户确认
  ↓
Step 3: article-writer → step3-article.md  → 🛑 等用户确认
  ↓
Step 4: image-designer → step4-images/  → 🛑 等用户确认
  ↓
Step 5: format-publisher → 云文档 C（全文+配图+排版预审）+ 主题选择卡  → 🛑 等用户确认
  ↓
format.py 排版 → 合规硬扫 → 推送草稿箱 → 完成通知
```

---

## 多 Agent 调度架构

### 角色分工（`agents/` 目录）

| Agent | 文件 | 职责 | 产出 artifact |
|-------|------|------|---------------|
| master-orchestrator | `agents/master-orchestrator.md` | 主调度，读 SKILL.md + session 状态，串行派发子 Agent | `sessions/<SID>.json` |
| topic-scout | `agents/topic-scout.md` | 读知识库 + 查 30 天指纹 → 生成 20 候选 → 输出 10 个 S/A/B 级选题 | `step1-topics.json` |
| title-outliner | `agents/title-outliner.md` | 为选中选题生成 5 个标题变体 + 6 段式大纲 | `step2-titles.json` |
| article-writer | `agents/article-writer.md` | 按科普大白话风格写 1500-2500 字全文 | `step3-article.md` |
| image-designer | `agents/image-designer.md` | Bento Grid 风格生成封面 + 2-3 张配图 | `step4-images/meta.json` |
| format-publisher | `agents/format-publisher.md` | 主题选择 → format.py 排版 → 合规硬扫 → 推送草稿箱 | `step5-media_id.txt` |

### 主 Agent 约束（客户可接管）

> ⚠️ `master-orchestrator` 被设计为**去人名化、可被客户侧 Main Agent 接管**。
> 它只读 `SKILL.md` + `sessions/<SID>.json` + 对应 step 的 artifact，**禁止**全量读取 `knowledge/` 或 `references/` 下的长文档，避免拖爆上下文。
> 详细权限边界见 `agents/master-orchestrator.md`。

### 串行约束（guard.py 强制）

每个子 Agent 启动前**必须**执行：

```bash
python3 scripts/guard.py check --sid <SID> --step N
# exit 0 → 允许进入; exit 非 0 → 拒绝进入
```

guard.py 校验项：
1. 上一步 artifact 文件存在且非空
2. guided 模式下，上一步 `status == "confirmed"`；auto 模式下允许 `artifact_ready`

子 Agent 完成后（guided 模式），主 Agent 收到用户反馈时调用：

```bash
python3 scripts/guard.py confirm --sid <SID> --step N --user-reply "..." --selected "1,3,5"
```

---

## 脚本工具栏

| 脚本 | 用途 | 核心命令 |
|------|------|---------|
| `scripts/guard.py` | 流程硬校验门控 | `new-session --mode auto\|guided` / `check --sid --step` / `confirm --sid --step` / `mark-ready` / `status` |
| `scripts/topic_history.py` | 30 天滚动去重 | `load-30d` / `check --json '{...}'` / `append --json '{...}' --sid SID` / `mark --title-hash XX --status published` / `stats` |
| `scripts/interactive/docs_publisher.py` | 云文档 A/B/C 预审发布 | `publish --sid <SID> --step 1\|2\|5` |
| `scripts/interactive/lark_ws_listener.py` | 飞书长连接卡片回调 | `python3 lark_ws_listener.py`（守护进程） |
| `scripts/interactive/card_builder.py` | schema 2.0 卡片构造 | 被 listener 调用，不单独运行 |
| `scripts/interactive/session_manager.py` | 会话状态读写 | 被 listener 和 Agent 调用 |
| `scripts/format/format.py` | Markdown → 微信 HTML | `--input X.md --theme mint-fresh --no-open` |
| `scripts/format/publish.py` | 推送公众号草稿箱 | `--dir /tmp/wechat-format/X/ --title "..." --cover assets/default-cover.jpg` |
| `scripts/format/generate_image.py` | Gemini 配图 | `--prompt "..." --filename X.png --resolution 2K` |

---

## 30 天选题滚动去重（v8.2 新增）

`scripts/topic_history.py` 维护 `logs/topic-history.jsonl`，基于三维指纹做去重：

1. **title_hash**：标题去停用词 + SHA1 前 12 位
2. **angle**：核心角度字符串严格匹配
3. **data_points**：数据点集合重合 ≥ 2 视为重复

topic-scout 生成候选时**必须**先 `load-30d` 过滤：

```python
from topic_history import load_fingerprints_30d, check_topic
fp = load_fingerprints_30d()
for candidate in raw_candidates:
    hit = check_topic(candidate, fp)
    if hit["hit"]:
        continue  # 30 天内写过，丢弃
```

入库时机：
- 候选落盘 → `append_candidates(topics, sid=SID)`，状态 `candidate`
- 发到草稿箱 → `mark --title-hash XX --status published`

---

## 云文档 A/B/C 预审（v8.2 新增）

`scripts/interactive/docs_publisher.py` 在三个关键节点自动创建飞书云文档：

| 云文档 | 触发步骤 | 内容 | 用户操作 |
|--------|---------|------|---------|
| A · 选题预审 | step 1 完成 | 10 个选题 × S/A/B 分组 + 评分 + 合规 + 备选标题 | 在云文档评论区写意见，或直接在多选卡勾选 |
| B · 标题大纲预审 | step 2 完成 | 每个选题 5 个标题变体 + 6 段式大纲 + 改进建议 | guided 模式下在反馈卡写具体修改意见 |
| C · 全文+配图+排版预审 | step 5 完成（推送前） | 全文 Markdown 解析 + 配图清单 + 排版主题 | 最后一次确认，OK 则回复"推送" |

调用方式：

```bash
python3 scripts/interactive/docs_publisher.py publish --sid <SID> --step 1
# 输出: https://bytedance.feishu.cn/docx/xxx
# 同时写回 sessions/<SID>.json.docs[str(step)]
```

---

## 写作风格（科普大白话，`references/science-popular-style.md`）

> ⚠️ **客户侧使用铁律**：写文章时**绝对不要**引用任何个人写作风格。
> article-writer 子 Agent 只读 `references/science-popular-style.md`，定位为「像社区医生跟邻居唠嗑」。

核心约束（完整见 references 文档）：

- 字数 1500-2500 字，段落 ≤ 5 行
- **禁用词**：商业黑话（赋能/链路/飞轮/颗粒度/抓手/闭环/触达/矩阵/范式/护城河/底层逻辑/降维打击/生态位/心智模型/跃迁/复利）、AI 客套（综上所述/值得一提的是/无独有偶/众所周知/毋庸置疑/由此可见/总而言之）、模糊废话（很多/大部分/各种各样/若干/相关人士/有关专家/业内人士）
- **禁用句式**：「不是 X 而是 Y」「不仅 X 而且 Y」「一方面 X 另一方面 Y」「首先/其次/最后」连续出现
- **破折号**：整篇 `——` 或 `—` ≤ 2 个
- **感叹号**：整篇 `!` ≤ 3 个
- **每个数字必注出处**
- **6 段式标准结构**：钩子（50-80 字）→ 问题陈述（200-300 字）→ 科学证据（300-500 字）→ 产品衔接（200-300 字）→ 赚钱逻辑（200-400 字，招商向才写）→ 收尾（50-100 字）

---

## 排版主题（10 精选 + 21 兜底，`references/themes-curated.md`）

### 10 精选主题（多选卡默认展示）

| # | key | 中文名 | 调性 | 适用场景 |
|---|-----|--------|------|---------|
| 1 | `minimal-blue` | 简约蓝 | 偏科普 · 专业感 | 临床研究、科学原理 |
| 2 | `coffee-house` | 咖啡馆 | 偏温暖 · 生活化 | 品牌故事、用户案例 |
| 3 | `mint-fresh` | 薄荷清爽 | 偏科普 · 亲和 | 科普解惑、健康常识 |
| 4 | `magazine` | 杂志风 | 偏品质 · 权威 | 深度长文、行业洞察 |
| 5 | `ink` | 水墨 | 偏文艺 · 高级 | 品牌调性、传统文化 |
| 6 | `newspaper` | 报纸 | 偏正经 · 严肃 | 政策解读、合规内容 |
| 7 | `midnight` | 午夜黑 | 偏高级 · 极简 | 产品发布、重点公告 |
| 8 | `lavender-dream` | 柔雾紫 | 偏柔和 · 女性向 | 美容院、女性健康 |
| 9 | `minimal-gray` | 极简灰 | 偏清爽 · 中性 | 日常科普、短内容 |
| 10 | `focus-gold` | 专注金 | 偏重点 · 招商 | 分销招商、赚钱逻辑 |

### 内容线 → 主题自动映射（auto 模式）

```python
AUTO_THEME_BY_LINE = {
    "科学信任": "minimal-blue",  "临床证据": "minimal-blue",
    "行业洞察": "magazine",       "品牌故事": "coffee-house",
    "赚钱逻辑": "focus-gold",     "科普解惑": "mint-fresh",
    "政策解读": "newspaper",      "女性健康": "lavender-dream",
    "日常科普": "minimal-gray",   "重点公告": "midnight",
}
```

用户在多选卡点「🔍 查看全部 31 个主题」可展开兜底清单。

---

## 飞书卡片回调机制（v8.1 起稳定）

> 飞书已配置**长连接（WebSocket）**，不走 webhook URL。

- `scripts/interactive/lark_ws_listener.py` 守护进程监听 `card.action.trigger` 事件
- 卡片采用 schema 2.0 + `form` 容器 + `form_action_type: "submit"` + `required: false`
- 用户提交后回调结构：`event.action.form_value.{user_feedback, topic_1, topic_3, ...}`
- listener 提取 `form_value.user_feedback` → 写入 `sessions/<SID>.json.replies[step]`
- 返回灰底锁定卡（保留原标题 + 正文，按钮替换为"已提交"）

关键约束：
- 回调必须 3 秒内返回响应，写稿走异步
- form 内 checker **不配 behaviors**（否则 230099）
- input 组件**不得**设 `required: true`（会触发"请勾选"幽灵校验）

---

## 合规贯穿全流程

每一步都内置合规机制：

- **step 1 选题**：5 项合规预检 + 🟢/🟡/🔴 分级
- **step 2 标题**：5 项合规查 + 标题禁用清单
- **step 3 全文**：7 条写作护栏 + 禁用词实时排查
- **step 5 推送前**：最终合规扫描（8 项法律红线 + 6 项平台规则 + 6 项内容质量 + 禁用词扫描）

> 完整合规规则见 `references/compliance.md` + `references/compliance-checklist.md`。

---

## 独立功能：合规复审

```
/nsksd 复审 <文案>
/nsksd 合规检查 <文案>
```

不进入主流程，对任意文案执行 20 项完整合规检查（法律红线 8 项 + 平台规则 6 项 + 内容质量 6 项 + 禁用词扫描）。

---

## 知识库与参考文件

### knowledge/ — 完整知识库（77 份原文，**仅子 Agent 按需读取**）

| 目录 | 文件数 | 内容 |
|------|--------|------|
| `knowledge/核心文档/` | 7 份 | 企业介绍、百问百答、专家建议、专家共识、临床册子、科学循证文献合辑 |
| `knowledge/2025新闻/` | 20 份 | 2025-2026 年央媒报道 |
| `knowledge/2025之前/` | 49 份 | 2019-2024 年历史新闻报道 |
| `knowledge/FFC2026大会预热宣传策划.md` | 1 份 | FFC 大会预热策划 |

### references/ — 精华提炼（子 Agent 和主 Agent 都可读）

| 文件 | 内容 | 谁读 |
|------|------|------|
| `references/knowledge-base.md` | 知识库核心素材精华 | topic-scout / article-writer |
| `references/topic-library.md` | 已验证选题 + 标题公式 | topic-scout / title-outliner |
| `references/science-popular-style.md` | **科普大白话写作规范** | article-writer（唯一风格来源） |
| `references/themes-curated.md` | 10 主题精选 + 自动映射 | format-publisher |
| `references/compliance.md` | 合规红线、禁用词 | 所有子 Agent |
| `references/compliance-checklist.md` | 20 项合规清单 | 写作和复审时 |

---

## 数据引用规范

引用知识库数据时必须准确，常用数据点：

| 数据 | 正确表述 | 来源 |
|------|----------|------|
| 1062 人临床 | "迄今纳豆激酶领域最大规模临床试验，1062 人参与" | 科学循证文献合辑 |
| 斑块改善率 | "颈动脉斑块改善率 66.5%-95.4%" | 临床册子 |
| 认知衰退风险 | "视觉空间功能衰退风险降低约 65%" | 浙大 RCT 研究 |
| 专家建议 | "北京神经内科学会等 3 家学术机构、30 余位专家" | 专家建议原文 |
| FU 用量 | "10800FU/天（1062 人试验）或 8000FU/天（浙大 RCT）" | 对应研究论文 |
| EFSA 安全性 | "欧洲食品安全局 2017 年认证安全" | 科学循证文献 |

---

## 公众号推送流程（format-publisher 执行）

```bash
# 1. 排版
python3 scripts/format/format.py --input artifacts/<SID>/step3-article.md --theme minimal-blue --no-open
# 输出: /tmp/wechat-format/step3-article/

# 2. 推送草稿箱
python3 scripts/format/publish.py \
  --dir /tmp/wechat-format/step3-article/ \
  --title "文章标题" \
  --cover artifacts/<SID>/step4-images/cover.png

# 3. 回写 media_id
echo "$MEDIA_ID" > artifacts/<SID>/step5-media_id.txt
```

干净草稿铁律（推到草稿箱前必删）：
- 评分、分级标记（S 级/A 级/🟢/🟡）
- "本文由 AI 生成"等暴露 AI 身份的声明
- 合规检查结果、审查报告
- "免责声明""温馨提示"等模板化尾注
- 素材来源清单、参考文献列表

---

## 凭据自动配置（首次使用时 Agent 自动执行）

> ⚠️ **铁律**：所有凭据从配置文件读取，绝不硬编码。Agent 自动获取一切能自动获取的，只在必要时问用户。

| 凭据 | Agent 自动获取？ | 获取方式 |
|------|:---:|------|
| 飞书 App ID / Secret / Open ID | ✅ | `lark-cli config show` |
| 飞书 Chat ID | ✅ | `lark-cli im +chat-search --query "群名" --as bot` |
| 微信 App ID / Secret | ❌ | 问用户一次（无 CLI） |
| 微信 IP 白名单 | ⚠️ 半自动 | `curl ifconfig.me` 查 IP，提醒用户加白名单 |

完整流程见 `docs/credentials-auto-setup.md`。一键脚本：`bash scripts/setup-credentials.sh`。

---

## 定时任务与环境配置

- **Mac**：LaunchAgent plist，每天 10:00 触发
- **Windows**：Task Scheduler XML，每天 10:00 触发
- **首次配置**：`bash scripts/setup.sh`

> 详情见 `docs/scheduling.md` / `docs/setup.md` / `docs/onboarding.md`。

---

## 详细文档索引

| 文档 | 内容 | 何时阅读 |
|------|------|----------|
| `agents/*.md` | 6 个 Agent 角色提示词 | 子 Agent 启动时由 master-orchestrator 挂载 |
| `references/science-popular-style.md` | **科普大白话风格指南** | article-writer 必读 |
| `references/themes-curated.md` | 10 主题精选 + 自动映射 | format-publisher 必读 |
| `docs/diagrams/` | 架构图（总览/双模式/多 Agent/去重） | 理解整体流程时 |
| `docs/credentials-auto-setup.md` | 凭据自动配置 | 凭据未配置时 |
| `docs/feishu-cards-step-by-step.md` | 飞书卡片完整手册 | 修改卡片或调试回调 |
| `docs/wechat-publish-step-by-step.md` | 微信推送完整手册 | 推送草稿箱时 |
| `docs/formatting.md` | 排版系统、31 主题、配图 | 执行排版时 |

---

## 关键提醒

1. **纳豆激酶是食品，不是药品**。任何内容不得暗示治疗效果
2. **NSKSD 是具体品牌**，不等于"纳豆激酶"品类。临床数据仅针对 NSKSD 产品
3. **目标读者是门店老板**，不是消费者。内容要讲"赚钱逻辑"
4. **科普大白话原则**是最高优先级的写作标准（不再引用任何个人写作风格）
5. **引导模式不可跳步**。guard.py 硬校验会拒绝跳步
6. **30 天内不重复选题**。topic_history.py 三维指纹去重
7. **排版走 10 精选 + 21 兜底**。按内容线自动映射
