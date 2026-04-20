# nsksd-content-skill

> 日生研NSKSD纳豆激酶 · 自媒体内容工厂 Skill（v8.4）
> 多 Agent 调度 · 模式持久化 · 定时触发 · 飞书闭环 · 日本表述弱化合规

**v8.4 新增**：国际关系敏感期合规升级——所有对外内容强制弱化"日本/日式/中日"等关键词，改用"原研方/国际合作研发机构/NSKSD"中性表述。合规硬扫兜底。

---

## 这个 Skill 解决什么问题

日生研（NSKSD 纳豆激酶中国总代理）需要持续产出公众号内容，吸引美容院/养生馆/社区门店老板成为分销商。

传统做法：人工选题→写稿→配图→排版→推送，5-6 小时/篇，还容易撞题、踩合规雷。

本 Skill 的做法：

```
主命令 /nsksd  或  每天 10:00 定时触发
  ↓
5 个子 Agent 串行接力：选题 → 标题大纲 → 全文 → 配图 → 排版推送
  ↓
guard.py 硬门控 + 30 天滚动去重 + 合规硬扫
  ↓
飞书多选卡 + 云文档预审 + 长连接回调闭环
  ↓
草稿箱待发 ≈ 30 分钟/篇（auto）或 按需打磨（guided）
```

---

## v8.4 新能力（本版）

**日本表述弱化 · 合规硬约束**：当前国际关系敏感期，客户反馈用户对"日本"关键词有情绪抵触，影响传播转化。

- 禁用关键词：`日本/日式/日系/东瀛/和风/中日/日企/日资/日货/日产`
- 标准替代：原研方 / 国际合作研发机构 / NSKSD纳豆激酶 / 国际研究
- 叙事主场切换：从"异域光环"→"科学循证"（1062 人临床 + 浙大 RCT + 中国专家共识）
- 豁免：产品包装 / 法律标签 / 学术论文原引

合规规则已下发到 `references/compliance.md` 第九章、`references/compliance-checklist.md` 第三B章、`references/science-popular-style.md` 第八章。写作 Agent 和合规硬扫都会执行。

---

## v8.3 新能力

| 能力 | 说明 |
|------|------|
| **单入口 `/nsksd`** | 取代双入口，启动时自动按保存模式跑 |
| **模式持久化** | 首次选模式后写入 `config.json`，之后不再问 |
| **口头切换** | "切换到引导模式 / 全自动" → 持久化切换并即刻生效 |
| **10 点定时 Step 1** | LaunchAgent 每天 10:00 触发，只跑选题+云文档+推卡 |
| **配图 5-8 张** | 封面 1 张 + 内文 5 张起步，上限 8 张（原 2-3 张） |

---

## 快速开始

### 1. 安装

```bash
git clone https://github.com/daknniel0881-png/nsksd-content-skill-private.git \
  ~/.claude/skills/nsksd-content
cd ~/.claude/skills/nsksd-content

# 拷贝配置模板
cp config.json.example config.json
cp scripts/server/.env.example scripts/server/.env
# 编辑 .env 填入飞书 LARK_APP_ID / LARK_APP_SECRET / TARGET_OPEN_ID
```

### 2. 设默认模式（可选，默认 auto）

```bash
python3 scripts/mode_manager.py set --mode auto --as-default
# 或：--mode guided
```

### 3. 启动飞书长连接监听

```bash
cd scripts/server && bun install && bun run index.ts
```

### 4. 主命令

在 Claude Code 里说：

```
/nsksd
```

主 Agent 会：
1. 读当前模式（`auto` 或 `guided`）
2. 告知用户"当前模式：xxx，如需切换说'切换到 xxx 模式'"
3. 创建会话 → 派发子 Agent 按模式跑

### 5. 定时任务（每天 10:00）

```bash
# 编辑 plist 中的路径
vim scripts/com.nsksd.daily-topics.plist
# 替换三处 /tmp/nsksd-content-skill 为你的实际路径

cp scripts/com.nsksd.daily-topics.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.nsksd.daily-topics.plist

# 验证
launchctl list | grep nsksd
```

10:00 触发后会自动：
- 生成 10 选题 → 创建飞书云文档 A → 推多选卡
- 等用户勾选后，按保存的 `effective_mode` 继续走

---

## 模式切换（口头即刻生效）

| 用户说 | 实际调用 | 效果 |
|--------|---------|------|
| "切换到引导模式" | `mode_manager.py set --mode guided` | 本次 + 默认都切 guided |
| "切换到全自动" | `mode_manager.py set --mode auto` | 本次 + 默认都切 auto |
| "恢复默认" | `mode_manager.py reset` | 恢复 auto |
| "当前什么模式？" | `mode_manager.py show` | 返回当前+默认 |

---

## 两种模式差异

### `auto`（全自动，默认）

一张多选卡 → 勾选 → 全自动到草稿箱 → 飞书通知。
**适合**：熟手、定时任务、追求效率。

### `guided`（引导打磨）

每步停下发反馈卡，用户写意见 → 主 Agent 带 feedback 重跑该步（最多 3 次）。
**适合**：新员工、需要逐步把控内容、打磨精品。

---

## 架构一览

```
┌──────────────────────────────────────────┐
│  入口：/nsksd（单入口+模式持久化）       │
│        或 LaunchAgent 10:00 → Step 1     │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│  master-orchestrator（主调度，去人名化） │
│  - 读 mode_manager 得模式               │
│  - guard.py new-session 建会话          │
│  - 串行派发 5 子 Agent                  │
└──────────────────────────────────────────┘
              ↓ 严格串行，guard 退出码门控
┌──────────────────────────────────────────┐
│  topic-scout → title-outliner →         │
│  article-writer → image-designer →      │
│  format-publisher                        │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│  飞书闭环：云文档 A/B/C + 多选卡/反馈卡  │
│  + 长连接 WSClient 回调 + 推送草稿箱     │
└──────────────────────────────────────────┘
```

---

## 目录结构

```
nsksd-content/
├── SKILL.md                    # Skill 主入口（单入口 + 模式说明）
├── README.md                   # 本文档
├── CHANGELOG.md                # 版本日志
├── config.json.example         # 配置模板（含 default_mode / image_count）
├── agents/                     # 6 个 Agent 提示词
│   ├── master-orchestrator.md
│   ├── topic-scout.md
│   ├── title-outliner.md
│   ├── article-writer.md
│   ├── image-designer.md       # v8.3：封面 1 + 内文 5-8
│   └── format-publisher.md
├── scripts/
│   ├── mode_manager.py         # v8.3 新增：模式持久化
│   ├── guard.py                # 流程硬门控
│   ├── topic_history.py        # 30 天去重
│   ├── run_nsksd_daily.sh      # v8.3：只跑 Step 1
│   ├── com.nsksd.daily-topics.plist  # macOS LaunchAgent
│   ├── interactive/
│   │   └── docs_publisher.py   # 云文档 A/B/C
│   └── server/                 # 飞书 WSClient (bun+TS)
├── references/                 # 长文参考（子 Agent 自读，主 Agent 禁读）
│   ├── science-popular-style.md
│   ├── themes-curated.md
│   ├── compliance.md
│   ├── knowledge-base.md
│   └── topic-library.md
├── knowledge/                  # 原文知识库（77 份）
├── themes/                     # 排版主题（10 精选 + 21 兜底）
├── templates/                  # 文章/图片模板
├── sessions/                   # 会话状态（SID.json）
├── artifacts/                  # 每步产物
└── logs/                       # 去重指纹 + 运行日志
```

---

## 为什么这么设计

1. **主 Agent 去人名化** → 客户侧 Main Agent 可以直接接管，不绑定任何运营个人
2. **5 子 Agent 串行 + guard 门控** → 避免并行乱序，每步都有明确的 artifact 落盘
3. **模式持久化** → 同一个运营基本只用一种模式，每次问打断心流
4. **定时只跑 Step 1** → 10 点人不在场，选题备好等勾选比直接跑到草稿更安全
5. **30 天指纹去重** → 公众号最怕撞题，三维指纹（title+angle+data）防撞
6. **云文档 A/B/C** → 飞书云文档留痕 + 评论 + 移动端可审，比 markdown 导出友好
7. **合规硬扫** → 保健品赛道合规红线高，format-publisher 内置拦截

---

## License

私有仓库，仅供日生研项目交付使用。
