# 图 1 · 日生研内容创作 Skill 整体架构

```mermaid
graph TB
    classDef input fill:#d3f9d8,stroke:#2f9e44,color:#000
    classDef mode fill:#e7f5ff,stroke:#1971c2,color:#000
    classDef agent fill:#e5dbff,stroke:#5f3dc4,color:#000
    classDef data fill:#fff4e6,stroke:#e67700,color:#000
    classDef output fill:#c5f6fa,stroke:#0c8599,color:#000
    classDef guard fill:#ffe3e3,stroke:#c92a2a,color:#000

    User[曲率 / 一线员工]:::input

    subgraph entry["入口层（两个模式）"]
        Auto["/nsksd-auto<br/>全自动模式<br/>多选卡一键到草稿箱"]:::mode
        Guided["/nsksd-guided<br/>引导打磨模式<br/>每步硬停确认"]:::mode
    end

    subgraph orchestrator["编排层（master-orchestrator · 主调度 Agent）"]
        Router[流程路由 + 状态机]:::agent
        Guard[guard.py<br/>硬校验守门]:::guard
        Session[session.json<br/>流程状态]:::data
    end

    subgraph agents["执行层（5 个专业子 Agent）"]
        A1[选题官<br/>topic-scout]:::agent
        A2[标题大纲官<br/>title-outliner]:::agent
        A3[撰稿官<br/>article-writer]:::agent
        A4[配图官<br/>image-designer]:::agent
        A5[排版推送官<br/>format-publisher]:::agent
    end

    subgraph knowledge["知识与记忆层"]
        KB[references/<br/>4份精华]:::data
        FullKB[knowledge/<br/>77份原文]:::data
        History[topic-history.jsonl<br/>选题去重日志]:::data
        Compliance[compliance-check.py<br/>20项硬校验]:::guard
    end

    subgraph delivery["交付层"]
        Doc1[云文档 A<br/>选题预审]:::output
        Doc2[云文档 B<br/>标题+大纲预审]:::output
        Doc3[云文档 C<br/>全文+排版+配图预审]:::output
        Draft[微信草稿箱]:::output
        Notify[飞书卡片通知]:::output
    end

    User --> entry
    entry --> Router
    Router <--> Guard
    Guard <--> Session
    Router --> A1
    A1 --> A2
    A2 --> A3
    A3 --> A4
    A4 --> A5

    A1 -.-> KB
    A1 -.-> History
    A2 -.-> KB
    A3 -.-> FullKB
    A3 -.-> Compliance
    A5 -.-> Compliance

    A1 --> Doc1
    A2 --> Doc2
    A3 --> Doc3
    A4 --> Doc3
    A5 --> Doc3
    A5 --> Draft
    A5 --> Notify
```

## 读图说明

- **入口层**：两个斜杠命令对应两种使用风格，用户在起步时选定
- **编排层**：主 Agent 只做调度和状态管理，不碰内容——避免一个 Agent 塞太多上下文
- **执行层**：每个子 Agent 单一职责，独立上下文，互不污染
- **知识与记忆层**：选题去重日志（topic-history）是这一版新增，解决"每天选题都一样"
- **交付层**：3 份云文档对应引导模式的 3 次预审；草稿箱是最终出口
