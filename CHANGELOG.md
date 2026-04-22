# 更新日志

## [V10.3] - 2026-04-22 · 引用来源规范硬门控 + 括号来源灰化 + 图内禁英文 + 配图必要性

### 背景

客户实际阅读时发现两类"AI 味"问题：
1. **引用来源不规范**：模型喜欢在每段后面加「（来源：同上）」这种模糊回指；或者用「袁总 / 老袁 / 张老师」这种亲昵称谓代替人的原名
2. **配图英文 + 装饰化**：生图模型（NanoBanana/GPT Image 2）对中文渲染无压力，但配图里仍然混杂英文（Nattokinase / RCT / Before-After）；且"为了美观配图"而不是"为了解释文章配图"，图没有衍生解释义务

### 新增

- **`scripts/citation_check.py`**：第三道发布前硬门控，扫三项
  - `honorifics`：括号来源 / 作者行里的亲昵称谓（袁总 / 老袁 / 张老师）
  - `vague_backref`：「来源：同上 / 同前 / 见上 / 同 N」模糊回指
  - `half_width_source`：半角括号 `(来源: xxx)`（破坏 format.py 自动灰化钩子）
  - 退码 0=通过 / 1=违规 / 2=文件错
- **`docs/playbooks/citation-source-naming.md`**：引用来源命名完整 playbook
  - 核心三规则（人原名 + 具体出处 + 全角括号）
  - format.py 自动灰化原理 + 客户看到的渲染效果
  - citation_check 扫描表 + 误伤 FAQ + 红线

### 修改

- **`scripts/format/format.py::gray_out_source_citations`**（新函数）：
  - 匹配 `（来源：XXX）`/`（出处：XXX）`/`（引自：XXX）`/`（参考：XXX）` 全角括号
  - 自动包 `<span style="color:#9aa0a6;font-size:0.92em">...</span>`
  - 在 `convert_image_captions` 末尾调用，4 个发布通道自动受益
- **`scripts/interactive/trigger_watcher.sh` Step 4.5**：
  - 三门控变四门控：layout → data_audit → **citation_check（新）** → image_size_check
  - 违规状态码 `rejected_citation_check`
- **`agents/image-designer.md`**：
  - 图内英文白名单收紧到仅 `NSKSD` + `FU`，其他所有英文必须翻中文（Nattokinase→纳豆激酶，RCT→临床试验，Before/After→服用前/服用后）
  - 新增「配图必要性原则」：7 必配场景（概念示意 / 数据可视化 / 机制拆解 / 对比反差 / 结构层级 / 时间线 / 行动引导）vs 4 禁配场景（纯观点 / 过渡 / 列表 / 强调）
  - 新增「衍生解释义务」：图信息量 ≥ 文字信息量，`meta.json.figures[].reason` 必填
- **`references/nsksd-writing-style.md`**：新增第 8B 节「引用来源规范」三条规则表 + automation 指引
- **`SKILL.md`** frontmatter：V10.2 → V10.3

### 验证

- `citation_check.py` 单测：`/tmp/test_article.md` 精准捕获 3/3 违规（袁总采访 / 来源：同上 / —— 袁总）
- `gray_out_source_citations` 单测：3/3 HTML case 正确包 gray span
- 正文里「张伟东老师讲过」不误伤（只扫括号来源 + 作者行）
- 「老中医」「工程师」等不误伤（HONORIFIC_SUFFIX 移除单字"师"）

---

## [V10.2] - 2026-04-22 · 公众号图片不裂 + 飞书云文档客户可读

### 背景

客户实际使用暴露两个严重问题：
1. **公众号草稿箱图片全部裂开**：本地相对路径直接塞进 `content`，微信服务器访问不到本地文件
2. **飞书云文档只有 bot 能读**：`lark-cli docs +create --as bot` 把文档 full_access 分给 CLI 用户（曲率自己），客户打开是 403

### 新增

- **`docs/playbooks/wechat-image-handling.md`**：公众号图片推送完整调用链
  - access_token → 封面上传（add_material）→ 内文图上传（uploadimg）→ content 替换 → draft/add
  - 每步的 HTTP method / Content-Type / 关键参数速查表
  - 6 条调试清单（裂图时照着走）
- **`docs/playbooks/feishu-doc-permissions.md`**：飞书云文档权限授权完整路径
  - 创建文档 → `drive permission.members create` 分发权限
  - member_type 前缀对照表（ou_ / oc_ / on_）
  - chat_id / open_id 获取办法
  - perm 字段取值与 perm_type 说明

### 修改

- **`scripts/lib/wechat_publish_core.py::replace_all_images`**：
  - 支持双引号/单引号/无引号三种 `src=` 写法（原只处理双引号）
  - 自动去 `./` 前缀
  - 上传失败场景打 `[wechat-img] FAIL` stderr 日志，方便定位
  - `data:` URI 显式跳过（原会误判为本地路径）
- **`scripts/lib/feishu_doc_publish.py`**：
  - `create_fallback_doc()` 改返回 `(doc_url, doc_token)` 元组
  - 新增 `share_doc_to_customer(doc_token, members, perm)`，调 `drive permission.members create`
- **`scripts/nsksd_publish.py`**：
  - 创建文档后自动授权：客户群（chatid）+ 曲率 admin（openid）→ edit 权限
  - 通过 config 的 `customer_open_chat_id` 和 `target_open_id` 自动判断 member_type
- **`SKILL.md`** frontmatter：V10.1 → V10.2

### 验证

`replace_all_images` 单测 5 个场景全过：
- 双引号 + `./` 前缀 → 替换成 mmbiz CDN
- 单引号 → 保持单引号格式
- 无引号 → 补双引号
- 已是 mmbiz URL → 跳过
- 本地找不到 → 保持原样 + stderr 日志

---

## [V10.1] - 2026-04-22 · 图片规则硬门控（尺寸 + 数量 + 中文优先）

### 背景

此前配图规则只口头约定，AI 出图常见三大病灶：
1. 公众号封面尺寸写成 900×500（错的，实际 900×383）
2. 小红书/视频封面完全没定义
3. 内文配图数量参差、图内文字经常英文主导

### 新增

- **`scripts/image_size_check.py`**：Pillow 实现的图片硬门控，三道扫描
  - `cover-wechat.png` 必须 900×383
  - `cover-xhs.png`（若存在）必须 1242×1660
  - `figure-*.png` 数量硬下限 3 张 / 上限 8 张
  - 可选 `--ocr` 启用 pytesseract 做图内中英文比例扫描（英文主导直接 fail）
  - 向后兼容旧命名 `cover.png`（带 warning）
  - 退出码：0 通过 / 1 违规 / 2 文件错

### 修改

- **`scripts/interactive/trigger_watcher.sh`**：Step 4.5 三门控（layout_check → data_audit → **image_size_check**），图片不合规 trigger.status 打 `rejected_image_check`，不发 IM、不落盘
- **`agents/image-designer.md`**：
  - 配图数量改为"3 张硬下限 / 5 张标配 / 8 张上限"（原先 5 张起步）
  - 新增 V10.1 尺寸硬规范表（公众号 900×383 / 小红书 1242×1660）
  - 新增 V10.1 图内文字硬规范（中文优先，英文仅限品牌词/括号内单位）
  - 提示词模板拆 B.1 公众号封面 / B.2 小红书竖封面 / B.3 内文配图三套
  - 落盘文件名 `cover.png` → `cover-wechat.png` + `cover-xhs.png`
- **`docs/playbooks/cover-image.md`**：同步 V10.1 尺寸 + 数量 + 中文优先三条硬规矩
- **`SKILL.md`** frontmatter：版本号 V10.0 → V10.1，description 更新为 5 点升级

### 发布规则

图片硬门控是发布前第三道闸门，和 layout_check / data_audit 并列：任一不过直接退回重生成，不发公众号。

---

## [V10.0] - 2026-04-22 · 数据事实硬门控 + S 级种子选题库 + Windows 选题引擎修复

### 背景

第十二次 / 十三次客户沟通同时暴露三个病根：
1. 模型引用数据时会偷懒瞎编"据研究/有数据显示"，**核查机制只存在于 playbook，没落到代码门控**
2. Windows 定时任务跑出 <10 条选题 + 角度单一 + 飞书消息没推送
3. 客户团队已有一篇蓝皮书级政策权威文章（海斌 2025-06-26 原文），但 skill 不知道它的存在，每天从零选题

### 新增

- **`scripts/data_audit.py`**：数据事实硬门控，六道扫描（数字断言缺源 / 医广绝对化 / 日本禁词 / 捏造信号短语 / FU 单位错写 / 孤证健康陈述），退码非 0 阻塞发布
- **`references/external-articles/mp.weixin.qq.com/landmark-articles-2026-04-22-bluebook-nsk/`**：S 级种子选题库
  - `bluebook-nsk-national-guidance.md` 海斌原文
  - `bluebook-nsk-national-guidance-captured.html` HTML 存证
  - `SEED-TOPICS.md` 拆解 13 条政策权威选题 + 10 条一级权威事实 + 交叉验证配对表 + 5 条禁止混搭红线

### 修改

- **`scripts/interactive/trigger_watcher.sh`**：发布前 Step 4.5 双门控（layout_check → data_audit），任一失败 trigger.status 打 `rejected_layout` / `rejected_data_audit`，不发 IM、不落盘
- **`scripts/daily-topics.ps1`**（I 组 6 条 Windows 修复）：
  - I-1 修 L136 字面量传参 → `$prompt | & claude -p` 走 stdin
  - I-2 prompt 加"不足 10 条必须派生同维度变体补齐"
  - I-3 回补"≥5 维度 + 5 类句式（主张/疑问/数字/场景/对比）各 1"
  - I-4 路径 POSIX 化（`$SKILL_DIR_POSIX`）再注入 prompt
  - I-5 JSON 解析分级 exit code（2=解析失败、3=<10 条）
  - I-6 最多 3 次尝试（1 正式 + 2 重试），仍不足则 Die
- **`references/data-verification.md`** v9.3 → v10.0：
  - 新增"选题阶段核查"章（topic-scout 读规则再选题，禁止幻觉信号短语进选题卡）
  - 新增"蓝皮书权威事实白名单"10 条（免交叉验证，只需标注蓝皮书一次）
  - 新增"数据事实硬门控"章说明 data_audit.py 六道扫描
- **`SKILL.md` frontmatter**：V9.9 → V10.0，description 扩写 5 点升级

### 测试

```bash
# 坏样本（12 项违规）
python3 scripts/data_audit.py /tmp/test-audit-bad.md
# → 退码 1，打印 12 条命中

# 好样本（2 条带源，1 条 authority_level=1）
python3 scripts/data_audit.py /tmp/test-audit-good.md
# → 退码 0
```

### 客户可见变化

- 文章里出现"治疗/治愈/根治/4000 mg/日本进口/据研究"等红线 → 发布流水线自动拦截，不再需要人工审
- 选题卡不再出现无出处的"据研究降低 XX%"幻觉数字
- 每日 10 点 Windows 选题保底 10 条、5 维度、5 类句式、飞书消息硬推送
- 蓝皮书事实进入白名单，所有作者引用时标注统一，不再各写各的

---

## [V9.9] - 2026-04-22 · 文章排版硬约束

### 背景

客户端反馈："现在写出来的文章，一大段大段文字，段落应该有适当分段，中间也缺很多小标题。写公众号文章应该有小标题，写到飞书云文档里也应该有小标题分区分块，它应该是完整文章结构，可读性好。"

根因：V9.4 版 `nsksd-writing-style.md` 第 4 节明确写了"用 ---- 或空行切换段落，不用 # 标题堆砌结构"，把小标题路径堵死；段落上限也只写了"≤ 5 行"没限字数。

### 新增

- **`scripts/layout_check.py`**：文章排版自查脚本，硬门控 `##` 小标题 3-6 个 + 段落字数 ≤ 100 + 目录词黑名单，退码非 0 阻塞发布

### 修改

- **`references/nsksd-writing-style.md` 第 4 节**：改为"段落不超过 100 字 + 必须有 3-6 个 `##` 二级小标题"，给出好/坏小标题示例
- **`references/science-popular-style.md` 第二节**：新增"段落与小标题"硬约束段
- **`agents/article-writer.md`**：
  - "写作硬约束"新增段落字数 + 小标题铁律
  - "步骤 B 六段撰写"每段注明是否起 `##` 小标题，附示例
  - "自查"从三轮升级为五轮，新增第 5 轮"段落+小标题扫描"
  - frontmatter 扩 `subheading_count` / `max_paragraph_chars` / `paragraph_overflow_count` 三字段

### 验收

```bash
# 坏样本：145 字段落 + 0 小标题 → 退码 1
python3 scripts/layout_check.py /tmp/bad_article.md

# 好样本：34 字段落 + 3 小标题 → 退码 0
python3 scripts/layout_check.py /tmp/good_article.md
```

---

## [V9.8] - 2026-04-22 · Windows 适配大修

### 新增

- **`scripts/daily-topics.ps1`**：Windows 每日 10:00 定时任务入口，对标 macOS 的 `run_nsksd_daily.sh`，4 步流水线（选题生成 / 多选卡构造 / listener + 推卡 / watcher 守护）全走 PowerShell + Python，UTF-8 强制，`Load-Credentials` 从 `~/.nsksd-content/config.json` 或 `scripts/.env` 自动注入凭证
- **`scripts/setup_cli.ps1`**：Windows 交互式配置包装器，取代让用户手动编辑 config.json 的反 Agent 模式
- **`docs/playbooks/windows-troubleshooting.md`**：整本 Windows 排障说明书，9 大类坑（Bash 路径坑 / 中文乱码 / 定时脚本缺失 / 飞书 URL / 凭证未注入 / 多选卡回调 / 安全软件误报 / venv 失效 / 完整 Checklist）

### 修复（14 条客户端测试踩坑 · 来源 `nska-windows-test-report.md`）

| # | 问题 | 修法 |
|---|------|------|
| 1 | `daily-topics.ps1` 缺失，`setup.ps1` Step 3.5 报错 | 新建文件 |
| 2 | 缺少自动初始化逻辑 | `setup.ps1` 已幂等注册 schtasks，无需用户手动 |
| 3 | 飞书开放平台 URL `open.feishu.cn/app` 会 404 | `setup_cli.py` 改为 `open.feishu.cn/page/launcher?from=backend_oneclick` |
| 4 | 配置流程反 Agent（让用户手动编 config.json） | 新增 `setup_cli.ps1` 交互式包装 |
| 5 | `target_open_id` 硬编码 | `setup_cli.py` 交互收集 + `send_notify.py` 从 config 兜底 |
| 6 | 飞书 API 认证流程错用 MCP 工具 | `send_notify.py` 用 tenant_access_token 直连 HTTP |
| 7 | Bash 工具在 Windows 上路径无限循环 | `windows-troubleshooting.md` 固化官方解法：重装 Git for Windows |
| 8 | `send_notify.py` 只支持 `--chat-id` | 改为 `--chat-id` / `--open-id` 互斥参数组，自动识别 `receive_id_type` |
| 9 | 安全软件把 `.ps1` 误报为蠕虫 | `windows-troubleshooting.md` 提供白名单 + PS2EXE 两套方案 |
| 10 | 缺飞书 CLI 自动安装流程 | `setup.ps1` Step 1 已内置 `bun install -g @larksuiteoapi/lark-cli` 幂等自动安装 |
| 11 | 飞书消息中文乱码 `���` | 全链路 UTF-8 强制：`daily-topics.ps1` 开头 `chcp 65001` + `PYTHONIOENCODING=utf-8`；`send_notify.py` `sys.stdout = TextIOWrapper(..., encoding='utf-8')`；HTTP 请求 `Content-Type: application/json; charset=utf-8` + `ensure_ascii=False.encode('utf-8')` |
| 12-A | `run_listener_win.bat` venv 路径硬编码 `bad interpreter` | 重写后启动前校验 `venv/Scripts/python.exe`，失效自动重建 |
| 12-B | `ModuleNotFoundError: lark_oapi` | 启动前 `python -c "import lark_oapi"`，缺失自动 `pip install lark-oapi` |
| 12-C | listener 环境变量未注入 `LARK_APP_ID` | 启动前从 `config.json` + `.env` 自动注入到环境变量 |
| 13-14 | PowerShell 无法被 Claude Code 直接调用 | 设计上 Skill 不依赖 Bash 工具，PowerShell 脚本由 schtasks 触发 |

### 代码变更

- `scripts/setup_cli.py`：飞书开放平台 URL 修正
- `scripts/interactive/send_notify.py`：`--chat-id` / `--open-id` 互斥参数组、UTF-8 stdout 强制、config.json 兜底读、HTTP 请求固定 `charset=utf-8`
- `scripts/interactive/run_listener_win.bat`：完全重写（~105 行），加凭证注入 + venv 校验 + 依赖自愈 + 精准 stop/restart
- `SKILL.md`：frontmatter description 加 V9.8 要点、V9.8 核心升级章节、Windows 安装 Checklist

### 待测（下一轮）

- [ ] Windows 客户端把本版 pull 下来重跑 14 条测试场景
- [ ] 确认飞书多选卡回调在新 `run_listener_win.bat` 下稳定触发
- [ ] 确认 `daily-topics.ps1` schtasks 触发后日志完整

---

## [V9.7] - 2026-04-21

### 新增（标题选题方法论大融合）
- **`references/title-playbook.md` 全文重写 V9.0 → V9.7**：45 爆款公式 = F1-F10 本地原有 + F11-F40 DBS 9 大类 30 公式 + F41-F45 全网爆款 5 补充；张力 6 维命中 ≥3 项硬门控；三库禁用词扫描；中老年 5 风格偏好；数字+痛点公式 +27% 打开率数据支撑
- **`references/topic-selection-rules.md` 全文重写 V9.1 → V9.7**：六维坐标系 M1-M6 扩容为八维 M1-M8（新增 M7 招商场景 / M8 名人古法）；硬约束 M7 ≤1/日、M6+M7 ≤2/日、C 端维度 ≥60%、主人群（门店/美容院/养生馆/分销商）≤1/日；反面示例黑名单 4 类
- **`references/knowledge-base.md` 第九章扩容**：C 端 6 类画像 + B 端 6 类画像 + C 端 70% / B 端 30% 硬比例
- **`docs/playbooks/topic-title-workflow.md` 新增**：E2E 7 步工作流图 + 硬约束速查表 + CLI 调用示例 + 4 类踩坑记录 + V9.7 变更对照

### 修复（5 个根因级 bug · 来自选题重复审计报告）
- **root-cause 1**：`SKILL.md` 北极星口径"目标=美容院老板+养生馆老板+门店老板成为分销商" → LLM 永远朝门店对齐。修法：改为"C 端消费者科普 70% + B 端招商场景 30%"
- **root-cause 2**：`logs/topic-history.jsonl` 不存在 → 三层去重"全部通过"实则空转。修法：`topic_history.py` 启动 `HISTORY_FILE.touch()`
- **root-cause 3**：三层去重纸面约束，无代码执行。修法：`check_dimension_quota()` + `check_frozen_keywords()` 代码化，CLI 子命令 `check-quota` / `check-frozen` 暴露给 prompt 调用
- **root-cause 4**：`title-playbook.md` 从未被 `run_nsksd_daily.sh` 加载进 prompt。修法：Step 1 prompt 重写，必读三件套包含 title-playbook.md
- **root-cause 5**：冷冻词池只有 20 个且不含门店 B 端词。修法：扩至 25 个，追加美容院/养生馆/社区门店/分销商/门店老板

### 代码变更
- `scripts/topic_history.py`：新增 `DAILY_CAP` / `WEEKLY_CAP` / `FROZEN_KEYWORDS(25)` 常量；新增 `_query_last_used` / `check_frozen_keywords` / `check_dimension_quota` 三函数；`append_candidate` 扩展 `dimension / formula / audience / frozen_keywords` 字段；CLI 新增 `check-frozen` / `check-quota` 子命令
- `scripts/run_nsksd_daily.sh`：Step 1 prompt 重写，加入必读三件套 + V9.7 硬约束 + 反面示例 + 张力 6 维 + 三库禁用词扫描

### TODO（记入 topic-title-workflow.md 第六节坑 3）
- 拆 `scripts/topic-crawler.ts` M6 关键词池：M6 产品科普（纳豆激酶/FU 活性/纤溶）+ M7 招商场景（门店/馆/私域）两个独立词池

## [V9.6] - 2026-04-21（深夜）

### 新增（引导反馈卡 E2E 打通）
- **Guided 反馈卡全链路工作**：`card_builder.py` + `lark_ws_listener.py` 配合跑通
  - 布局：blue header + 产出 markdown + input(max_length=1000) + column_set(bisect) 双 button
  - 点击后：feedback 文件落地 `triggers/guided/{session_id}-{step_name}.feedback`（含 action + feedback_text + 时间戳）
  - 锁定态：header 变 grey + 原产出保留 + 双 button disabled + 末尾追加「📝 曲率修改意见 · HH:MM」
- **新增 `docs/playbooks/guided-feedback-card.md`**：完整踩坑记录（5 个真因）+ 硬规则 + 诊断命令 + E2E 剧本

### 修复（3 个死活交互不通的真因）
- **root-cause 1**：锁定卡 `disabled + danger/primary` 组合 → Code-356 拒收。修法：disabled button 统一 `type: "default"`
- **root-cause 2**：原卡 reject 按钮 `type: "danger" + form_action_type: "submit"` + value 嵌 `_skeleton` → 客户端本地 schema 校验失败 → 事件根本不发网络。修法：reject 改 `primary`，视觉靠 🔴 emoji
- **root-cause 3**：`run_listener_mac.sh` 不注入凭证 → 新进程闪退 → 系统一直跑老代码。修法：脚本自动从 `~/.nsksd-content/config.json` 读 `LARK_APP_ID/SECRET`

### 优化
- **input max_length 500 → 1000**（飞书 schema 2.0 官方硬限，5000 不支持）
- **flex_mode stretch → bisect**：手机端保持左右布局（stretch 会 fallback 成堆叠上下）
- **button.value 塞骨架不塞整 body**：从可能超 2KB 降到 309 字节级

### E2E 验证
- ✅ 场景 A：空输入点 reject → feedback 正确落地（action=reject, feedback_text=""）
- ✅ 场景 B：填"123"点 reject → feedback 正确落地（action=reject, feedback_text="123"）

## [V9.5] - 2026-04-21（晚）

### 新增（铁律升级）
- **飞书+公众号双推铁律**：`scripts/nsksd_publish.py` 重构 main() 流程：
  - 飞书云文档无条件先推（永远保底，用于预览/审阅/归档）
  - 公众号凭证齐时追加推送，凭证缺/失败时通知卡明确告知"公众号未推"
  - exit code 语义：0 双端成功 / 3 飞书✅+公众号未配置 / 4 飞书✅+公众号失败 / 2 输入缺失

### 修复（上线拦路 bug）
- **lark-cli 1.0.14 绝对路径被拒**：`--markdown @file` 要求相对路径
  - 解法：改用 `tempfile.mkdtemp` 专用目录 + `cwd=tmp_dir` + 相对文件名
- **jq 表达式错取字段**：lark-cli 返回的 URL 在 `.data.doc_url`，之前取 `.data.url` 永远为空
  - 解法：改为 `.data.doc_url // .data.url // .url // empty`，raw 解析兜底同步补上 doc_url
- **trigger_watcher Step 5 签名错配**：之前调 `--html --cover --title`，新版只接 `--dir`
  - 解法：统一产物目录 `/tmp/nsksd-${session_id}/` 含 `article.html` + `images/cover.jpg`

### 新增（客户自助体验）
- **setup_cli 查询链接提示**：凭证未填时主动给微信公众平台 / 飞书开放平台 / api-explorer 直链 + IP 白名单提醒

### E2E 验证
- `scripts/nsksd_publish.py --dir /tmp/nsksd-dualpush-test --author "日生研内容部"` 双推打通：
  - 飞书云文档：https://www.feishu.cn/docx/TJTDdCsZ3ocSMOxUd1xcsTn7nlb
  - 公众号草稿 media_id：RTt8Y-U45B92SLFlt9IpKAgcH4GjtQb4IPNGtaB01rTuWyHPjLiph73SsvW9hjhg
  - 通知卡送达曲率 admin_open_id ✅

---

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
