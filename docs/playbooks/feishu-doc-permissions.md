# Playbook：飞书云文档权限开放（V10.2）

> **坑位 & 真相**：`lark-cli docs +create --as bot` 创建的文档，**只有 bot 和当前 CLI 用户能读**，客户打开是 403。

---

## 核心真相

调 `lark-cli docs +create --as bot` 的返回里有一段：

```json
{
  "permission_grant": {
    "member_type": "openid",
    "user_open_id": "ou_01317d9f...",   ← 当前 CLI 用户（曲率自己）
    "perm": "full_access",
    "status": "granted"
  }
}
```

CLI 已经把创建者（=曲率）设为 full_access，但**其他任何人（客户、客户群、客户团队）全部无权限**。点开链接会看到 "您没有此文档的查看权限"。

解法：创建文档后立刻调 `/drive/v1/permissions/{token}/members` 把客户群 / 客户个人加进来。

---

## 完整调用链（V10.2）

```
┌───────────────────────────────────────────────────────────┐
│ 1. 创建文档                                                 │
│    lark-cli docs +create \                                │
│        --title "文章标题" \                                  │
│        --markdown @article.md \                           │
│        --as bot                                           │
│    → data.doc_id  = "YdYbdyzc0o3Xu4xx9LScVNw3nqd"         │
│    → data.doc_url = "https://www.feishu.cn/docx/Yd..."    │
│    👆 此时只有 bot + 曲率能读                               │
└──────────────────────┬────────────────────────────────────┘
                       ↓
┌───────────────────────────────────────────────────────────┐
│ 2. 把客户群加成协作者                                          │
│    lark-cli drive permission.members create \             │
│        --params '{"token":"<doc_id>","type":"docx"}' \    │
│        --data '{"member_type":"chatid",                   │
│                 "member_id":"oc_xxx",                     │
│                 "perm":"edit"}' \                         │
│        --as bot                                           │
│    → 群内所有人都能打开文档                                    │
└──────────────────────┬────────────────────────────────────┘
                       ↓
┌───────────────────────────────────────────────────────────┐
│ 3.（可选）把曲率 admin 加管理员                                 │
│    lark-cli drive permission.members create \             │
│        --params '{"token":"<doc_id>","type":"docx"}' \    │
│        --data '{"member_type":"openid",                   │
│                 "member_id":"ou_01317d9f...",             │
│                 "perm":"full_access"}' \                  │
│        --as bot                                           │
└───────────────────────────────────────────────────────────┘
```

---

## 关键参数速查

### `params`（URL 路径 + query 参数，JSON 编码）

| 字段 | 必填 | 说明 |
|------|------|------|
| `token` | ✅ | 步骤 1 返回的 `data.doc_id` |
| `type` | ✅ | `docx`（新版文档）/ `doc` 老版 / `sheet` / `bitable` / `wiki` / `file` |

### `data`（请求体 JSON）

| 字段 | 必填 | 说明 |
|------|------|------|
| `member_type` | ✅ | `openid`(ou_...) / `chatid`(oc_...) / `userid` / `email` / `unionid` / `groupid` |
| `member_id` | ✅ | 对应 member_type 的 ID 值 |
| `perm` | ✅ | `view` 只读 / `edit` 可编辑 / `full_access` 可管理 |
| `perm_type` | ❌ | `container` 仅容器 / `single_page` 仅本页（默认 container）|
| `type` | ❌ | `user` / `chat` / `department` / `group`（可省略，与 member_type 同义）|

### 常见 member_type 对应 ID 前缀

| member_type | ID 前缀 | 含义 |
|-------------|---------|------|
| `openid` | `ou_` | 应用维度的用户 ID（同一用户在不同 App 下 openid 不同）|
| `unionid` | `on_` | 租户维度的用户 ID（同一用户在同企业不同 App 下一致）|
| `userid` | 任意 | 企业自定义 ID |
| `chatid` | `oc_` | 飞书群 ID |
| `groupid` | 任意 | 用户组 |
| `email` | xxx@xxx | 邮箱（仅租户内成员）|

---

## V10.2 代码

`scripts/lib/feishu_doc_publish.py::share_doc_to_customer`：

```python
def share_doc_to_customer(doc_token: str,
                          member_ids: list,  # [(member_type, member_id)]
                          perm: str = "edit") -> dict:
    """返回 {"granted":[...], "failed":[...]}"""
```

`scripts/nsksd_publish.py` 里创建文档后自动调：

```python
doc_url, doc_token = create_fallback_doc(title, html)
if doc_token:
    members = []
    # 客户群（oc_...）
    if customer_chat.startswith("oc_"):
        members.append(("chatid", customer_chat))
    # 曲率 admin（ou_...）
    if admin_open.startswith("ou_"):
        members.append(("openid", admin_open))
    share_doc_to_customer(doc_token, members, perm="edit")
```

---

## 获取客户 chat_id / open_id 的办法

### 1. 客户群 chat_id（推荐）

```bash
# 让客户把"日生研内容小助手"拉进他们的内容审稿群
# 然后列出 bot 所在的所有群
lark-cli im chats --as bot
# 返回里找到目标群的 chat_id，形如 oc_xxx
```

填到 `~/.nsksd-content/config.json`：

```json
{
  "feishu": {
    "customer_open_chat_id": "oc_真实群ID"
  }
}
```

### 2. 客户个人 open_id

```bash
# 用邮箱换
lark-cli contact user.batch_get_id --as bot \
    --data '{"emails":["customer@company.com"]}'
# 返回 open_id 形如 ou_xxx
```

---

## 验证方法

1. 授权完用手机飞书（非曲率账号）打开 doc_url，应该直接进入不提示 403
2. 命令行验证：
   ```bash
   lark-cli drive permission.members auth \
       --params '{"token":"<doc_id>","type":"docx"}' \
       --data '{"perm":"view"}' \
       --as bot
   # 返回 is_permitted: true
   ```

---

## 常见错误

| 错误 | 原因 | 处理 |
|------|------|------|
| "您没有此文档的查看权限" | 创建后没加协作者 | 跑 share_doc_to_customer |
| `1061002` InvalidArgument | member_id 格式不对 | 核对前缀（oc_ / ou_ / on_）|
| `1061003` NotAuthorized | bot 不是文档所有者 | `--as bot` 和创建时一致 |
| chat_id 对不上 | 客户群名换了 / bot 被踢 | 重新让客户把 bot 拉进群 |

---

## 红线

- ❌ 创建完文档不加协作者 → 客户 100% 看不了
- ❌ 加权限用 `--as user` 但 token 是 bot 创的 → 1061003
- ✅ 统一 `--as bot`，bot 创建 bot 授权
- ✅ 客户群 chatid 优先，覆盖面最大，客户换人不用重新配
