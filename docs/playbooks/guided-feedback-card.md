# 引导反馈卡做事说明书（Guided Feedback Card Playbook）

> **适用场景**：半自动引导模式（`guided`），在每一步子 Agent 产出后向客户推送「产出预览 + 修改意见输入框 + 打回/通过双按钮」的交互卡，收到回调后把意见回流给 Claude session 继续打磨。
>
> **最后更新**：2026-04-21 晚 · V9.6
> **验证状态**：✅ E2E 通过（曲率本人 open_id，空输入/填"123"两种场景均成功）

---

## 1. 成功路径（三步必须按顺序做，少一步就挂）

### Step 1：构造卡片（card_builder.py）
- 使用 `build_guided_feedback_card(session_id, step_name, step_index, total_steps, step_output_md)`
- 返回 schema 2.0 卡片 JSON，包含：
  - `header.template = "blue"`（未锁定态）
  - `body.elements`：产出 markdown + hr + **form 容器**
  - form 内：1 个 input（`feedback_text`，`max_length: 1000`）+ 1 个 `column_set`（`flex_mode: "bisect"`）包 2 个 button
  - 两个 button **必须 `type: "primary"`**（见踩坑记录 · 根因 2）
  - button 的 `form_action_type: "submit"` + `behaviors[0].value` 带 `_skeleton`（原卡骨架，供锁定态重建）

### Step 2：推送卡片（lark-cli）
```bash
lark-cli im +messages-send \
  --receive-id-type open_id \
  --receive-id <user_open_id> \
  --msg-type interactive \
  --content @card.json
```
- 必须 `--receive-id-type open_id`（推私聊），**不要推群 chat_id**
- `--content @file`：相对路径（绝对路径被 lark-cli 1.0.14 拒）

### Step 3：监听回调（lark_ws_listener.py）
- `run_listener_mac.sh start` 启动 WebSocket 长连接
- **必须从 `~/.nsksd-content/config.json` 读 `LARK_APP_ID/SECRET` 注入环境变量**（见踩坑记录 · 根因 3）
- 客户点击按钮后，listener 收到 `card.action.trigger`：
  - 按 `button_value.action` 分流（`approve` / `reject`）
  - 写 feedback 文件：`triggers/guided/{session_id}-{step_name}.feedback`
  - 返回锁定卡（`build_guided_locked_card(skeleton, action, feedback_text, ...)`）替换原消息

---

## 2. 踩坑记录 · 真因与修法

### 根因 1 ❌：锁定卡 `disabled + danger/primary` 组合 → Code-356
**症状**：点 reject 后飞书客户端报 `Code-356`，卡片不更新
**真因**：飞书 schema 2.0 对 `button.disabled: true` + `type: "danger"` 组合做严格校验，返回的锁定卡被拒
**修法**：锁定卡所有 disabled button **统一 `type: "default"`**，视觉差异靠 emoji（🔴/🟢）和 header `template: "grey"` 传递
**代码位置**：`card_builder.py::build_guided_locked_card` 第 405 / 418 行

### 根因 2 ❌：原卡 reject 按钮 `type: "danger" + form_action_type: "submit" + value 嵌 _skeleton` → 事件根本不发网络
**症状**：approve 每次成功（listener 日志有事件），reject 每次失败（listener 日志空的，客户端提示"请选择多选卡片"）
**真因**：飞书客户端对 `form_action_type=submit` 的 button 本地 schema 校验——`primary` 宽容、`danger` 严格。value 里嵌套 `_skeleton` 这种 dict 时，danger 按钮本地校验失败 → 事件不发 → listener 永远收不到
**修法**：reject 按钮 `type` 从 `danger` 改 `primary`，视觉靠 🔴 emoji 保留红色视觉
**代码位置**：`card_builder.py::build_guided_feedback_card` 第 295 行

### 根因 3 ❌：listener 启动脚本不注入凭证 → 新进程闪退 → 系统一直跑老代码
**症状**：每次改完代码 `pkill + nohup bash run_listener_mac.sh` 起新 listener 但卡片回调仍走旧逻辑
**真因**：`run_listener_mac.sh` 之前没读 `~/.nsksd-content/config.json`，nohup 起子进程不继承当前 shell 的 export → 新进程缺 `LARK_APP_ID/SECRET` → 闪退 → 系统里只有你手动 export 后起的那个跑老代码的进程
**修法**：启动脚本自动从 `config.json` 解析并 export 凭证
**代码位置**：`scripts/interactive/run_listener_mac.sh`

### 根因 4 ❌：button.value 嵌整个 body.elements → 超 2KB 飞书拒发
**症状**：button 构造时 value 太大，推卡失败或事件回传超限
**真因**：飞书 button.value 硬限 ~2KB
**修法**：button.value 只塞骨架（`{title, subtitle, step_output_md}`，309 字节级），锁定态重建
**代码位置**：`card_builder.py::build_guided_feedback_card` 第 234-248 行

### 根因 5 ❌：`flex_mode: "stretch"` 手机端按钮堆叠成上下
**症状**：桌面端左右布局，手机端自动堆叠
**真因**：`stretch` 模式在窄屏会 fallback 成 vertical
**修法**：改 `flex_mode: "bisect"`（二等分，所有端保持左右）
**代码位置**：`card_builder.py::build_guided_feedback_card` 第 282 行

---

## 3. 硬规则（Must / Must-Not）

### Must
- ✅ 所有 button 用 `type: "primary"` 或 `"default"`，**禁用 `danger`**
- ✅ 锁定卡 disabled button 统一 `type: "default"`
- ✅ `max_length: 1000`（飞书 input 官方硬限，5000 会被服务端拒）
- ✅ `flex_mode: "bisect"`，不要 `stretch`
- ✅ listener 启动脚本必须注入 `LARK_APP_ID/SECRET` 环境变量
- ✅ feedback 文件路径固定：`triggers/guided/{session_id}-{step_name}.feedback`
- ✅ button.value 只塞骨架，禁止塞完整 body.elements

### Must-Not
- ❌ 不要用 `type: "danger"` 的 form submit button（事件会丢）
- ❌ 不要 `disabled: true + type: "danger/primary"` 组合（返回锁定卡会被拒 Code-356）
- ❌ 不要推群 chat_id（除非明确产品需求），私聊 `open_id` 体验最稳
- ❌ 不要用 `nohup bash run_listener_mac.sh` 直接启动（子进程继承问题），用 `run_listener_mac.sh restart`

---

## 4. 诊断命令（遇到问题先跑这些）

```bash
# 1. listener 进程状态
ps aux | grep -v grep | grep lark_ws_listener.py

# 2. listener 日志（看事件是否到达）
tail -50 /tmp/nsksd-listener.out | grep -E "(button value|form_value|guided trigger)"

# 3. feedback 文件是否落地
ls -lt ~/.claude/skills/nsksd-content/scripts/interactive/triggers/guided/

# 4. 读最新 feedback 内容
cat ~/.claude/skills/nsksd-content/scripts/interactive/triggers/guided/*.feedback

# 5. 重启 listener（正确姿势）
bash ~/.claude/skills/nsksd-content/scripts/interactive/run_listener_mac.sh restart

# 6. 验证卡片 JSON 结构
cd ~/.claude/skills/nsksd-content/scripts/interactive
python3 card_builder.py guided | python3 -m json.tool | head -60
```

---

## 5. 回流到 Claude Code session（Phase 2 · 待实现）

当前 V9.6 已打通「推卡 → 点击 → feedback 落盘」，下一步 Phase 2：

- `nsksd_publish.py` 启动时生成 `claude_session_id = uuid4()`，写 session 状态
- 推卡时 `button.value` 带 `claude_session_id`
- listener 收到 reject/approve 后：
  ```python
  subprocess.Popen([
      "claude", "--resume", claude_session_id,
      "--print",
      f"曲率修改意见：{feedback_text}\n请重做当前步（{step_name}）并产出新版本。"
  ], cwd=FIXED_CWD)
  ```
- 同一 session_id 用 `flock` 串行化，避免并发覆盖

---

## 6. E2E 验证剧本

```bash
# 场景 A：空输入 reject（已验证 ✅ 2026-04-21 21:04）
# 场景 B：填 "123" reject（已验证 ✅ 2026-04-21 21:10）
# 场景 C：填长文本 approve（TODO）
# 场景 D：输入 1000 字极限 reject（TODO，验证 max_length 边界）
```

验证命令：
```bash
# 推一张测试卡
python3 /tmp/push_guided_card.py

# 客户点按钮后，读 feedback 验证回传
cat ~/.claude/skills/nsksd-content/scripts/interactive/triggers/guided/*.feedback
```

预期 feedback JSON：
```json
{
  "session_id": "<session_id>",
  "step_name": "<step_name>",
  "step_index": 1,
  "action": "approve|reject",
  "feedback_text": "<用户输入或空串>",
  "created_at": "<ISO8601>",
  "status": "pending"
}
```
