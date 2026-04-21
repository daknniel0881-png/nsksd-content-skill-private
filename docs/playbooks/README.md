# docs/playbooks/ · 做事说明书总索引

> 遇到问题，先翻这里。每个 playbook 都是"场景 → 步骤 → 参数 → 常见错误 → 验证方法 → 回查兜底"的结构。

---

## 目录

| 文件 | 覆盖场景 | 何时翻阅 |
|------|----------|----------|
| [wechat-publish.md](./wechat-publish.md) | 公众号推送全流程 | 推送草稿箱失败、403/40164 报错、图片宽度错乱、author 字段为空时 |
| [feishu-card.md](./feishu-card.md) | 飞书交互卡片 | 卡片乱码、多选卡不显示、trigger 文件流、chat_id 获取、凭证来源 |
| [feishu-doc.md](./feishu-doc.md) | 飞书云文档保底 | 公众号凭证缺失或推送失败后的兜底、lark-cli 语法、权限配置 |
| [cover-image.md](./cover-image.md) | 配图生成与转换 | 封面/内文图片生成、尺寸要求、Markdown 转 HTML 时 width=auto 保持 |
| [data-verification.md](./data-verification.md) | 数据与事实核查 | 写文章前核查数据来源、WebFetch 验证 URL、找不到来源的降级写法 |
| [style-card.md](./style-card.md) | 排版主题选择卡 | 首次配置 preferred_theme、用户说"换排版"时弹卡、查看全部 31 个主题 |

---

## 快速定位

**我遇到的是……**

- 推送公众号报错 403 → [wechat-publish.md](./wechat-publish.md#常见错误)
- 飞书卡片显示乱码 → [feishu-card.md](./feishu-card.md#乱码防护)
- 公众号凭证没有，要保底 → [feishu-doc.md](./feishu-doc.md#何时触发保底)
- 配图尺寸不对 → [cover-image.md](./cover-image.md#尺寸规范)
- 数据找不到来源 → [data-verification.md](./data-verification.md#找不到来源怎么办)
- 用户想换排版风格 → [style-card.md](./style-card.md#触发弹卡)

---

## 通用约定

1. **凭证不写在代码里**：所有凭证从 `~/.nsksd-content/config.json` 读，chmod 600
2. **图片宽度**：转 HTML 时一律 `width=auto`，不写固定像素
3. **飞书权限**：给 chat_id 而不是 user_id，除非场景明确要求
4. **保底顺序**：公众号推送失败 → 先飞书云文档 → 再 IM 推链接
5. **数据必核查**：每条数据三问（URL 活着吗？有第二来源吗？）后才写进文章
