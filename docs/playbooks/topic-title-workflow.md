# 选题 + 标题工作流 Playbook（V9.7）

> 问题：历史版本每日 10 选题里门店/美容院/养生馆重复率 50%+，标题公式局限，医广合规靠经验。
> V9.7 解法：八维坐标系 + 45 公式 + 三层代码去重 + 医广红线双扫 + 反面示例黑名单。
> 版本：2026-04-21

---

## 一、上游资源（必读三件套 + 辅助三件套）

| 类型 | 文件 | 作用 |
|-----|-----|-----|
| 必读 | `references/topic-selection-rules.md` | 八维 M1-M8 + 硬限额 + 三层去重 + 反面示例 |
| 必读 | `references/title-playbook.md` | 45 公式 + 张力 6 维 + 三库禁用词 + 医广红线 |
| 必读 | `references/topic-library/README.md` | 分块资讯池 + 8 招商角度 |
| 辅助 | `references/knowledge-base.md` | 目标人群画像（C 端 6 类 + B 端 6 类）|
| 辅助 | `references/wechat-benchmark/titles-corpus.md` | 高阅读真实标题 |
| 辅助 | `scripts/topic_history.py` | 去重 CLI（check-quota / check-frozen）|

---

## 二、标准流程（E2E）

```
┌─────────────────────────────────────────────────┐
│  Step 1  topic-scout 生成 20 候选               │
│  ├─ 读 hotspots/当日.json                       │
│  ├─ 读 topic-library/*.md                       │
│  ├─ 每候选标 dimension(M1-M8) + formula(F1-F45) │
│  └─ 每候选标 audience (C-end-* / B-end-*)       │
├─────────────────────────────────────────────────┤
│  Step 2  三层去重过滤                           │
│  ├─ Layer 1: check_topic() 指纹去重             │
│  ├─ Layer 2: check_dimension_quota() 维度配额   │
│  └─ Layer 3: check_frozen_keywords() 25 词冷冻  │
├─────────────────────────────────────────────────┤
│  Step 3  反面示例黑名单扫描                     │
│  ├─ 4 类禁止选题（见 topic-selection-rules 第二节）│
│  └─ 命中直接剔除                                │
├─────────────────────────────────────────────────┤
│  Step 4  title-outliner 每选题出 5 候选标题     │
│  ├─ 公式至少跨 3 种                             │
│  ├─ 至少 1 条带具体数字                         │
│  └─ 至少 1 条带 C 端人群/场景                   │
├─────────────────────────────────────────────────┤
│  Step 5  三库禁用词 + 医广红线双扫              │
│  ├─ 库 1: DBS/曲率 AI 味词                      │
│  ├─ 库 2: 保健食品广告法绝对化用语              │
│  └─ 库 3: 医疗效果承诺                          │
├─────────────────────────────────────────────────┤
│  Step 6  张力 6 维 + 五维评分                   │
│  ├─ 6 维命中 ≥3 项                              │
│  ├─ 五维评分 ≥85                                │
│  └─ 长度 18-25 字，关键词前置前 10 字           │
├─────────────────────────────────────────────────┤
│  Step 7  最终 10 条进卡片（用户勾 5 条）        │
│  ├─ ≥5 维度覆盖                                 │
│  ├─ M7 ≤1 条（硬线）                            │
│  ├─ M6 + M7 ≤2 条                               │
│  └─ C 端维度 ≥6/10                              │
└─────────────────────────────────────────────────┘
```

---

## 三、硬约束速查表（一屏看全）

| 约束 | 数值 | 来源 |
|-----|-----|-----|
| 每日选题总数 | 10 条 | 业务固定 |
| 维度覆盖 | ≥5 个不同维度 | V9.7 新增 |
| M7 招商场景单日 | ≤1 条（硬线）| V9.7 新增 |
| M6 + M7 合计单日 | ≤2 条 | V9.7 新增 |
| C 端维度占比（M1+M3+M4+M8）| ≥60% | V9.7 新增 |
| 主人群（门店老板/美容院老板/养生馆老板/分销商）| ≤1 条 | V9.7 新增 |
| 标题字数（公众号）| 18-25 字 | 全网爆文经验 |
| 关键词前置 | 前 10 字 | 微信搜一搜权重规则 |
| 张力 6 维命中 | ≥3 项 | V9.7 新增 |
| 五维评分 | ≥85 | V9.0 延续 |
| 标题 emoji 数 | ≤1 个 | 2026 爆文经验 |
| 相似度（近 30 天）| < 0.6 | V9.0 延续 |

---

## 四、CLI 调用示例（topic_history.py V9.7）

```bash
cd /Users/suze/.claude/skills/nsksd-content

# 单个标题冷冻词检查
python3 scripts/topic_history.py check-frozen \
  --title "美容院下一个利润增长点" \
  --angle "门店分销"
# 命中 → exit 1，输出 frozen_hits 数组

# 10 候选维度配额校验
python3 scripts/topic_history.py check-quota --json '[
  {"dimension":"M7"},{"dimension":"M7"},{"dimension":"M4"}, ...
]'
# 超额 → exit 1，输出 over_quota 字典

# 单个选题指纹去重
python3 scripts/topic_history.py check --json '{
  "title":"...","angle":"...","data_points":[...]
}'

# 30 天指纹摘要
python3 scripts/topic_history.py load-30d

# 选题落盘（candidate → selected → published）
python3 scripts/topic_history.py append --json '{...}' --sid SID-xxx
python3 scripts/topic_history.py mark --title-hash abc123 --status selected
```

---

## 五、反面示例黑名单（禁止生成）

### 5.1 门店招商同质选题
- ❌ 美容院下一个利润增长点
- ❌ 养生馆老板靠手艺赚钱
- ❌ 社区门店锁定 500 个家庭
- ❌ 门店第二曲线

### 5.2 泛化无锚点选题
- ❌ 血管健康到底怎么管
- ❌ 关于血管你需要知道这些
- ❌ 纳豆激酶的那些事

### 5.3 触医广红线
- ❌ 根治 / 治愈 / 最好 / 第一 / 当天见效
- ❌ 治疗高血压 / 专治血栓 / 替代降压药

### 5.4 AI 味句式
- ❌ 不是 A 而是 B / 不是 A 是 B
- ❌ 破折号 —— 连接长句
- ❌ 赋能 / 链路 / 飞轮 / 底层逻辑

---

## 六、踩坑记录

### 坑 1 · logs/topic-history.jsonl 不存在导致去重空转（已修复）
- 现象：三层去重"全部通过"，实则文件不存在，load_records 返回空
- 修复：V9.7 topic_history.py 启动 `HISTORY_FILE.touch()`
- 验证：`ls -la logs/topic-history.jsonl`

### 坑 2 · SKILL.md 把门店老板写成唯一目标受众（已修复）
- 现象：LLM 每次读 SKILL.md 先吃到"分销商目标"，选题必然朝门店对齐
- 修复：V9.7 改为 C 端 70% + B 端 30%
- 验证：`grep "70%" SKILL.md`

### 坑 3 · M6 关键词池全是门店/馆/私域（待修复 · 记为 TODO）
- 现象：scripts/topic-crawler.ts 第 37-44 行 M6 词全是门店场景
- 下一步：拆 M6（产品科普）+ M7（招商场景）两个词池，见 topic-selection-rules.md 第一节

### 坑 4 · title-playbook.md 未进入主 prompt（已修复）
- 现象：run_nsksd_daily.sh 只让 LLM 读 SKILL.md + topic-selection-rules.md
- 修复：V9.7 主 prompt 新增"必读三件套"包含 title-playbook.md
- 验证：`grep "title-playbook.md" scripts/run_nsksd_daily.sh`

---

## 七、V9.7 变更日志

| 变更项 | V9.1 旧值 | V9.7 新值 |
|-------|---------|---------|
| 维度数量 | 6（M1-M6）| 8（+M7 招商 +M8 名人古法）|
| 公式数量 | 10（F1-F10）| 45（+35 DBS/全网）|
| 去重层实装 | 纸面 | 全代码化 |
| 冷冻词数 | 20 | 25（+5 反门店）|
| M6 每日上限 | 1（泛）| 1（仅产品科普）|
| M7 每日上限 | - | 1（硬线招商）|
| C 端占比 | 未约束 | ≥60% |
| 反面示例 | 无 | 4 类 |
| 标题数据支撑 | 口述 | 数字+痛点 +27% 打开率等 |
