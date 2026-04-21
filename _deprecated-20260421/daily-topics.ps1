# ============================================================
# 日生研NSKSD · 每日选题自动化脚本（Windows）
#
# 功能：
# 1. 调用Claude CLI生成选题
# 2. 发送V2多选卡片到飞书
# 3. 启动回调服务器等待提交
#
# 用法：
#   .\daily-topics.ps1              # 完整流程
#   .\daily-topics.ps1 -Mode server # 只启动回调服务器
#   .\daily-topics.ps1 -Mode card   # 只发送卡片
# ============================================================

param(
    [ValidateSet("full", "server", "card", "generate", "stop")]
    [string]$Mode = "full"
)

$ErrorActionPreference = "Stop"

# ---- 配置 ----
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillDir = Split-Path -Parent $ScriptDir
$TopicsOutput = "$env:TEMP\nsksd-topics-result.md"
$LogDir = "$SkillDir\logs"
$Today = Get-Date -Format "yyyy-MM-dd"

# 加载 .env 文件
$EnvFile = "$ScriptDir\.env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.+)$') {
            [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process")
        }
    }
}

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

function Write-Log($msg) {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg"
}

# ---- 启动服务器 ----
function Start-CallbackServer {
    $existingJob = Get-Job -Name "nsksd-server" -ErrorAction SilentlyContinue
    if ($existingJob -and $existingJob.State -eq "Running") {
        Write-Log "回调服务器已在运行"
        return
    }

    Write-Log "启动回调服务器..."
    $job = Start-Job -Name "nsksd-server" -ScriptBlock {
        param($dir)
        Set-Location "$dir\server"
        bun run index.ts
    } -ArgumentList $ScriptDir

    Start-Sleep -Seconds 2
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:9800/health" -Method Get -ErrorAction Stop
        Write-Log "服务器健康检查通过"
    } catch {
        Write-Log "服务器可能还在启动中..."
    }
}

function Stop-CallbackServer {
    $job = Get-Job -Name "nsksd-server" -ErrorAction SilentlyContinue
    if ($job) {
        Stop-Job -Job $job
        Remove-Job -Job $job
        Write-Log "回调服务器已停止"
    }
}

# ---- 生成选题 ----
function New-Topics {
    Write-Log "正在生成选题..."

    $prompt = @"
请阅读 $SkillDir/SKILL.md 了解工作流。
然后阅读以下参考文件：
- $SkillDir/references/knowledge-base.md
- $SkillDir/references/topic-library.md
- $SkillDir/references/compliance.md

现在执行"阶段一：情报收集+选题生成"，生成10个选题。
按S/A/B分级，每个选题包含：标题、内容线、目标人群、合规分级、五维评分、3个标题选项、写作大纲。
"@

    claude -p $prompt > $TopicsOutput 2>"$LogDir\claude-topics-$Today.log"

    if ($LASTEXITCODE -eq 0 -and (Test-Path $TopicsOutput)) {
        Write-Log "选题生成完成: $TopicsOutput"
    } else {
        Write-Log "选题生成失败"
        exit 1
    }
}

# ---- 发送卡片 ----
function Send-TopicCard {
    Write-Log "发送选题卡片到飞书..."
    Set-Location $ScriptDir
    bun run send-topic-card.ts $TopicsOutput 2>&1 | Tee-Object -FilePath "$LogDir\card-$Today.log"
}

# ---- 主流程 ----
switch ($Mode) {
    "server" {
        Start-CallbackServer
        Write-Log "服务器运行中，按 Ctrl+C 停止"
        while ($true) { Start-Sleep -Seconds 60 }
    }
    "stop" {
        Stop-CallbackServer
    }
    "card" {
        Start-CallbackServer
        Send-TopicCard
    }
    "generate" {
        New-Topics
    }
    "full" {
        Write-Log "日生研NSKSD · 每日选题自动化"
        Write-Log "================================"
        Start-CallbackServer
        New-Topics
        Send-TopicCard
        Write-Log "================================"
        Write-Log "全部完成！等待飞书卡片提交..."
    }
}
