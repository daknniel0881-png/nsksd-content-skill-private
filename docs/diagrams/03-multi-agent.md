# 图 3 · 多 Agent 协作架构（核心创新）

```mermaid
graph TB
    classDef master fill:#ffe3e3,stroke:#c92a2a,color:#000
    classDef worker fill:#e5dbff,stroke:#5f3dc4,color:#000
    classDef context fill:#fff4e6,stroke:#e67700,color:#000
    classDef shared fill:#e7f5ff,stroke:#1971c2,color:#000
    classDef output fill:#c5f6fa,stroke:#0c8599,color:#000

    subgraph master_layer["主 Agent 层（轻上下文）"]
        Master[master-orchestrator<br/>主调度 Agent<br/>只管流程状态<br/>不读知识库原文]:::master
    end

    subgraph shared_state["共享状态层"]
        Session[session.json<br/>当前步骤+用户反馈]:::shared
        TopicHistory[topic-history.jsonl<br/>30天选题日志]:::shared
        Artifacts[artifacts/<br/>各步骤产物]:::shared
    end

    subgraph scout["选题官 topic-scout"]
        ScoutCtx[独立上下文<br/>读: knowledge-base精华<br/>读: topic-library<br/>读: topic-history去重]:::context
        ScoutWork[输出: 10个选题+S/A/B评级]:::worker
    end

    subgraph outliner["标题大纲官 title-outliner"]
        OutCtx[独立上下文<br/>读: 用户选中的选题<br/>读: 标题公式库<br/>读: 合规禁用词]:::context
        OutWork[输出: 每选题5标题+完整大纲]:::worker
    end

    subgraph writer["撰稿官 article-writer"]
        WrCtx[独立上下文<br/>读: 确认的标题大纲<br/>读: 核心文档7份<br/>读: science-popular-style.md]:::context
        WrWork[输出: 1500-2500字全文]:::worker
    end

    subgraph designer["配图官 image-designer"]
        DsCtx[独立上下文<br/>读: 全文内容<br/>读: 5种配图风格模板<br/>调: Gemini 3 Pro Image]:::context
        DsWork[输出: 配图占位符→实际图片]:::worker
    end

    subgraph publisher["排版推送官 format-publisher"]
        PubCtx[独立上下文<br/>读: 完稿+配图<br/>读: 31个主题<br/>调: format.py + publish.py]:::context
        PubWork[输出: 草稿箱 media_id]:::worker
    end

    Master -->|派单+上下文打包| scout
    scout -->|产物回写| Artifacts
    Master -->|派单| outliner
    outliner -->|产物| Artifacts
    Master -->|派单| writer
    writer -->|产物| Artifacts
    Master -->|派单| designer
    designer -->|产物| Artifacts
    Master -->|派单| publisher
    publisher -->|产物| Artifacts

    Master <--> Session
    scout -.读.-> TopicHistory
    scout -.写入新选题.-> TopicHistory

    Artifacts -.加载上一步产物.-> outliner
    Artifacts -.加载.-> writer
    Artifacts -.加载.-> designer
    Artifacts -.加载.-> publisher
```

## 为什么要多 Agent

**单 Agent 问题**：所有知识塞一个上下文 → 37KB SKILL.md + 77份知识库 + 20项合规 + 31个主题——Agent 注意力被稀释，细节必丢。

**多 Agent 解法**：
- 每个 Agent 只读自己岗位需要的文件（上下文瘦身 5-10 倍）
- 主 Agent 只做流程编排，不碰内容
- 产物通过 `artifacts/` 文件系统传递，不走对话上下文

## 每个 Agent 的最小上下文

| Agent | 读什么 | 不读什么 | 输出到 |
|-------|--------|---------|--------|
| topic-scout | knowledge-base.md + topic-library.md + topic-history.jsonl | 77份原文、31个主题、合规清单 | artifacts/step1-topics.json |
| title-outliner | step1选中的选题 + 标题公式库 | 配图、主题、全文 | artifacts/step2-titles.json |
| article-writer | step2产物 + 核心文档7份 + science-popular-style | 选题库、主题、推送配置 | artifacts/step3-article.md |
| image-designer | step3全文 + 配图风格模板 | 合规清单、主题、发布配置 | artifacts/step4-images/ |
| format-publisher | step3全文 + step4配图 + 主题选择 | 选题库、知识库原文 | artifacts/step5-media_id.txt |

## 实现机制

用 Claude Code 的 Task Tool（subagent_type）派发：

```python
# 伪代码
master.dispatch(
    subagent_type="general-purpose",
    role="topic-scout",
    prompt="读取 references/knowledge-base.md + topic-history.jsonl，去重后生成10个选题，输出到 artifacts/step1-topics.json",
    allowed_files=[
        "references/knowledge-base.md",
        "references/topic-library.md",
        "/tmp/nsksd/topic-history.jsonl"
    ]
)
```

子 Agent 跑完归还结果，主 Agent 不继承子 Agent 的长上下文——只拿到产物文件路径。
