# 日生研 Skill 架构可视化索引

> v8 设计稿 · 2026-04-20 · 基于客户反馈第二轮迭代

## 图索引

| 图 | 文件 | 说明 |
|----|------|------|
| 1 | [01-overall-architecture.md](./01-overall-architecture.md) | 整体五层架构（入口/编排/执行/知识/交付） |
| 2 | [02-two-modes.md](./02-two-modes.md) | 全自动 vs 引导打磨 双模式对比 |
| 3 | [03-multi-agent.md](./03-multi-agent.md) | 多 Agent 协作机制（主调度 + 5 个子 Agent） |
| 4 | [04-topic-dedup.md](./04-topic-dedup.md) | 选题去重机制（30天滚动窗口 + 三维指纹） |

## 飞书云文档（可直接渲染）

https://hcnf4puys7we.feishu.cn/docx/MMsrd2fwIowJORxleKwc9jlrnjf

## v8 落地顺序（施工清单）

1. [ ] `scripts/guard.py` + `session.json` schema（硬校验跳步）
2. [ ] `logs/topic-history.jsonl` + 三维指纹去重逻辑
3. [ ] 5 个子 Agent 提示词模板（agents/*.md）
4. [ ] 双入口命令 `/nsksd-auto` + `/nsksd-guided`
5. [ ] 配图官独立化 + 端到端测试
6. [ ] 3 份云文档 A/B/C 生成脚本
7. [ ] GitHub 仓库同步
