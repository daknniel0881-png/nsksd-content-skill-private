---
name: nsksd-content
description: 日生研NSKSD纳豆激酶自媒体内容工厂Skill（V10.6）。当用户提到日生研、NSKSD、纳豆激酶的公众号选题、文章撰写、内容创作、招商文案、标题优化、大会宣传时，必须使用此Skill。V10.5 **排版宽松化 + 重复词软提示 + 读者视角自审 + 修订清单落盘**：①主题 v5-sample 段间距放宽到 1.1em，wrapper 增加 15px 上下页边距，对齐丁香医生/人民日报健康版观感；②新增 `scripts/redundancy_check.py`（stdlib-only，滑动 n-gram + 碎片去噪），检查高频实词/段首重复/近邻重复三档软提示，exit 永远 0 不阻断发布，trigger_watcher 在 fact_auditor 后接软扫，产物落 `artifacts/<SID>/redundancy-warns.json`；③`agents/article-writer.md` 新增 Step 3d 读者视角自审（5 问：钩子/逻辑流/冗余/结尾/配图），落 `step3d-self-audit.md`；④新增 `templates/revision-checklist.md` 修订清单模板（6 占位符：SID/TIMESTAMP/FACT_ISSUES/CITATION_ISSUES/REDUNDANCY_WARNS/SELF_AUDIT_NOTES），每次写完合并 fact/citation/redundancy/self-audit 报告落 `artifacts/<SID>/revision-checklist.md`，发布前人工过清单。V10.4.1 **修复 fact_auditor 过度误杀**：规则 A（orphan_number）同段命中 [n] 脚注 / 《刊物》/ 研究/发表/公众号/刊文 等任一出处线索即自动通过，只有"段内完全没有任何出处语言"的裸奔数字才 high；规则 D（institution_without_doi）合规载体扩展到公众号刊文/发表于/[n]脚注/白皮书/指南，匹配丁香医生 + 人民日报健康版主流脚注挂尾写法。大额数字、精确数据可以放心用，只要带出处线索（脚注数字、刊物名、"研究/发表"等）就通过。V10.4 **OpenID 自动查询 + 白名单源 + fact_auditor 第五道事实硬门控 + 占位符两阶段写作 + 懒惰话术禁用**：①新增 `scripts/lib/openid_resolver.py` 封装 lark-cli 零参数查 open_id / chat_id，`setup_cli.py` 不再让用户手输 `target_open_id` 和 `customer_open_chat_id`（serp 先自动查，客户群用序号选择，失败才 fallback ask）；②新增 `references/whitelist-sources.md` 50 条四分组（官方政府/学术期刊/行业权威/品牌自述）数据源白名单，引用机构不在白名单内降级为 medium 警告；③新增 `scripts/fact_auditor.py` 第五道硬门控（`rejected_fact_audit`）四规则：orphan_number（硬医疗单位缺源 high）/ weasel_phrase（研究表明/专家认为/据统计等 13 条懒惰话术 high）/ non_whitelist_source（medium）/ institution_without_doi（机构+年份+研究无DOI high）；④`agents/article-writer.md` 重写 Step 3 为 Step 3a 骨架（数字/人名/机构/DOI 一律写 `[待填充:xxx]`）+ Step 3b 三级查证填充（白名单 → 本地 KB → WebSearch 限定 domain），产出结构化 `step3-facts.json`；⑤writing-style §5 新增"无知许可"条款（宁可留空不可编造），§6 新增 13 条懒惰话术禁用清单；⑥`trigger_watcher.sh` 四门控升五门控（layout → data_audit → citation_check → **fact_auditor** → image_size_check），step3-article.md/step4-images 缺失时 fail-closed 不再 fail-open。V10.3 **引用来源规范 + 图内禁英文 + 配图必要性**：①新增 `scripts/citation_check.py` 第三道硬门控（亲昵称谓"袁总/老袁"/模糊回指"同上/同前"/半角括号来源），在 layout_check + data_audit 之后拦截；②`format.py::gray_out_source_citations` 把全角 `（来源：XXX）` 自动包成浅灰色 span（`#9aa0a6` / 0.92em），视觉降级与正文拉开层级；③图内文字白名单收紧为仅 `NSKSD` 和 `FU` 两个英文 token，其他一律中文（含 Nattokinase/RCT/BMI/Before-After 等全部翻译）；④新增《配图必要性原则》7 种必配场景 + 4 种禁配场景 + 「图信息量 ≥ 文字信息量」衍生解释义务，治"段段配图"; ⑤新增 `docs/playbooks/citation-source-naming.md` 引用规范 playbook。V10.2 **修公众号图片裂开 + 飞书云文档客户可读**：`replace_all_images` 三套正则（双引/单引/无引号）+ 去 `./` 前缀 + stderr 日志；`share_doc_to_customer` 调 `drive permission.members create` 把客户群/曲率 admin 加协作者。V10.1 **图片规则硬门控**：①公众号封面硬钉 900×383（~2.35:1 头图位），小红书/视频封面硬钉 1242×1660（~3:4 竖版），新增 `scripts/image_size_check.py` 用 Pillow 精确校验尺寸；②内文配图硬下限 3 张、标配 5 张、上限 8 张；③图内文字中文优先；④`trigger_watcher.sh` Step 4.5 图片硬门控。V10.0 **数据事实硬门控 + S 级种子选题库**：①新增 `scripts/data_audit.py` 六道扫描（数字断言缺源/医广绝对化/日本禁词/捏造信号短语/FU 单位错写/孤证孤立健康陈述），在 layout_check 之后做发布前第二道硬门控，由 `trigger_watcher.sh` Step 4.5 自动拦截；②选题阶段就强制走数据核查（topic-scout 读 `references/data-verification.md` v10.0 再选题，禁止"据研究/有数据显示/权威报告"等无出处幻觉信号）；③收录海斌原文《蓝皮书发布｜纳豆激酶首次被纳入国家级健康管理专家指引》到 `references/external-articles/mp.weixin.qq.com/landmark-articles-2026-04-22-bluebook-nsk/` 作为 S 级种子，附 `SEED-TOPICS.md` 拆解 13 条政策权威选题 + 独家一级权威事实 10 条（蓝皮书名称/附录/主编单位/4000-8000 FU 剂量/四大机制/参编身份）+ 交叉验证配对表 + 禁止混搭 5 条红线；④Windows 选题引擎修复（stdin 管道传 prompt 取代字面量化 / ≥10 条不足自动重试 2 次 / 回补"维度≥5 + 5 类句式各 1 条"多样性硬约束 / 路径 POSIX 化 / JSON 解析失败分级 exit code）；⑤飞书消息推送硬编码步骤写入发布流水线，修复"只写云盘不推 IM"断点。V9.9 **文章排版硬约束**：段落 ≤ 100 字 + 每篇 3-6 个 `##` 二级小标题 + `layout_check.py` 脚本做发布前硬门控；解决客户端吐槽"大段文字无小标题可读性差"问题。V9.8 **Windows 适配大修**：修 14 条客户端测试踩坑（daily-topics.ps1 缺失 / 飞书开放平台 URL 错 / send_notify 不支持 open_id / 中文消息乱码 / run_listener_win.bat 不注入凭证 / venv 路径硬编码 / 安全软件白名单 / Bash 工具路径坑）；新增 scripts\daily-topics.ps1 Windows 定时入口；新增 scripts\setup_cli.ps1 Windows 交互配置包装；重写 run_listener_win.bat 自动注入凭证 + 校验 venv + 自动装 lark-oapi；新增 docs\playbooks\windows-troubleshooting.md 整本排障说明书。V9.7 **标题选题方法论大融合**：45 爆款公式（DBS 30 + 全网 5 + 本地 10）、八维坐标系 M1-M8（+招商 +名人古法）、三层代码去重硬线化（M7 ≤1/日 / M6+M7 ≤2/日 / C 端 ≥6/10）、反门店同质化 25 冷冻词、C 端 70% + B 端 30% 硬比例、医广红线三库双扫、反面示例黑名单 4 类。V9.6 **Guided 引导反馈卡 E2E 打通**。V9.5 飞书云文档+公众号草稿**双推铁律**。V9.4 彻底与 wechat-autopublish 解耦，独立 10 主题排版 + nsksd-writing-style 写作规则 + docs/playbooks 做事说明书矩阵 + CLI 引导配置凭证（零硬编码）+ 飞书云文档保底。V9.1 新增 bun+飞书CLI 自动安装授权、飞书多选卡片乱码防护。V9.0 选题六维坐标系+三层去重+标题手册+爆款语料库+路由表；v8.4 日本表述弱化；v8.3 单入口 `/nsksd` + 模式持久化、每日 10 点定时推、5 子 Agent 串行、guard.py 硬门控、飞书长连接回调。
---

# 日生研NSKSD纳豆激酶 · 自媒体内容工厂（V10.6）

## V10.6 核心升级（本版 · 2026-04-22 · 竞品数据污染紧急清除 + 数据黑名单门控）

### 为什么要做 V10.6？

发现知识库长期混入**广东双骏生物科技**的临床数据，被 AI 错误归属于日生研/NSKSD。受污染的错误数据：1062人、4家医院、Frontiers in Cardiovascular Medicine、10800FU×12月、66.5-95.4%改善率。V10.6 紧急清除全库污染并封闭漏洞。

### 1. 全库数据清洁（Task A）

受污染文件逐一修正，共涉及 10 个 reference 文件：`knowledge-base.md` / `whitelist-sources.md` / `compliance.md` / `nsksd-writing-style.md` / `topic-selection-rules.md` / `topic-library.md` / `title-playbook.md` / `science-popular-style.md` / `compliance-checklist.md` / `research-papers/2026-04-16-pan-vascular-disease/` 目录（4 文件）。

正确数据：
- **市一97例**：97例 / 90天 / 斑块46.7% / IMT42.1% / 《中华养生保健》第42卷第5期 / 钱申贤教授
- **浙大120人RCT**：120人 / 8000FU/天 / 6个月 / 楼敏教授 / 《卒中与脑血管疾病杂志》

### 2. 竞品数据黑名单（Task B）

新增 `references/competitor-data-blacklist.md`（6条指纹）+ `scripts/fact_auditor.py` 规则E `scan_competitor_data()`，发布流水线自动拦截竞品数据混入（exit code=1 阻断）。

---

## V10.0 核心升级（2026-04-22 · 数据事实硬门控 + S 级种子 + Windows 选题引擎修复）

### 为什么要做 V10.0？

第十二次/十三次客户沟通同时暴露三件事：**(1)** 模型会在引用数据时偷懒瞎编"据研究/有数据显示"；**(2)** Windows 定时选题生成不足 10 条、角度单一、飞书消息没推送；**(3)** 客户团队已有一篇蓝皮书级别的政策权威文章（海斌原文），但 skill 不知道它的存在，每次写作都从零找素材。V10.0 一次治这三个病根。

### 1. 数据事实硬门控（最高优先级）

**机制层**：`scripts/data_audit.py` 新脚本 · 六道扫描 · 退码非 0 阻塞发布：

| 扫描项 | 规则 |
|-------|------|
| `numbers_without_source` | 百分比/倍数/FU/人数/年份 60 字上下文无来源标注 → 违规 |
| `medical_absolutes` | 治疗/治愈/根治/当天见效/第一/唯一/国家批准疗效 → 违规 |
| `japan_forbidden` | 日本进口/日本原装/日式工艺/日本匠心 → 违规 |
| `fabrication_signals` | 据研究/有数据显示/权威报告/相关研究表明 + 后置无《》或 URL → 违规 |
| `unit_misuse` | 纳豆激酶剂量写成 mg/IU/毫克 → 违规（FU 唯一合法） |
| `isolated_claims` | 健康功效核心陈述（降低血栓/改善血脂）sources_checked <2 条或 authority_level=1 <1 条 → 违规 |

**流水线层**：`trigger_watcher.sh` Step 4.5 双门控：
```
Steps 1-4 完成 → layout_check（排版）→ data_audit（事实）→ Step 5 发布
              └─ 任一非 0 → trigger.status = rejected_layout / rejected_data_audit，不发 IM，不落盘
```

**选题层**：topic-scout 生成选题时必须走 `references/data-verification.md` v10.0 一遍，禁止引用未核验的"据研究"型陈述进选题卡。

### 2. S 级种子选题库（海斌原文落地）

路径：`references/external-articles/mp.weixin.qq.com/landmark-articles-2026-04-22-bluebook-nsk/`

- `bluebook-nsk-national-guidance.md` — 海斌 2025-06-26 原文
- `bluebook-nsk-national-guidance-captured.html` — 原始 HTML 存证
- `SEED-TOPICS.md` — 拆解 13 条政策权威选题 + 10 条一级权威事实 + 交叉验证配对表 + 5 条禁止混搭红线

**硬约束**：topic-scout 每天选题前优先扫该 `SEED-TOPICS.md`，S 级选题池里这 13 条拥有**绝对优先权**，直到蓝皮书相关角度用完再开新题。

**独家权威事实白名单**（可直接引用无需再做交叉验证）：
- 蓝皮书全称、主编单位（健康中国研究中心·中关村新智源）、出版社、2024 年
- 专家指引附录四大机制（溶栓/降粘聚/抑血小板/延动脉硬化）
- 4000-8000 FU/日 · 餐后或睡前 · 长期服用
- 适用人群 5 类、日生研参编身份、1998 年行业首家、30+ 项临床试验

### 3. Windows 选题引擎修复（I 组全 6 条）

- **I-1** `daily-topics.ps1` L136 修：`(Get-Content '…')` 字面量传参 → `$prompt | & claude -p` 走 stdin
- **I-2** prompt 加"若不足 10 条必须用同维度派生不同角度变体补齐，不许 <10"
- **I-3** 回补"10 选题覆盖 ≥5 维度 M1-M8" + "主张/疑问/数字/场景/对比 5 类句式至少各 1"
- **I-4** 路径 POSIX 化：`$SKILL_DIR_POSIX = $SKILL_DIR.Replace('\','/')` 再注入 prompt
- **I-5** JSON 解析分级 exit code（2=解析失败、3=<10 条）+ 追加强化提示重试
- **I-6** 最多 3 次尝试（1 正式 + 2 重试），仍不足则 Die，彻底告别"Windows 跑出 6 条就上线"

### 4. 飞书消息推送硬编码

第十三次沟通原话："生成成功是直接放到他的云盘，但是没有直接通过飞书消息发给他。" 把"将文章发送至飞书"的 1-2-3 步硬编码写进 `nsksd_publish.py` + `trigger_watcher.sh`，不再依赖模型自主推断。

### 5. 依赖文件总览

| 新增/修改 | 文件 | 说明 |
|----------|------|------|
| ➕ | `scripts/data_audit.py` | 六道数据事实扫描硬门控 |
| ➕ | `references/external-articles/mp.weixin.qq.com/landmark-articles-2026-04-22-bluebook-nsk/` | 海斌原文 + HTML 存证 + SEED-TOPICS 拆解 |
| ✏️ | `scripts/interactive/trigger_watcher.sh` | 发布前 Step 4.5 双门控（layout + data） |
| ✏️ | `scripts/daily-topics.ps1` | I-1~I-6 Windows 选题引擎修复 |
| ✏️ | `references/data-verification.md` | v9.3 → v10.0，选题阶段核查 + 蓝皮书白名单 |

---

## V9.9 核心升级（上一版 · 2026-04-22 · 文章排版硬约束）

客户反馈："现在写出来的文章，大段大段文字，缺小标题，可读性差。"根因是 V9.4 的写作规范明确写了"不用 # 标题堆砌结构"，把小标题这条路堵死了。V9.9 把规则反过来：

1. **段落字数硬上限 100 字**（V9.9 新增）：写进 `nsksd-writing-style.md` / `science-popular-style.md` / `article-writer.md` 三处写作规范。两句一段是常态，长段必拆
2. **每篇必须有 3-6 个 `##` 二级小标题**：主干 4 段（问题 / 科学 / 产品 / 赚钱）每段起一个小标题当路标。小标题写成完整观点句，不写"背景/方法/结论"式目录词
3. **新增 `scripts/layout_check.py` 脚本**：发布前硬门控，自动统计二级小标题数 + 逐段字数 + 目录词扫描，命中退码非 0 阻止流水线
4. **`article-writer.md` 自查清单扩展**：从"三轮自查"升级为"五轮自查"，新增第 5 轮"段落+小标题扫描"硬条目
5. **`step3-article.md` frontmatter 扩字段**：`subheading_count` / `max_paragraph_chars` / `paragraph_overflow_count` 三项进入 style_check，没填算不合格

## V9.8 核心升级（2026-04-22 · Windows 适配大修）

基于客户端 Windows 11 一整晚实测（`nska-windows-test-report.md`）反馈的 14 条问题系统性修复：

1. **补齐 Windows 定时入口 `scripts/daily-topics.ps1`**（问题 #1 #3）：V9.7 之前 `setup.ps1` 引用但文件缺失导致 schtasks 注册失败。新脚本对标 `run_nsksd_daily.sh`，4 步（生成选题 / 构造多选卡 / 启动 listener + 推卡 / 启动 watcher）全走 PowerShell + Python，不依赖 Git Bash
2. **修飞书开放平台 URL 错位**（问题 #3）：`setup_cli.py` 里 `https://open.feishu.cn/app` → 改为 `https://open.feishu.cn/page/launcher?from=backend_oneclick`（launcher 直链，旧地址会 404）
3. **`send_notify.py` 支持 `--open-id` / `--chat-id` 二选一**（问题 #8）：原脚本硬绑 `--chat-id` + `receive_id_type=chat_id`，但测试配置里只有 `target_open_id`。新版互斥参数组 + 自动从 `~/.nsksd-content/config.json` 兜底读
4. **中文消息乱码全链路修复**（问题 #11）：Windows 控制台 GBK 编码 + Git Bash curl 未声明 charset 双重成因；`send_notify.py` 开头 `sys.stdout = TextIOWrapper(..., encoding='utf-8')`；`daily-topics.ps1` 全脚本强制 `chcp 65001` + `PYTHONIOENCODING=utf-8` + `Content-Type: application/json; charset=utf-8`
5. **`run_listener_win.bat` 重写**（问题 #12）：原脚本三大坑（venv 路径硬编码 bad interpreter / `lark-oapi` 未装 / 环境变量未注入）全治。新脚本自动从 `config.json` + `.env` 注入凭证、校验 venv 有效性失效则重建、检测 `lark-oapi` 缺失则 `pip install`
6. **新增 `scripts/setup_cli.ps1` Windows 交互配置包装**（问题 #4）：取代"让用户手动编辑 config.json"的反 Agent 模式，一次交互写入 `%USERPROFILE%\.nsksd-content\config.json`
7. **新增 `docs/playbooks/windows-troubleshooting.md` 整本排障说明书**（问题 #1 #2 #6 #7 #9 #12）：Bash 工具无限循环坑 / 安全软件白名单 / venv 失效 / 多选卡回调不触发 → 事件订阅未配置，一站式答疑
8. **Bash 工具问题官方结论固化**：不要手动复制 `bash.exe`（会触发 Claude Code 智能路径适配无限循环），唯一正解是**重装 Git for Windows + 勾选 Git Bash Here**（2026-04-22 已客户端验证）

### Windows 安装 Checklist（V9.8 新增）

```powershell
# 1. 前置：Python 3.8+ / Node.js 18+ / Git for Windows（勾 Git Bash Here）/ Claude Code
# 2. clone
git clone https://github.com/daknniel0881-png/nsksd-content-skill-private.git %USERPROFILE%\.claude\skills\nsksd-content
cd %USERPROFILE%\.claude\skills\nsksd-content

# 3. 依赖 + 定时任务
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

# 4. 交互式配置凭证
powershell -ExecutionPolicy Bypass -File scripts\setup_cli.ps1

# 5. 启动监听器（飞书多选卡回调必需）
cd scripts\interactive
.\run_listener_win.bat start

# 6. 手动触发验收
cd ..
powershell -ExecutionPolicy Bypass -File scripts\daily-topics.ps1
```

遇坑翻 `docs/playbooks/windows-troubleshooting.md`。

---

## V9.7 核心升级（2026-04-21）

1. **标题 45 公式融合**（`references/title-playbook.md` 全文重写）：
   - **F1-F10**：本地原有 10 公式（数字党/反常识/悬念钩子/对立冲突/权威背书/场景代入/指南型/提问型/反转型/情绪共鸣）
   - **F11-F40**：DBS skill 30 公式 9 大类（身份呼唤/感人式/吓人式/古法养生/时间场景/权威背书/对比反差/数字承诺/名人引用）
   - **F41-F45**：全网爆款 5 补充（数字+痛点公式 +27% 打开率 / 对立疑问 / 时间压迫 / 结果倒推 / 身份专属）
2. **八维坐标系扩容**（`references/topic-selection-rules.md` 全文重写，M1-M6 → M1-M8）：
   - M7 **招商场景**（硬线 ≤1 条/日，单独从泛 M6 拆出）
   - M8 **名人古法**（为张奶奶/古法养生类中老年爆款题材独立配额）
   - C 端维度（M1 医学循证 + M3 节气养生 + M4 用户痛点 + M8 名人古法）占比硬约束 ≥60%（7/10 以上）
3. **三层去重代码化硬线**（`scripts/topic_history.py` 重构）：
   - Layer 1：`check_topic()` SHA1 指纹 30 天去重
   - Layer 2：`check_dimension_quota()` M7 ≤1、M6+M7 ≤2、C 端 ≥6/10、主人群（门店/美容院/养生馆/分销商）≤1
   - Layer 3：`check_frozen_keywords()` **25 冷冻词**（美容院/养生馆/社区门店/分销商/门店老板等 +5 反门店）30 天窗口
   - 启动 `HISTORY_FILE.touch()` 修 logs/topic-history.jsonl 不存在导致空转真因
4. **C 端 70% + B 端 30% 硬比例**（`references/knowledge-base.md` 第九章扩容）：
   - C 端 6 类画像：关注血管健康的中年人 / 三高家族史职场人 / 给父母买保健品的子女 / 日式健康食品尝鲜者 / 已确诊慢病中老年 / 养生达人
   - B 端 6 类画像：美容院/养生馆/社区门店老板 + 大健康创业者 + 医药连锁店长 + 健康管理师
   - 修 SKILL.md 老口径"目标=美容院老板+养生馆老板+门店老板成为分销商"这个北极星错位
5. **反面示例黑名单 4 类 + 医广红线三库双扫**：
   - 黑名单：门店同质化 / 泛化无锚点 / 触医广红线 / AI 味句式（不是…而是… / 破折号 —— / 赋能链路飞轮）
   - 三库：医广红线（治疗/根治/当天见效）+ 保健食品广告法绝对化用语 + 曲率 AI 味词
6. **主 prompt 真正加载 title-playbook.md**（`scripts/run_nsksd_daily.sh` Step 1 重写）：之前只读 SKILL.md + topic-selection-rules.md，title-playbook.md 从未进 prompt 导致标题公式形同虚设
7. **新增 `docs/playbooks/topic-title-workflow.md`**：E2E 7 步工作流图 + 硬约束速查表 + CLI 调用示例 + 4 类踩坑记录 + V9.7 变更日志对照

## V9.6 核心升级（2026-04-21 深夜）

1. **Guided 引导反馈卡 E2E 打通**：`card_builder.py::build_guided_feedback_card` + `build_guided_locked_card` + listener `is_guided_card` 分支完整工作。点击按钮后 feedback 文件正确落地（action + feedback_text + 时间戳），锁定态灰化原产出保留
2. **修 3 个死活不通的真因**（花了一晚上定位，全部记入 `docs/playbooks/guided-feedback-card.md`）：
   - 锁定卡 `disabled + danger/primary` → Code-356 拒收。改 `type: "default"`
   - 原卡 reject `type: "danger" + form_action_type: "submit"` + 嵌 `_skeleton` → 客户端本地 schema 校验失败，事件不发网络。改 `primary`，视觉靠 🔴 emoji
   - `run_listener_mac.sh` 不注入凭证 → 新进程闪退，系统跑老代码。脚本自动读 `~/.nsksd-content/config.json`
3. **飞书 input 硬限 500→1000**（官方 schema 2.0 硬限）
4. **flex_mode stretch→bisect**：手机端保持左右布局
5. **button.value 塞骨架不塞整 body**：309 字节级，远低于 2KB 限制

## V9.5 核心升级（2026-04-21 晚）

1. **飞书+公众号双推铁律**：`scripts/nsksd_publish.py` 重构 main()——飞书云文档**无条件先推**（永远保底，可预览/审阅/归档），公众号**凭证齐时追加推送**。通知卡同时展示两端状态，不再让人误解"飞书推了=公众号推了"。exit code 语义：0=双端✅ / 3=飞书✅+公众号⚠️未配置 / 4=飞书✅+公众号❌失败 / 2=输入文件缺失
2. **修 2 个 lark-cli 上线拦路 bug**：
   - `lark-cli 1.0.14+` 要求 `--markdown @file` 是相对路径，之前传绝对路径被拒 → 改 `tempfile.mkdtemp` + `cwd=tmp_dir` + 相对文件名
   - lark-cli 返回体 URL 在 `.data.doc_url`，jq 表达式之前错取 `.data.url`（永远为空）→ 改为 `.data.doc_url // .data.url // .url // empty`
3. **trigger_watcher Step 5 签名统一**：Claude CLI 产物目录约定 `/tmp/nsksd-${session_id}/` 含 `article.html` + `images/cover.jpg`，nsksd_publish 用 `--dir` 入口（之前 `--html/--cover/--title` 签名错配会直接失败）
4. **setup_cli 加查询链接提示**：凭证未填时主动给出微信公众平台 + 飞书开放平台 + api-explorer 直链，客户不用到处 Google

## V9.4 核心升级（2026-04-21）

1. **彻底与 wechat-autopublish 解耦**：清除 4 处 quyu-writing-style 残留引用，trigger_watcher Step5 改走 `nsksd_publish.py` 本地流水线
2. **独立写作规则**：新增 `references/nsksd-writing-style.md`，大白话+专业，不引任何个人写作风格
3. **做事说明书矩阵**：新增 `docs/playbooks/` 7 个文件（wechat-publish / feishu-card / feishu-doc / cover-image / data-verification / style-card + README 总索引）
4. **CLI 引导配置**：新增 `scripts/setup_cli.py`，交互式收凭证，chmod 600，零硬编码
5. **config.example.json 完整化**：含 preferred_theme 字段和中文行内说明

## V9.1 核心升级（2026-04-21 早版）

1. **bun + 飞书 CLI 自动安装授权**：`scripts/setup.sh` / `setup.ps1` 检测不到 bun 时自动 `curl https://bun.sh/install`（Mac/Linux）或 `irm bun.sh/install.ps1`（Windows）；自动 `bun install -g @larksuiteoapi/lark-cli`（npm fallback）；从 `.env` 读 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 自动 `lark config set` 完成授权，全程无交互。文档见 `docs/lark-cli-setup.md`
2. **飞书多选卡片乱码防护**：`scripts/server/utils/text-sanitizer.ts` 从 7 个源头阻断（BOM / 零宽字符 / CRLF / 控制字符 / UTF-8 字节截断 / option.value 特殊字符 / Content-Type charset）；配套 `text-sanitizer.test.ts` **13/13 测试通过**
3. **选题库分块重构**：在六维坐标系之上叠加 6 个内容模块 `references/topic-library/{M1-industry-news,M2-nattokinase-research,M3-health-management,M4-cases-stories,M5-policy-regulation,M6-partner-channels}/{YYYY-MM}/`；新增 `scripts/topic-crawler.ts` 按关键词池抓取归档；**M6 招商模块硬约束 8 个角度**（店主形象/咨询能力/会员裂变/组合设计/合规/跨品类/社群/动线话术），禁止单一"卖产品→利润"角度
4. **4.16 PDF 入库**：《"颠覆性"认知对泛血管病防治影响与实践》原文 + 全文提取 + 选题点拆解 + 关键数据卡 + 图表识别（后台 Agent 处理中，完成后补充归档路径）

## V9.0 核心升级（2026-04-21 早版）

1. **选题重复问题根治**：新增 `references/topic-selection-rules.md`——六维坐标系（M1-M6）+ 三层去重（30天指纹 + 维度配额 + 20个禁用词30天冷冻窗口）+ 日志扩展 dimension/frozen_keywords 字段
2. **标题专项手册**：新增 `references/title-playbook.md`——10条爆款公式（数字党/反常识/悬念钩子/对立冲突/权威背书/场景代入/指南型/提问型/反转型/情绪共鸣）+ 日生研场景示例矩阵 + 5条雷区硬线 + A/B决策树 + 五维评分（≥85 才进候选池）
3. **爆款标题语料库**：抓取 24 篇破千/破万阅读量公众号文章，存 `references/wechat-benchmark/raw/` 原文 + `titles-corpus.md` 语料 + `titles-pattern-analysis.md` 共性分析 + `content-pattern-analysis.md` 正文共性（抓取由独立 Agent 执行）
4. **内部路由表**：新增 `config/routing-table.yaml`——参考曲率 dispatcher 架构，8 条路由（选题/标题/正文/合规/配图/发布/飞书卡片/模式切换），按 trigger 硬编码加载 MD，避免暴力全量 Read references/
5. **引导界面直链补齐**：`SETUP-GUIDE.md` + `docs/onboarding.md` 补飞书开放平台一键启动链接 `https://open.feishu.cn/page/launcher?from=backend_oneclick` + 微信开发平台 `https://developers.weixin.qq.com/console/product/mp/`
6. **定时任务自动安装**：`scripts/setup.sh`（Mac · launchd）新增自动 load plist；新增 `scripts/setup.ps1`（Windows · schtasks）一键注册每日 10:00；安装时 OS 自动检测，不再询问用户

## 路由表（V9.0 新增）

调用本 Skill 时，`master-orchestrator` 先读 `config/routing-table.yaml`，按用户 trigger 词命中加载对应 MD 文件，而非全量 Read references/。详见该 yaml 文件。

| 路由 | trigger | 加载 |
|------|---------|------|
| R1 选题生成 | 选题 / /nsksd | topic-selection-rules + topic-library + themes-curated + titles-corpus |
| R2 标题打磨 | 标题 / title | title-playbook + wechat-benchmark/titles-* |
| R3 正文撰写 | 写文章 / 撰稿 | science-popular-style + content-pattern-analysis + knowledge/核心文档/ |
| R4 合规审查 | 合规 / 审核 | compliance + compliance-checklist |
| R5 配图生成 | 配图 / 封面 | generate-image skill |
| R6 排版推送 | 发布 / 推送 | wechat-autopublish skill |
| R7 飞书卡片 | 推卡 / 多选卡 | scripts/send-topic-card.ts |
| R8 模式切换 | 切换到 / reset | scripts/mode_manager.py |

---



> 品牌：日生研生命科学（浙江）有限公司
> 产品：NSKSD纳豆激酶（海外原研方 / 国际合作研发机构生产，日生研为中国总代理）
> 目标（V9.7 重写）：通过多元内容触达 **C 端消费者科普（70%）+ B 端招商场景（30%）**，
> 吸引信任型 C 端消费者 + 优质 B 端分销合作伙伴
> 内容策略：科学信任（40%）+ 健康科普（30%）+ 品牌故事（15%）+ 招商转化（15%）
> 目标人群：中老年消费者（45-65 岁本人/家庭决策者）为主，分销渠道老板（美容院/养生馆/社区门店）为辅

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

## 遇到问题翻说明书

`docs/playbooks/` 目录下有 7 个做事说明书，遇到问题先查：

| 文件 | 覆盖场景 |
|------|----------|
| `docs/playbooks/README.md` | 总索引，快速定位该翻哪个说明书 |
| `docs/playbooks/wechat-publish.md` | 公众号推送全流程、403/40164 报错、图片宽度、mock 模式 |
| `docs/playbooks/feishu-card.md` | 飞书卡片乱码防护、多选卡 schema 2.0、trigger 文件流、chat_id 获取 |
| `docs/playbooks/feishu-doc.md` | 飞书云文档保底、lark-cli 语法、Markdown 格式规则、权限给 chat_id |
| `docs/playbooks/cover-image.md` | 配图生成、Bento Grid 风格、尺寸 900x500、width=auto 保持 |
| `docs/playbooks/data-verification.md` | 数据核查步骤、WebFetch 验证 URL、找不到来源的降级写法 |
| `docs/playbooks/style-card.md` | 排版主题选择卡、10 推荐主题表、preferred_theme 配置、"查看全部 31 个"展开 |

---

## 版本历史

- V9.4（2026-04-21）：彻底与 wechat-autopublish 解耦 + docs/playbooks 说明书矩阵 + CLI 引导配置
- V9.1（2026-04-21）：bun+飞书CLI 自动安装授权 + 飞书乱码防护 + 选题库分块重构
- V9.0（2026-04-21）：选题六维坐标系 + 三层去重 + 标题手册 + 爆款语料库 + 路由表
- v8.4（2026-04-20）：日本表述弱化硬约束（国际关系敏感期合规升级）
- v8.3（2026-04-20）：单入口 + 模式持久化 + 定时 Step 1 + 配图 5-8 张
- v8.2（2026-04-15）：多 Agent 调度 + guard 硬门控 + 30 天去重 + 双入口
- v8.1（2026-04-10）：飞书卡片长连接回调稳定版
- v8.0（2026-04-01）：重写为多 Agent 架构

详细 Changelog 见 `CHANGELOG.md`。
