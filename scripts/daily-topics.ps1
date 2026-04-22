# ============================================================
# 日生研NSKSD · Windows 每日 10:00 定时任务入口（V9.8 新增）
#
# 对标 macOS 的 run_nsksd_daily.sh：
#   Step 1  调 claude -p 生成 10 选题
#   Step 2  构造多选卡
#   Step 3  确保 listener 在跑 + 推卡
#   Step 4  确保 trigger-watcher 在跑
#
# 由 Task Scheduler 触发：
#   schtasks /Create /TN NSKSD-Daily-Topics /SC DAILY /ST 10:00 ^
#     /TR "powershell -NoProfile -ExecutionPolicy Bypass -File <path>\daily-topics.ps1"
#
# 手动测试：
#   powershell -File daily-topics.ps1              # 完整流程
#   powershell -File daily-topics.ps1 -CardOnly    # 跳过生成选题
#   powershell -File daily-topics.ps1 -DaemonsOnly # 只启动守护进程
# ============================================================
[CmdletBinding()]
param(
    [switch]$CardOnly,
    [switch]$DaemonsOnly
)

$ErrorActionPreference = 'Stop'

# 强制 UTF-8 输入输出，防中文乱码（问题 #11 根因）
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$SKILL_DIR = Split-Path -Parent $SCRIPT_DIR
$INTERACTIVE_DIR = Join-Path $SCRIPT_DIR 'interactive'
$LOG_DIR = Join-Path $SKILL_DIR 'logs'
$TODAY = Get-Date -Format 'yyyy-MM-dd'
$SESSION_ID = "daily-$TODAY"
$LOG_FILE = Join-Path $LOG_DIR "daily-$TODAY.log"

$TMP = $env:TEMP
$TOPICS_MD = Join-Path $TMP "nsksd-topics-$TODAY.md"
$TOPICS_JSON = Join-Path $TMP "nsksd-topics-$TODAY.json"
$CARD_JSON = Join-Path $TMP "nsksd-card-$TODAY.json"

New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

function Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $LOG_FILE -Value $line -Encoding UTF8
}

function Die($msg) {
    Log "FATAL: $msg"
    exit 1
}

# ---- 凭证注入（优先 ~/.nsksd-content/config.json，fallback scripts/.env） ----
function Load-Credentials {
    $configPath = Join-Path $env:USERPROFILE '.nsksd-content\config.json'
    if (Test-Path $configPath) {
        try {
            $cfg = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($cfg.lark.app_id -and $cfg.lark.app_id -ne 'REPLACE_ME') {
                $env:LARK_APP_ID = $cfg.lark.app_id
                $env:LARK_APP_SECRET = $cfg.lark.app_secret
                $env:TARGET_OPEN_ID = $cfg.lark.target_open_id
                if ($cfg.lark.customer_open_chat_id -and $cfg.lark.customer_open_chat_id -ne 'REPLACE_ME') {
                    $env:TARGET_CHAT_ID = $cfg.lark.customer_open_chat_id
                }
                Log "  ✅ 从 $configPath 加载飞书凭证"
                return
            }
        } catch {
            Log "  ⚠️  config.json 解析失败：$_"
        }
    }

    # fallback：scripts/.env
    $envPath = Join-Path $SCRIPT_DIR '.env'
    if (Test-Path $envPath) {
        Get-Content $envPath -Encoding UTF8 | ForEach-Object {
            if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.+?)\s*$') {
                $k = $matches[1]
                $v = $matches[2].Trim('"').Trim("'")
                if ($k -in @('LARK_APP_ID','LARK_APP_SECRET','TARGET_OPEN_ID','TARGET_CHAT_ID','FEISHU_APP_ID','FEISHU_APP_SECRET')) {
                    # 兼容 FEISHU_ 前缀
                    if ($k -eq 'FEISHU_APP_ID') { $k = 'LARK_APP_ID' }
                    if ($k -eq 'FEISHU_APP_SECRET') { $k = 'LARK_APP_SECRET' }
                    Set-Item -Path "Env:$k" -Value $v
                }
            }
        }
        Log "  ✅ 从 $envPath 加载凭证"
    }

    if (-not $env:LARK_APP_ID)     { Die 'LARK_APP_ID 未设置（请跑 python scripts/setup_cli.py 配置）' }
    if (-not $env:LARK_APP_SECRET) { Die 'LARK_APP_SECRET 未设置' }
    if (-not $env:TARGET_OPEN_ID)  { Die 'TARGET_OPEN_ID 未设置' }
}

# ---- Step 1: 生成选题 ----
function Generate-Topics {
    Log 'Step 1: 调 claude -p 生成 10 选题...'

    $claudeBin = Get-Command claude -ErrorAction SilentlyContinue
    if (-not $claudeBin) { Die 'claude CLI 未找到（请安装 Claude Code）' }

    # 用 heredoc 风格构造 prompt，写到临时文件再喂给 claude
    $promptPath = Join-Path $TMP "nsksd-prompt-$TODAY.txt"
    $prompt = @"
请阅读 $SKILL_DIR/SKILL.md 了解 V9.7 工作流。
【必读三件套】
- $SKILL_DIR/references/topic-selection-rules.md（八维坐标系 + 三层去重 + 反面示例）
- $SKILL_DIR/references/title-playbook.md（45 标题公式 + 张力 6 维 + 三库禁用词 + 医广红线）
- $SKILL_DIR/references/topic-library/README.md（分块资讯池 + 8 招商角度硬约束）

执行【Step 1 · 选题生成】:
1. 读当日热点 $SKILL_DIR/references/topic-library/hotspots/$TODAY.json（无则跳过）
2. 查 $SKILL_DIR/logs/topic-history.jsonl 做 30 天三维指纹去重（文件不存在就当空集合）
3. 生成 >= 10 个选题（S/A/B 分层），至少 3 个结合当日热点

【V9.7 硬约束】M7 ≤1/日；M6+M7 ≤2/日；C 端 ≥6/10；主人群（门店/美容院/养生馆/分销商）≤1/日
【V9.7 张力】每条标题至少命中 3 项（对比反差/具体数字/悬念好奇/冲突争议/时间承诺/结果承诺）
【禁用】医广红线（治疗/根治/当天见效）+ 曲率 AI 味词（赋能/链路/飞轮/颠覆）+ 破折号 + 「不是…而是…」句式
【严禁】捏造数据 / 捏造 URL / 日本表述

【输出格式】文末用 ``````json 代码块输出 JSON 数组，字段:
  - value: 选题编号 (topic_1, topic_2, ...)
  - text:  完整 Markdown 文本（例 "🏆 选题1 · 标题（M4/F21，90分）"）
至少 10 个 options。
"@
    [System.IO.File]::WriteAllText($promptPath, $prompt, [System.Text.Encoding]::UTF8)

    $null = & claude -p "(Get-Content '$promptPath' -Raw -Encoding UTF8)" 2>>$LOG_FILE | Out-File -Encoding UTF8 -FilePath $TOPICS_MD
    if (-not (Test-Path $TOPICS_MD) -or (Get-Item $TOPICS_MD).Length -eq 0) {
        Die '选题生成失败（TOPICS_MD 为空）'
    }

    # 提取 JSON
    $py = @"
import re, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
content = open(r'$TOPICS_MD', encoding='utf-8').read()
m = re.search(r'``````json\s*\n(.*?)\n``````', content, re.DOTALL)
if not m:
    print('ERROR: 无法从选题文件提取 json 代码块', file=sys.stderr); sys.exit(1)
data = json.loads(m.group(1))
if len(data) < 10:
    print(f'ERROR: options 数量 {len(data)} < 10', file=sys.stderr); sys.exit(1)
json.dump(data, open(r'$TOPICS_JSON', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'✅ 已提取 {len(data)} 个选题')
"@
    $pyPath = Join-Path $TMP "nsksd-extract-$TODAY.py"
    [System.IO.File]::WriteAllText($pyPath, $py, [System.Text.Encoding]::UTF8)
    python $pyPath
    if ($LASTEXITCODE -ne 0) { Die '选题 JSON 解析失败' }

    Log "  ✅ 选题文件: $TOPICS_JSON"
}

# ---- Step 2: 构造卡片 ----
function Build-Card {
    Log 'Step 2: 构造 v4 多选卡...'

    $py = @"
import json, sys, io
sys.path.insert(0, r'$INTERACTIVE_DIR')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from card_builder import multi_choice_card
options = json.load(open(r'$TOPICS_JSON', encoding='utf-8'))
card = multi_choice_card(
    session_id='$SESSION_ID',
    step='topic_select',
    title='日生研NSKSD · 每日选题多选 ($TODAY)',
    intro_md=f'💡 **今日 {len(options)} 条选题**\n\n按 V9.7 八维坐标系生成 · 勾选你想创作的，点底部按钮一次提交',
    options=options,
)
json.dump(card, open(r'$CARD_JSON', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'✅ 卡片构造完成: {len(options)} 选项')
"@
    $pyPath = Join-Path $TMP "nsksd-build-card-$TODAY.py"
    [System.IO.File]::WriteAllText($pyPath, $py, [System.Text.Encoding]::UTF8)
    python $pyPath
    if ($LASTEXITCODE -ne 0) { Die '卡片构造失败' }
}

# ---- Step 3: listener + 推卡 ----
function Ensure-Listener {
    $listenerScript = Join-Path $INTERACTIVE_DIR 'run_listener_win.bat'
    if (-not (Test-Path $listenerScript)) {
        Log "  ⚠️  $listenerScript 不存在，跳过启动"
        return
    }
    # 调用 run_listener_win.bat start（自动幂等）
    Push-Location $INTERACTIVE_DIR
    & cmd /c "$listenerScript start" | Out-Null
    Pop-Location
    Log '  ✅ listener 已确保运行'
}

function Send-Card {
    Log 'Step 3: 推送多选卡到飞书...'
    Ensure-Listener

    # 用 Python 脚本统一发卡（PowerShell Invoke-RestMethod 中文编码坑多，交给 send_notify 后继用 Python）
    $py = @"
import json, os, sys, io, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

APP_ID = os.environ['LARK_APP_ID']
APP_SECRET = os.environ['LARK_APP_SECRET']
TARGET_OPEN_ID = os.environ['TARGET_OPEN_ID']

req = urllib.request.Request(
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    data=json.dumps({'app_id': APP_ID, 'app_secret': APP_SECRET}).encode('utf-8'),
    headers={'Content-Type': 'application/json; charset=utf-8'},
    method='POST',
)
with urllib.request.urlopen(req, timeout=10) as r:
    token = json.loads(r.read())['tenant_access_token']

card = json.load(open(r'$CARD_JSON', encoding='utf-8'))
payload = {
    'receive_id': TARGET_OPEN_ID,
    'msg_type': 'interactive',
    'content': json.dumps(card, ensure_ascii=False),
}
req = urllib.request.Request(
    'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id',
    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
    headers={
        'Content-Type': 'application/json; charset=utf-8',
        'Authorization': f'Bearer {token}',
    },
    method='POST',
)
with urllib.request.urlopen(req, timeout=10) as r:
    resp = json.loads(r.read())
    if resp.get('code') != 0:
        print(f'推卡失败: {resp}', file=sys.stderr); sys.exit(1)
    print(f"✅ 卡片已推送 (message_id: {resp['data']['message_id']})")
"@
    $pyPath = Join-Path $TMP "nsksd-sendcard-$TODAY.py"
    [System.IO.File]::WriteAllText($pyPath, $py, [System.Text.Encoding]::UTF8)
    python $pyPath
    if ($LASTEXITCODE -ne 0) { Die '推卡失败（查看上面错误）' }
}

# ---- Step 4: trigger-watcher（Windows 暂用轮询版 Python 守护） ----
function Ensure-Watcher {
    Log 'Step 4: trigger-watcher 守护（Windows 版暂用 Python 轮询）...'
    $watcherPy = Join-Path $INTERACTIVE_DIR 'trigger_watcher.sh'
    if (-not (Test-Path $watcherPy)) {
        Log '  ⏭️  trigger_watcher 不存在，等用户勾选后需手动触发流水线'
        return
    }
    # Git Bash 可用时复用 .sh；否则提示用户
    $bash = Get-Command bash -ErrorAction SilentlyContinue
    if ($bash) {
        Log '  ✅ 检测到 bash，trigger_watcher 可通过 `bash scripts/interactive/trigger_watcher.sh &` 启动'
    } else {
        Log '  ⚠️  未检测到 bash，勾选后需手动跑 claude -p 流水线（见 docs/playbooks/windows-troubleshooting.md）'
    }
}

# ---- 主流程 ----
Log '============================================'
Log "日生研NSKSD · 每日选题推送（Windows）· $TODAY"
Log '============================================'

Load-Credentials

if ($DaemonsOnly) {
    Ensure-Listener
    Ensure-Watcher
    Log '✅ 守护进程已启动'
    exit 0
}

if (-not $CardOnly) { Generate-Topics }
Build-Card
Send-Card
Ensure-Watcher

Log '============================================'
Log '✅ 完成 · 等待用户在飞书勾选选题'
Log "  listener log: $INTERACTIVE_DIR\listener.out"
Log "  daily log:    $LOG_FILE"
Log '============================================'
