# ============================================================
# 日生研NSKSD · Windows 首次安装配置脚本 (V9.0)
#
# 用法：cd nsksd-content-skill; pwsh scripts/setup.ps1
# 效果：检查依赖 + 创建配置 + 装 bun 依赖 + 自动注册每日 10:00 定时任务
# ============================================================

$ErrorActionPreference = 'Stop'

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$SKILL_DIR = Split-Path -Parent $SCRIPT_DIR

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  日生研NSKSD · 内容创作Skill 安装配置 (Win)" -ForegroundColor Cyan
Write-Host "============================================"
Write-Host ""

# ---- Step 1: 依赖检查 ----
Write-Host "📋 Step 1: 检查依赖..."
function Check-Cmd($name) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { Write-Host "  ✅ $name $($cmd.Source)" } else { Write-Host "  ❌ $name 未找到" -ForegroundColor Yellow }
}
Check-Cmd "claude"
Check-Cmd "python"

# V9.1：bun 不存在则自动安装
if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
    Write-Host "  🔧 未检测到 bun，自动安装中..." -ForegroundColor Yellow
    try {
        powershell -NoProfile -Command "irm bun.sh/install.ps1 | iex" | Out-Null
        $env:Path = "$env:USERPROFILE\.bun\bin;$env:Path"
        if (Get-Command bun -ErrorAction SilentlyContinue) {
            Write-Host "  ✅ bun 自动安装完成：$(bun --version)"
        } else {
            Write-Host "  ❌ bun 自动安装失败，请手动执行：irm bun.sh/install.ps1 | iex" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ❌ bun 自动安装异常：$_" -ForegroundColor Red
    }
} else {
    Write-Host "  ✅ bun $((Get-Command bun).Source)"
}

# V9.1：lark CLI 不存在则自动安装
if (-not (Get-Command lark -ErrorAction SilentlyContinue)) {
    Write-Host "  🔧 未检测到 lark CLI，自动安装中..." -ForegroundColor Yellow
    if (Get-Command bun -ErrorAction SilentlyContinue) {
        bun install -g '@larksuiteoapi/lark-cli' 2>&1 | Out-Null
    }
    if (-not (Get-Command lark -ErrorAction SilentlyContinue) -and (Get-Command npm -ErrorAction SilentlyContinue)) {
        npm install -g '@larksuiteoapi/lark-cli' 2>&1 | Out-Null
    }
    if (Get-Command lark -ErrorAction SilentlyContinue) {
        Write-Host "  ✅ lark CLI 自动安装完成"
    } else {
        Write-Host "  ⚠️  lark CLI 自动安装失败，飞书推送将退化为纯 HTTP 模式"
    }
} else {
    Write-Host "  ✅ lark $((Get-Command lark).Source)"
}

# ---- Step 2: 配置文件 ----
Write-Host ""
Write-Host "📋 Step 2: 创建配置文件..."

$ENV_FILE = Join-Path $SCRIPT_DIR "server\.env"
$ENV_EXAMPLE = Join-Path $SCRIPT_DIR "server\.env.example"
if (Test-Path $ENV_FILE) {
    Write-Host "  ⏭️  $ENV_FILE 已存在，跳过"
} elseif (Test-Path $ENV_EXAMPLE) {
    Copy-Item $ENV_EXAMPLE $ENV_FILE
    (Get-Content $ENV_FILE) -replace '^SKILL_PATH=.*', "SKILL_PATH=$SKILL_DIR" | Set-Content $ENV_FILE
    Write-Host "  ✅ 已创建 $ENV_FILE"
    Write-Host "  ⚠️  请编辑此文件填入飞书/微信凭据" -ForegroundColor Yellow
}

$CONFIG_FILE = Join-Path $SKILL_DIR "config.json"
$CONFIG_EXAMPLE = Join-Path $SKILL_DIR "config.json.example"
if (-not (Test-Path $CONFIG_FILE) -and (Test-Path $CONFIG_EXAMPLE)) {
    Copy-Item $CONFIG_EXAMPLE $CONFIG_FILE
    Write-Host "  ✅ 已创建 $CONFIG_FILE"
}

# ---- Step 3: 安装 bun 依赖 ----
Write-Host ""
Write-Host "📋 Step 3: 安装服务端依赖..."
if (Get-Command bun -ErrorAction SilentlyContinue) {
    Push-Location (Join-Path $SCRIPT_DIR "server")
    bun install 2>&1 | Out-Null
    Write-Host "  ✅ bun install 完成"
    Pop-Location
} else {
    Write-Host "  ⏭️  bun 未安装，跳过"
}

# ---- Step 3.6: 飞书 CLI 自动授权 (V9.1) ----
Write-Host ""
Write-Host "📋 Step 3.6: 飞书 CLI 自动授权..."

if (Get-Command lark -ErrorAction SilentlyContinue) {
    if (Test-Path $ENV_FILE) {
        $envContent = Get-Content $ENV_FILE
        $appId = ($envContent | Where-Object { $_ -match '^FEISHU_APP_ID=' }) -replace '^FEISHU_APP_ID=', '' -replace '[''"]', ''
        $appSecret = ($envContent | Where-Object { $_ -match '^FEISHU_APP_SECRET=' }) -replace '^FEISHU_APP_SECRET=', '' -replace '[''"]', ''
        if ($appId -and $appSecret -and $appId -ne 'your_app_id_here') {
            try {
                lark config set app_id $appId 2>&1 | Out-Null
                lark config set app_secret $appSecret 2>&1 | Out-Null
                Write-Host "  ✅ 飞书 CLI 已用 .env 凭据自动授权"
            } catch {
                Write-Host "  ⚠️  lark config set 失败，可手动运行：lark login --app-id XXX --app-secret YYY"
            }
        } else {
            Write-Host "  ⏭️  .env 尚未填写 FEISHU_APP_ID / FEISHU_APP_SECRET，跳过"
        }
    }
} else {
    Write-Host "  ⏭️  lark CLI 未安装，跳过"
}

# ---- Step 3.5: 自动注册每日 10:00 定时任务 (V9.0) ----
Write-Host ""
Write-Host "📋 Step 3.5: 注册 Windows 每日 10:00 定时任务..."

$TASK_NAME = "NSKSD-Daily-Topics"
$SCRIPT_ENTRY = Join-Path $SCRIPT_DIR "daily-topics.ps1"

if (-not (Test-Path $SCRIPT_ENTRY)) {
    Write-Host "  ❌ 找不到入口脚本：$SCRIPT_ENTRY" -ForegroundColor Red
} else {
    # 删除已有任务（幂等）
    schtasks /Delete /TN $TASK_NAME /F 2>$null | Out-Null

    $action = "-NoProfile -ExecutionPolicy Bypass -File `"$SCRIPT_ENTRY`""
    schtasks /Create `
        /SC DAILY `
        /ST 10:00 `
        /TN $TASK_NAME `
        /TR "powershell.exe $action" `
        /F | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ 定时任务已注册：每日 10:00 触发 $TASK_NAME"
    } else {
        Write-Host "  ❌ schtasks 注册失败（exit $LASTEXITCODE）" -ForegroundColor Red
    }
}

# ---- Step 4: 验证 ----
Write-Host ""
Write-Host "📋 Step 4: 快速验证..."
$mustFiles = @(
    "SKILL.md",
    "scripts\server\index.ts",
    "scripts\run_nsksd_daily.sh",
    "scripts\daily-topics.ps1",
    "config\routing-table.yaml"
)
foreach ($f in $mustFiles) {
    $p = Join-Path $SKILL_DIR $f
    if (Test-Path $p) { Write-Host "  ✅ $f" } else { Write-Host "  ❌ $f 缺失" -ForegroundColor Red }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  ✅ 基础配置完成！"
Write-Host ""
Write-Host "  下一步："
Write-Host "  1. 编辑 scripts\server\.env 填入凭据"
Write-Host "  2. 编辑 config.json 填入微信公众号信息"
Write-Host "  3. 授权直达（V9.0 直链）："
Write-Host "     飞书：https://open.feishu.cn/page/launcher?from=backend_oneclick"
Write-Host "     微信：https://developers.weixin.qq.com/console/product/mp/"
Write-Host "  4. 每日 10:00 定时任务已自动注册，无需手动配置"
Write-Host "============================================"
