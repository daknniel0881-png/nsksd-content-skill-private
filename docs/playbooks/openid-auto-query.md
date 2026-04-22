# Playbook：自动查询飞书 open_id / chat_id

> 通过 lark-cli 零参数查询，无需登录 api-explorer 或翻日志。
> 前提：`lark-cli auth login --as user` 已完成。

---

## 场景一：查自己的 open_id

```bash
lark-cli contact +get-user --as user --jq '.data.user.open_id'
```

预期输出：
```
"ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

---

## 场景二：查别人的 open_id（按姓名/手机号/邮箱）

```bash
# 按姓名
lark-cli contact +search-user --query "张三" --as user --jq '.data.users[0].open_id'

# 按手机号（含国际区号）
lark-cli contact +search-user --query "+8613812345678" --as user --jq '.data.users[0].open_id'
```

预期输出：
```
"ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

---

## 场景三：查我所在的群及其 chat_id

```bash
lark-cli im chats list --as user --jq '.data.items[] | {name: .name, chat_id: .chat_id}'
```

预期输出（每行一个群）：
```
{"name":"日生研客户群","chat_id":"oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}
{"name":"内容部","chat_id":"oc_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"}
```

---

## 场景四：查某群的成员 open_id 列表

```bash
# 先拿到 chat_id（见场景三），再查成员
lark-cli im +chat-members --chat-id "oc_xxxxxxxx" --as user --jq '.data.items[] | {name: .name, open_id: .member_id}'
```

预期输出：
```
{"name":"张三","open_id":"ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}
{"name":"李四","open_id":"ou_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"}
```

---

## 失败排查

| 现象 | 原因 | 解决 |
|------|------|------|
| `lark-cli: command not found` | 未安装 | `npm install -g @nicepkg/lark-cli` |
| `identity: user` 但 open_id 为空 | user 身份未登录 | `lark-cli auth login --as user` |
| 返回空 users 列表 | 查询词无匹配 | 换手机号或全名重试 |
| `code: 99991663`（权限不足） | lark-cli user 身份缺少联系人权限 | 检查应用后台是否已开通 `contact:user.base:readonly` |
