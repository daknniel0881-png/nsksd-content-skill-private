# nsksd-content-skill

> 日生研NSKSD纳豆激酶 · 自媒体内容工厂 Skill（V9.4）
> 客户专用版 · 零硬编码 · 独立部署 · 飞书云文档保底

**这是客户使用的 Skill，不依赖任何个人写作风格或个人凭证。**

---

## 这个 Skill 解决什么问题

日生研（NSKSD 纳豆激酶中国总代理）需要持续产出公众号内容，吸引美容院/养生馆/社区门店老板成为分销商。

传统做法：人工选题 → 写稿 → 配图 → 排版 → 推送，5-6 小时/篇，还容易撞题、踩合规红线。

本 Skill 的做法：

```
主命令 /nsksd  或  每天 10:00 定时触发
  ↓
5 个子 Agent 串行接力：选题 → 标题大纲 → 全文 → 配图 → 排版推送
  ↓
guard.py 硬门控 + 30 天滚动去重 + 合规硬扫
  ↓
飞书多选卡 + 长连接回调闭环 + 公众号草稿箱或飞书云文档保底
  ↓
草稿箱待发 ≈ 30 分钟/篇（auto 模式）
```

---

## V9.4 重要变更

- **彻底与 wechat-autopublish 解耦**：独立本地发布流水线，不依赖任何外部 skill
- **nsksd-writing-style 独立写作规则**：大白话+专业，不带任何个人签名句式
- **docs/playbooks/ 做事说明书矩阵**：7 个 playbook，遇到问题翻这里
- **CLI 引导配置**：`python3 scripts/setup_cli.py` 交互式填凭证，chmod 600
- **公众号凭证缺失自动保底**：飞书云文档兜底，内容不丢

---

## 快速开始

### 1. 安装

```bash
git clone https://github.com/daknniel0881-png/nsksd-content-skill-private.git \
  ~/.claude/skills/nsksd-content
cd ~/.claude/skills/nsksd-content
```

### 2. 配置凭证（首次必做）

```bash
python3 scripts/setup_cli.py
```

交互式引导填写：
- 微信公众号 app_id / app_secret（可选，缺失自动走飞书保底）
- 飞书机器人 app_id / app_secret / target_open_id / customer_open_chat_id

凭证保存到 `~/.nsksd-content/config.json`（chmod 600），仓库内零硬编码。

### 3. 启动飞书监听

```bash
# 安装依赖
cd scripts/server && bun install
# 或 npm install

# 启动 WebSocket 监听（后台运行）
cd /Users/xxx/.claude/skills/nsksd-content/scripts/interactive
nohup bash run_listener_mac.sh > /tmp/nsksd-listener.log 2>&1 &
```

### 4. 主命令

在 Claude Code 里说：

```
/nsksd
```

### 5. 定时任务（每天 10:00 自动推选题卡）

```bash
# 编辑 plist 中的路径（三处替换为实际路径）
vim scripts/com.nsksd.daily-topics.plist

cp scripts/com.nsksd.daily-topics.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.nsksd.daily-topics.plist

# 验证
launchctl list | grep nsksd
```

---

## 5 步流水线

```
选题生成（topic-scout）
  ↓ 飞书多选卡，用户勾选
标题大纲（title-outliner）
  ↓
正文撰写（article-writer）
  ↓ 按 references/nsksd-writing-style.md 写，大白话+专业
配图生成（image-designer）
  ↓ Bento Grid 风格，封面 1 张 + 内文 5-8 张
排版发布（format-publisher → nsksd_publish.py）
  ↓
公众号草稿箱（凭证正常）
或 飞书云文档保底（凭证缺失/推送失败）
```

---

## 公众号凭证缺失怎么办

不影响流水线运行。凭证缺失时自动走飞书云文档保底：

1. 文章内容创建为飞书云文档
2. 文档链接推送到飞书群
3. 运营人员复制内容手动发布

---

## 排版主题

10 个推荐主题（默认 `mint-fresh`），另有 21 个兜底主题。

用户说"换个排版"或"换主题"时自动弹出主题选择卡。

修改默认主题：
```bash
python3 scripts/setup_cli.py
# 或直接编辑 ~/.nsksd-content/config.json 的 settings.preferred_theme 字段
```

查看全部主题：`references/themes-curated.md`

---

## 遇到问题翻说明书

`docs/playbooks/` 目录下有 7 个做事说明书：

| 说明书 | 场景 |
|--------|------|
| [README.md](./docs/playbooks/README.md) | 总索引，快速定位 |
| [wechat-publish.md](./docs/playbooks/wechat-publish.md) | 公众号推送、403 报错、图片宽度 |
| [feishu-card.md](./docs/playbooks/feishu-card.md) | 飞书卡片乱码、trigger 文件流 |
| [feishu-doc.md](./docs/playbooks/feishu-doc.md) | 飞书云文档保底、权限配置 |
| [cover-image.md](./docs/playbooks/cover-image.md) | 配图生成、尺寸规范 |
| [data-verification.md](./docs/playbooks/data-verification.md) | 数据核查、找不到来源降级写法 |
| [style-card.md](./docs/playbooks/style-card.md) | 排版主题选择卡、31 个主题 |

---

## 两种工作模式

### `auto`（全自动，默认）

多选卡勾选 → 全自动跑完 5 步 → 草稿箱或飞书保底 → 飞书通知。
适合：熟手、定时任务、追求效率。

### `guided`（引导打磨）

每步停下发反馈卡，可以写意见 → 主 Agent 带反馈重跑（最多 3 次）。
适合：新员工、需要逐步把控内容质量。

切换模式：
```bash
python3 scripts/mode_manager.py set --mode guided   # 切换到引导模式
python3 scripts/mode_manager.py set --mode auto     # 切换到全自动
python3 scripts/mode_manager.py reset               # 恢复默认（auto）
```

或直接在对话里说"切换到引导模式"。

---

## 目录结构

```
nsksd-content/
├── SKILL.md                     # Skill 主入口（V9.4）
├── README.md                    # 本文档（客户视角）
├── CHANGELOG.md                 # 版本日志
├── config.example.json          # 配置模板（含所有字段说明）
├── agents/                      # 5 个子 Agent 提示词
├── docs/
│   └── playbooks/               # 做事说明书矩阵（7 个 playbook）
├── scripts/
│   ├── setup_cli.py             # CLI 引导首次配置凭证
│   ├── nsksd_publish.py         # 本地发布流水线（独立，不依赖外部 skill）
│   ├── mode_manager.py          # 模式持久化
│   ├── guard.py                 # 流程硬门控
│   ├── topic_history.py         # 30 天去重
│   ├── run_nsksd_daily.sh       # 定时任务（只跑 Step 1）
│   └── interactive/             # 飞书卡片交互组件
├── references/
│   ├── nsksd-writing-style.md   # NSKSD 写作规范（独立版）
│   ├── science-popular-style.md # 科普大白话写法
│   ├── compliance.md            # 合规规则
│   ├── title-playbook.md        # 标题手册
│   ├── topic-selection-rules.md # 选题六维坐标系
│   └── topic-library/           # 选题资料库（M1-M6 模块）
├── themes/                      # 排版主题（10 精选 + 21 兜底）
├── knowledge/                   # 产品知识库
└── logs/                        # 去重指纹 + 运行日志
```

---

## 更新日志

### V9.4（2026-04-21）

- 彻底与 wechat-autopublish 解耦，nsksd 完全独立运行
- 新增 `references/nsksd-writing-style.md`（大白话+专业，不带个人签名句）
- 新增 `docs/playbooks/` 做事说明书矩阵（7 个文件）
- 新增 `scripts/setup_cli.py` CLI 引导配置凭证（chmod 600）
- `config.example.json` 完整化，含 `preferred_theme` 字段和中文注释
- `trigger_watcher.sh` Step5 改走 `nsksd_publish.py`
- 清除 4 处 quyu-writing-style 残留引用

### V9.1（2026-04-21）

- bun + 飞书 CLI 自动安装授权
- 飞书多选卡片乱码防护（sanitizer + 13/13 测试）
- 选题库分块重构（M1-M6 资讯模块 + 月度归档）

### V9.0（2026-04-21）

- 选题六维坐标系 + 三层去重 + 标题手册 + 爆款语料库

### v8.4（2026-04-20）

- 日本表述弱化硬约束（国际关系敏感期合规升级）

### v8.3（2026-04-20）

- 单入口 /nsksd + 模式持久化 + 定时 Step 1 + 配图 5-8 张

---

## License

私有仓库，仅供日生研项目交付使用。
