# 图 2 · 双模式对比（自动 vs 引导）

```mermaid
graph TB
    classDef start fill:#d3f9d8,stroke:#2f9e44,color:#000
    classDef step fill:#e7f5ff,stroke:#1971c2,color:#000
    classDef stop fill:#ffe3e3,stroke:#c92a2a,color:#000
    classDef doc fill:#fff4e6,stroke:#e67700,color:#000
    classDef done fill:#c5f6fa,stroke:#0c8599,color:#000
    classDef auto fill:#f3d9fa,stroke:#862e9c,color:#000

    Start([用户触发]):::start

    Start --> Pick{选择模式}

    Pick -->|"/nsksd-auto"| Auto1[选题官 生成10个选题]:::auto
    Auto1 --> Auto2[发多选卡 到飞书]:::auto
    Auto2 --> AutoWait[等待用户勾选]:::auto
    AutoWait --> Auto3[自动跑 标题+大纲+文案+配图+排版]:::auto
    Auto3 --> AutoGuard{合规硬校验}:::stop
    AutoGuard -->|通过| Auto4[直接推送 公众号草稿箱]:::auto
    AutoGuard -->|不通过| AutoBlock[拦截+报告]:::stop
    Auto4 --> AutoDone([飞书通知 已入草稿箱]):::done

    Pick -->|"/nsksd-guided"| G1[Step1 选题官 生成10个]:::step
    G1 --> GD1[写入 云文档A]:::doc
    GD1 --> GW1[Guard: 等待用户回复<br/>选编号+修改意见]:::stop
    GW1 --> G2[Step2 标题大纲官<br/>基于选中选题生成]:::step
    G2 --> GD2[写入 云文档B]:::doc
    GD2 --> GW2[Guard: 等待用户确认<br/>标题+大纲OK?]:::stop
    GW2 --> G3[Step3 撰稿官<br/>写全文]:::step
    G3 --> G3B[配图官<br/>逐图确认]:::step
    G3B --> G3C[排版官<br/>应用主题]:::step
    G3C --> GD3[写入 云文档C<br/>全文+配图+排版效果]:::doc
    GD3 --> GW3[Guard: 云文档预审<br/>确认推送?]:::stop
    GW3 --> G4[Step4 推送草稿箱]:::step
    G4 --> GuideDone([飞书通知 已入草稿箱]):::done

    GW1 -.->|修改意见| G1
    GW2 -.->|修改意见| G2
    GW3 -.->|修改意见| G3
```

## 两种模式的本质区别

| 维度 | 全自动模式 | 引导打磨模式 |
|------|----------|-------------|
| **适用人群** | 业务/文字能力较弱的一线员工 | 业务/文字能力较强的资深员工 |
| **目标** | 堆量，跑得快 | 打磨，跑得稳 |
| **确认次数** | 1次（只在多选卡勾选） | 3次（选题/标题大纲/全文预审） |
| **云文档** | 0份 | 3份 |
| **每步可修改** | 否 | 是（打回重跑） |
| **合规检查** | 推送前硬校验 | 每步都走 + 推送前硬校验 |
| **失败兜底** | 合规不过直接拦截 | 每步都可人工接管 |

## 硬停机制（Guard）

- 引导模式每一步都调用 `python3 scripts/guard.py check --step N`
- 上一步状态非 `confirmed` 则 `exit 1`，Agent 不得进入下一步
- 用户回复后调用 `guard.py confirm --step N --user-reply "..."` 落盘状态
- 状态文件：`/tmp/nsksd-session-{date}.json`
