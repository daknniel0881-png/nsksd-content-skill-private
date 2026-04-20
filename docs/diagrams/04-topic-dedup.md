# 图 4 · 选题去重机制（30天窗口）

```mermaid
graph TB
    classDef input fill:#d3f9d8,stroke:#2f9e44,color:#000
    classDef logic fill:#e5dbff,stroke:#5f3dc4,color:#000
    classDef data fill:#fff4e6,stroke:#e67700,color:#000
    classDef out fill:#c5f6fa,stroke:#0c8599,color:#000
    classDef reject fill:#ffe3e3,stroke:#c92a2a,color:#000

    Start[选题官启动]:::input
    Start --> Load[加载 topic-history.jsonl]:::logic

    Load --> Filter30[筛选 最近30天记录]:::logic
    Filter30 --> ExtractKeys[提取去重指纹<br/>标题hash + 角度hash + 数据点]:::logic

    ExtractKeys --> Gen[读知识库+热点<br/>碰撞生成 候选选题池 20个]:::logic

    Gen --> Check{每个候选<br/>是否命中30天指纹?}:::logic

    Check -->|命中| Reject[淘汰 or 角度重构]:::reject
    Check -->|未命中| Pass[进入评审打分]:::logic

    Reject -.->|角度重构后重审| Check

    Pass --> Score[五维评分 S/A/B分级]:::logic
    Score --> Output[输出10个选题]:::out

    Output --> WriteLog[写入 topic-history.jsonl<br/>含日期+标题+角度+数据点]:::data

    WriteLog --> ShowUser[呈现给用户]:::out

    subgraph history_file["topic-history.jsonl 字段"]
        F1[date: 2026-04-20]
        F2[title: 1062人临床如何打破...]
        F3[line: 科学信任]
        F4[angle: 临床数据权威背书]
        F5[data_points: 1062人,浙大65%,EFSA]
        F6[used_in: published/draft/rejected]
    end

    WriteLog -.-> history_file
```

## 去重机制的 3 层指纹

不只是标题去重，三维指纹匹配：

| 指纹 | 匹配规则 | 示例 |
|------|---------|------|
| **标题语义** | 标题去停用词后 jaccard > 0.6 视为重复 | "1062人临床证明X" vs "1062人试验揭示X" → 命中 |
| **核心角度** | angle 字段严格匹配 | "临床数据权威背书" 30天内只能出现1次 |
| **数据点组合** | data_points 集合重合 ≥ 2 视为重复 | 同时用了"1062人+EFSA"的选题合并计数 |

## 30天滚动窗口

```
Day 1:    选题A (用了1062人数据)
Day 5:    选题B (用了浙大65%+EFSA)
Day 10:   选题C (品牌故事线，无重叠)
...
Day 31:   选题A 的指纹 过期 → 可以重新出现（换角度重写）
```

## 写入时机

| 时机 | used_in 字段 |
|------|------------|
| 选题官输出10个 | `candidate` |
| 用户选中的（进入第二步） | `selected` |
| 最终推送草稿箱 | `published` |
| 用户打回/淘汰 | `rejected` |

**关键**：未被选中的候选选题也入库，防止下次又推一遍。

## 紧急逃生阀

知识库就这么多素材，硬去重30天可能卡死。方案：
- 30天全命中 → 允许**角度重构**复用（同素材不同切入）
- 角度重构 ≥ 3次还命中 → 报警给主 Agent + 管理员："选题池枯竭，需补知识库"

## 文件位置

```
~/.claude/skills/nsksd-content/
  └── logs/
      └── topic-history.jsonl   # 每行一个JSON记录
```
