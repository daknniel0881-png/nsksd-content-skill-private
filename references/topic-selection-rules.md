# 日生研内容创作 · 选题规则与去重机制（V9.7）

> 本文件是 nsksd-content Skill 的选题层"宪法"。topic-scout Agent 每次生成选题前必须读本文件并严格遵守。
> V9.7 核心升级：**八维坐标系**（原六维 + M7 招商场景 + M8 名人古法）+ **M6/M7 硬限额 ≤1/日** + **3 层去重全部代码化** + **反面示例显式化**。

---

## 零、V9.7 核心变更说明（为什么升级）

过去问题：每日 10 选题里反复出现"美容院老板 / 养生馆老板 / 社区门店"系列，占比高达 50%+。根源 5 条已在 `/tmp/nsksd-topic-title-audit.md` 验证：

1. SKILL.md 目标写死"美容院老板 / 养生馆老板 / 社区门店老板成为分销商"——已在 V9.7 改为 C 端 70% + B 端 30%
2. topic-library.md 67% 样本都是门店招商——已在 V9.7 扩容 C 端选题
3. M6 关键词池全是门店/馆/私域——已在 V9.7 拆成 M6（产品科普）+ M7（招商场景）
4. 主 prompt 没有反面示例——V9.7 新增
5. 三层去重零实现（纸面）——V9.7 全部代码化

---

## 一、八维坐标系（V9.7 扩展）

每日推送 10 选题，必须覆盖 **≥5 个维度**，且**招商类（M7）≤1 条**。

| 维度 | 定义 | 典型角度 | 每日上限 | 每周上限 |
|------|------|---------|---------|---------|
| M1 · 医学循证 | 临床研究/RCT/专家共识/文献综述 | 市一97例临床、浙大120人RCT、认知衰退 65% | 3 | 8 |
| M2 · 大会热点 | 行业大会/峰会/学术会议 | FFC2026、五湖大会 | 1 | 2 |
| M3 · 节气养生 | 时令/节气/季节慢病防控 | 秋冬血管收缩、春季养肝 | 2 | 5 |
| M4 · 用户痛点（C 端情感） | 真实用户焦虑/场景问题 | 熬夜血管、加班三高、父母斑块 | 3 | 8 |
| M5 · 政策监管 | 国标/蓝皮书/政策文件 | 专家指引、保健食品新规 | 1 | 2 |
| M6 · 产品科普 | 成分/活性/工艺/差异化对比 | 活性 FU、纳豆差 10 倍、选品逻辑 | **1** | 3 |
| **M7 · 招商场景（新增）** | 门店/加盟/渠道/私域场景 | 养生馆转型、员工培训、会员体系 | **1（硬线）** | **3** |
| **M8 · 名人古法（新增）** | 名人案例/医生故事/古法/节点 | 协和老专家、《黄帝内经》、名人家族 | 2 | 5 |

### 硬约束（V9.7 新增）

1. **10 选题 ≥ 5 个不同维度**（原为 5 选题 ≥3 维度，V9.7 加严）
2. **M6 + M7 合计 ≤ 2 条/日**（产品科普 + 招商场景不能同时超量）
3. **M7 单日 ≤ 1 条**（彻底解决门店重复）
4. **C 端维度（M1+M3+M4+M8）占比 ≥ 60%**（7/10 以上给 C 端消费者）
5. 维度命中统计来源于 `logs/topic-history.jsonl` 的 `dimension` 字段

---

## 二、反面示例（禁止生成的选题类型）

> 这些标题/角度过去反复出现，V9.7 起**禁止 LLM 在 10 选题里再产类似变体**。

### 禁止 1 · 门店招商同质选题
- ❌ 美容院下一个利润增长点，不在脸上
- ❌ 养生馆老板：你还在靠手艺赚钱吗
- ❌ 社区门店如何靠一款产品锁定 500 个家庭
- ❌ 美容院老板，第二曲线的答案
- ❌ 养生馆转型，这条路为什么对

**为什么禁**：主人群（门店老板/美容院老板/养生馆老板）+ 主话题（利润/第二曲线/锁客）组合过去已出过 8+ 次变体。

### 禁止 2 · 泛化"血管健康"无具体数字/人群
- ❌ 血管健康到底怎么管
- ❌ 关于血管，你需要知道这些
- ❌ 纳豆激酶的那些事

**为什么禁**：无锚点，张力 6 维全部不中。

### 禁止 3 · 绝对化/医疗承诺
- ❌ 根治血栓的方法
- ❌ 治愈高血压一款产品搞定
- ❌ 最有效的血管清道夫

**为什么禁**：触 2025 医广新规红线，罚款百万级。

### 禁止 4 · 同维度连发
- 当日已生成 M7 选题后，禁止再出任何"门店/美容院/养生馆/分销"角度。
- 当日 M4 已达 3 条后，禁止再出痛点共鸣类。

---

## 三、三层去重机制（V9.7 全面代码化）

### Layer 1 · 30 天指纹去重（已有 → 修复空转）

**改进**：V9.7 起 `topic_history.py` 启动时**自动创建** `logs/topic-history.jsonl`（如不存在则 `touch`）。

- `title_hash`：标题去停用词后 SHA1 前 12 位
- `angle`：核心角度关键词归一化严格匹配
- `data_points`：数据点集合交集 ≥2 视为重复

**命中任一维度 = 直接剔除**。

### Layer 2 · 维度配额（V9.7 代码化）

新增 `check_dimension_quota(candidates: list[dict]) -> dict`：

```python
def check_dimension_quota(candidates):
    """返回 {dimension: over_count}，超额维度需要重生成"""
    week_history = load_history(days=7)
    week_counts = Counter([t["dimension"] for t in week_history])
    today_counts = Counter([c["dimension"] for c in candidates])
    over = {}
    for dim, cap in DAILY_CAP.items():
        if today_counts[dim] > cap:
            over[dim] = today_counts[dim] - cap
    for dim, cap in WEEKLY_CAP.items():
        if week_counts[dim] + today_counts[dim] > cap:
            over[dim] = (week_counts[dim] + today_counts[dim]) - cap
    return over
```

超额 → 强制 topic-scout 重生成（换维度）。

### Layer 3 · 禁用词 30 天冷冻（V9.7 代码化 + 新增 5 词）

新增 `check_frozen_keywords(title, angle) -> list[str]`。

**冷冻词表（25 词，V9.7 在原 20 词基础上 +5）**：

| 医学向（保留） | 新增（V9.7 反门店）|
|-------------|------------------|
| 1. 斑块 / 2. 溶栓 / 3. 血栓 | **21. 美容院** |
| 4. 认知/阿尔茨海默/痴呆 | **22. 养生馆** |
| 5. 熬夜 / 6. 三高 / 7. 高血压 | **23. 社区门店** |
| 8. 心梗 / 9. 脑梗 / 10. 中风 | **24. 分销商 / 分销** |
| 11. 活性 FU / 12. RCT/临床 | **25. 门店老板** |
| 13. 专家共识 / 14. 浙大 | |
| 15. 市一97例 / 16. 纳豆 vs 药 | |
| 17. 慢病管理 / 18. 心脑血管 | |
| 19. 非药物干预 / 20. 抗凝 | |

**算法**：

```python
def check_frozen_keywords(title: str, angle: str) -> list[str]:
    hits = []
    now = datetime.now(timezone.utc)
    for kw in FROZEN_KEYWORDS:
        if kw in title or kw in angle:
            last_used = _query_last_used(kw)
            if last_used and (now - last_used).days < 30:
                hits.append(kw)
    return hits
```

**命中逻辑**：任一词命中冷冻期 → 选题降级为 B 级并标记 `frozen_hit`，topic-scout 必须换角度或换核心词。

---

## 四、topic-scout 执行流程（V9.7 升级）

```
1. 读本文件（选题八维 + 三层去重）
2. 读 references/title-playbook.md（45 公式 + 张力 6 维 + 三库禁用词）
3. 读 references/knowledge-base.md（企业/产品/临床事实 + 目标人群画像）
4. 读 references/topic-library/README.md（分块选题库 + 8 角度硬约束）
5. 读当日 hotspots/$(date).json（无则跳过）
6. 生成 20 个候选
   ├─ 每候选标注 dimension (M1-M8)
   ├─ 每候选 3-5 个 data_points
   ├─ 每候选 1 个 angle
   └─ 每候选套用的 title-playbook 公式编号 (F1-F45)
7. 三层去重
   ├─ Layer 1 (30 天指纹) → 剔除
   ├─ Layer 2 (维度配额 + M6/M7 硬线) → 超额剔除
   └─ Layer 3 (25 词 30 天冷冻) → 降级或改写
8. 反面示例扫描 → 命中任一"禁止"条直接剔除
9. 剩余按 S/A/B 五维评分排序
10. 挑 10 条进卡片（用户勾 5 条）
    ├─ 必覆盖 ≥5 维度
    ├─ M7 ≤ 1 条（硬线）
    ├─ M6+M7 ≤ 2 条
    └─ C 端维度（M1+M3+M4+M8）≥ 6/10
```

---

## 五、日志结构（V9.7 扩展字段）

`logs/topic-history.jsonl` 每条记录：

```json
{
  "date": "2026-04-21T10:00:00+00:00",
  "session_id": "SID-xxx",
  "title": "...",
  "title_hash": "abc123def456",
  "line": "...",
  "angle": "...",
  "data_points": ["市一97例", "浙大120人RCT", "认知65%"],
  "dimension": "M1",
  "formula": "F5",                    // V9.7 新增：套用的 title-playbook 公式编号
  "frozen_keywords": ["斑块"],
  "audience": "C-end-middle-aged",    // V9.7 新增：C-end-* / B-end-*
  "used_in": "candidate|selected|published"
}
```

---

## 六、自查清单（topic-scout 输出前过一遍）

- [ ] 10 候选每个都有 dimension + formula + audience 三字段
- [ ] 10 候选覆盖 ≥5 个维度
- [ ] M7 ≤ 1 条
- [ ] M6 + M7 ≤ 2 条
- [ ] C 端维度占比 ≥ 60%
- [ ] 无 Layer 1 指纹命中
- [ ] 无 Layer 2 维度超额
- [ ] 25 词冷冻命中的已降级或改写
- [ ] 反面示例 4 类全部规避
- [ ] 每条有 3+ data_points
- [ ] S/A/B 评级分布合理

---

## 七、V9.7 变更摘要

| 项 | V9.1 | V9.7 |
|---|------|------|
| 坐标维度 | 六维 M1-M6 | **八维 M1-M8**（加 M7 招商 + M8 名人古法）|
| M6 每日上限 | 1（泛）| **1（仅产品科普）**|
| M7 每日上限 | - | **1（硬线，招商场景）**|
| 最少维度覆盖 | 5 选题 ≥ 3 维度 | **10 选题 ≥ 5 维度**|
| C 端占比 | 未约束 | **≥ 60%**|
| 三层去重实装 | 纸面 | **全代码化**|
| 冷冻词表 | 20 词 | **25 词（加 5 反门店）**|
| 反面示例 | 无 | **4 类显式禁止**|
