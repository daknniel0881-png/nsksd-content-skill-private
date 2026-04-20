# 飞书长连接交互层(打磨模式)

## 做什么

让日生研内容创作 skill 在打磨模式下,每一步都能:
1. 推一张**带输入框**的飞书卡片给员工
2. 员工输入修改意见后点提交
3. **无需公网 URL**,通过飞书长连接(WebSocket)实时收到回调
4. 提交后卡片自动变灰锁定,保留原正文 + 展示用户输入
5. 用户输入写入会话 JSON,主 Agent 可轮询读取进入下一步

## 核心文件

| 文件 | 作用 |
|------|------|
| `lark_ws_listener.py` | 长连接监听器(常驻进程) |
| `card_builder.py` | 3 类卡片模板构建器(feedback/multi_choice/confirm) |
| `session_manager.py` | 会话状态机(主 Agent CLI 调用) |
| `run_listener_mac.sh` | Mac 启停脚本 |
| `run_listener_win.bat` | Windows 启停脚本 |
| `sessions/` | 会话 JSON 落盘目录(监听器写 + 主 Agent 读) |
| `events.log` | 事件审计日志 |

## 快速开始

### Mac

```bash
cd ~/.claude/skills/nsksd-content/scripts/interactive
./run_listener_mac.sh start   # 首次会自动建 venv + pip install lark-oapi
./run_listener_mac.sh status  # 看是否在跑
./run_listener_mac.sh logs    # 实时日志
./run_listener_mac.sh stop
```

### Windows

```cmd
cd %USERPROFILE%\.claude\skills\nsksd-content\scripts\interactive
run_listener_win.bat start
run_listener_win.bat status
run_listener_win.bat stop
```

## 主 Agent 的用法(打磨模式一步)

```bash
# 1. 新建会话
SID=$(python3 session_manager.py new)

# 2. 生成"标题大纲"卡片 JSON
CARD=$(python3 card_builder.py feedback | jq -c .)
# (真实场景中 card_builder 会被主 Agent 以 Python 模块方式 import 调用)

# 3. 发卡给员工
lark-cli im +messages-send --user-id $USER_ID \
    --msg-type interactive --content "$CARD" --as bot

# 4. 阻塞等回复(最多 30 分钟)
python3 session_manager.py wait $SID title_outline 1800

# 5. 读到回复 JSON,进入下一步
```

## 前置条件

1. 飞书应用事件订阅已开启 **WebSocket 长连接**(非 HTTP 回调)
2. 应用权限包含:`im:message`(发卡) + `im:card:action`(收卡片回调)
3. 环境变量 `LARK_APP_ID` / `LARK_APP_SECRET` 已设置(或者在 `lark_ws_listener.py` 里改默认值)

## 技术要点(踩坑记录)

- ✅ 卡片必须用 **schema 2.0** + `form` 容器 + `form_action_type=submit` 按钮,否则 `form_value` 永远为空
- ✅ input 设 `required: false`,避免飞书前端自动弹"必填"提示
- ✅ 锁定版卡片保留**原 header 标题 + 原 body markdown**,只灰化头 + 加禁用按钮 + 展示输入
- ✅ 事件回调 return 的 `card.type="raw"` + `card.data=新卡片JSON` 会整张替换原卡
- ✅ Python 跨平台:Mac/Win 同一份 lark_ws_listener.py,差别只在启停脚本

## 验证过的链路

- 2026-04-20:长连接握手成功、卡片发送成功、输入框值正确回传、锁定卡正确渲染
- 事件样本见 `events.log`
