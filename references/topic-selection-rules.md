# 日生研内容创作 · 选题规则与去重机制（V9.1）

> 本文件是 nsksd-content Skill 的选题层"宪法"。topic-scout Agent 每次生成选题前必须读本文件并严格遵守。
> 解决问题：**每日推送存在选题重复**——过去依赖 30 天指纹去重仍不够，本次从"坐标系 + 配额 + 禁用词窗口"三层阻断重复。

> **V9.1 补充**：在"六维坐标系"之上叠加**分块选题库（M1-M6 内容模块）**——见 `references/topic-library/README.md`。
>
> - **六维坐标系 M1-M6**（本文件）：选题的**视角维度**（医学循证/大会热点/节气养生/用户痛点/政策监管/产品科普），用于保证每日跨维度均衡。
> - **分块选题库 M1-M6**（topic-library/README.md）：选题的**外部资讯来源模块**（行业热点/纳豆激酶研究/健康管理/真实案例/政策监管/招商场景），由 `scripts/topic-crawler.ts` 按关键词池抓取，按月归档。
> - **二者关系**：资讯模块是"原料池"，坐标系是"成品分布约束"。一条 M6（招商）模块的资讯，可以切出 M4（用户痛点）或 M6（产品科普）的坐标维度选题。
> - **招商多角度硬约束**：M6 招商模块严禁只切"养生馆老板卖产品→利润增长"单一角度，必须覆盖 **8 个角度**（店主专业形象升级 / 客户健康咨询能力 / 会员裂变粘性 / 产品组合设计 / 合规风险规避 / 跨品类联动 / 社群运营 / 门店动线话术），详见 topic-library/README.md。

---

## 一、选题六维坐标系（强制跨维度）

每日推送 5 个选题，必须覆盖 **≥3 个维度**（同一天内任一维度上限 2 个）。

| 维度 | 定义 | 典型角度 | 每日上限 | 每周上限 |
|------|------|---------|---------|---------|
| M1 · 医学循证 | 临床研究/RCT/专家共识/文献综述 | 1062人临床、浙大RCT、认知衰退65% | 2 | 6 |
| M2 · 大会热点 | 行业大会/峰会/学术会议 | FFC2026、营养健康大会、五湖大会 | 1 | 2 |
| M3 · 节气养生 | 时令/节气/季节慢病防控 | 秋冬血管收缩、春季养肝、三高调理 | 1 | 3 |
| M4 · 用户痛点 | 真实用户焦虑/场景问题 | 熬夜血管、加班三高、父母斑块 | 2 | 5 |
| M5 · 政策监管 | 国标/蓝皮书/政策文件/行业监管 | 专家指引、保健食品新规、药食同源 | 1 | 2 |
| M6 · 产品科普 | 成分/活性/工艺/差异化对比 | 活性FU、同样纳豆差10倍、选品逻辑 | 1 | 3 |

**硬约束**：
- 5 选题 = 至少覆盖 3 个不同维度
- 同一维度单日最多 2 条
- 维度命中统计来源于 `logs/topic-history.jsonl` 的 `dimension` 字段（新增）

---

## 二、三层去重机制（升级版）

### Layer 1 · 30天指纹去重（已有，继续保留）

现有 `scripts/topic_history.py` 的三维指纹算法：
- `title_hash`：标题去停用词后 SHA1 前 12 位
- `angle`：核心角度关键词归一化严格匹配
- `data_points`：数据点集合交集 ≥ 2 视为重复

**命中任一维度 = 直接剔除**。

### Layer 2 · 维度配额（本版新增）

读取 `logs/topic-history.jsonl` 近 7 天记录，按 `dimension` 字段统计：
- 某维度周用量达到"每周上限"→ 本批次禁止再出该维度选题
- 若 5 选题不可避免都集中在同一维度 → 强制向 topic-scout 抛错，要求重生成

### Layer 3 · 禁用词滚动窗口（本版新增）

下表关键词在"首次出现后 30 天内"禁止重复命中为主标题核心词：

| 一月内禁用高频词（命中后 30 天冷冻） |
|--|
| 1. 斑块 |
| 2. 溶栓 |
| 3. 血栓 |
| 4. 认知 / 阿尔茨海默 / 痴呆 |
| 5. 熬夜 |
| 6. 三高 |
| 7. 高血压 |
| 8. 心梗 |
| 9. 脑梗 |
| 10. 中风 |
| 11. 活性FU |
| 12. RCT / 临床 |
| 13. 专家共识 / 专家指引 |
| 14. 浙大 |
| 15. 1062人 / 大样本 |
| 16. 纳豆 vs 药 |
| 17. 慢病管理 |
| 18. 心脑血管 |
| 19. 非药物干预 |
| 20. 抗凝 |

**算法**：
```python
# scripts/topic_history.py 新增 check_frozen_keywords
def check_frozen_keywords(title: str, angle: str) -> list[str]:
    """返回标题/角度命中且仍在30天冷冻期的禁用词列表"""
    hits = []
    now = datetime.now(timezone.utc)
    for kw in FROZEN_KEYWORDS:
        if kw in title or kw in angle:
            last_used = _query_last_used(kw)  # 读 history jsonl
            if last_used and (now - last_used).days < 30:
                hits.append(kw)
    return hits
```

**命中逻辑**：任一词命中冷冻期 → 选题降级为 B 级，需要 topic-scout 主动换角度或替换核心词。

---

## 三、topic-scout 执行流程（V9.0 升级）

```
1. 读 references/topic-library.md（31 主题池）+ themes-curated.md（10 精选）
2. 读 references/knowledge-base.md（企业/产品/临床事实）
3. 读 references/wechat-benchmark/titles-pattern-analysis.md（高阅读标题共性）
4. 生成 20 个候选
   ├─ 每个候选必须标注 dimension (M1-M6)
   ├─ 每个候选必须标注 3-5 个 data_points
   └─ 每个候选必须标注 1 个 angle
5. 三层去重过滤
   ├─ Layer 1 (30天指纹) → 剔除
   ├─ Layer 2 (维度配额) → 超额剔除
   └─ Layer 3 (禁用词30天冷冻) → 降级或改写
6. 剩余按 S/A/B 五维评分排序
7. 挑选 10 个进卡片（最终用户勾 5 个）
   ├─ 必须覆盖 ≥3 个维度
   └─ 同维度不超过 2 条
```

---

## 四、日志结构（V9.0 扩展字段）

`logs/topic-history.jsonl` 每条记录新增：

```json
{
  "date": "2026-04-21T10:00:00+00:00",
  "session_id": "SID-xxx",
  "title": "...",
  "title_hash": "abc123def456",
  "line": "...",
  "angle": "...",
  "data_points": ["1062人", "浙大RCT", "认知65%"],
  "dimension": "M1",              // V9.0 新增
  "frozen_keywords": ["斑块", "认知"],  // V9.0 新增
  "used_in": "candidate|selected|published"
}
```

---

## 五、自查清单（topic-scout 输出前过一遍）

- [ ] 10 候选每个都有 dimension 标签
- [ ] 10 候选覆盖 ≥3 个维度
- [ ] 同维度不超过 2 条
- [ ] 无 Layer 1 指纹命中
- [ ] 无 Layer 2 维度超额
- [ ] 冷冻期禁用词命中的已降级或改写
- [ ] 每条都有 3+ data_points
- [ ] S/A/B 评级分布合理（不是全 S）
