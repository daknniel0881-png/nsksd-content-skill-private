# ============================================================
# 日生研 NSKSD · Windows 交互式配置包装器（V9.8 新增）
#
# 作用：拉起 setup_cli.py 交互引导，保证 UTF-8 编码 + 权限 + 提示链接直达
# 用法：powershell -ExecutionPolicy Bypass -File scripts\setup_cli.ps1
#
# 修复测试报告：
#   - 问题 #4：取代"让用户手动编辑 config.json"的反 Agent 模式
#   - 问题 #10：顺便提示飞书 CLI 安装（setup.ps1 已装则跳过）
# ============================================================
$ErrorActionPreference = 'Stop'
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ''
Write-Host '============================================' -ForegroundColor Cyan
Write-Host '  日生研NSKSD · 凭证交互配置（Windows）'       -ForegroundColor Cyan
Write-Host '============================================'
Write-Host ''

# Python 存在性检查
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host '[错误] 未检测到 python，请先安装 Python 3.8+：https://www.python.org/downloads/' -ForegroundColor Red
    exit 1
}

# 直链提示（问题 #3 修正）
Write-Host '📎 参考直链' -ForegroundColor Yellow
Write-Host '   飞书开放平台：https://open.feishu.cn/page/launcher?from=backend_oneclick'
Write-Host '   微信公众平台：https://mp.weixin.qq.com/'
Write-Host '   open_id 反查：https://open.feishu.cn/api-explorer  →  batch_get_id'
Write-Host ''

# 拉起交互式 Python 引导
python (Join-Path $SCRIPT_DIR 'setup_cli.py')
$code = $LASTEXITCODE

if ($code -ne 0) {
    Write-Host ''
    Write-Host "[失败] setup_cli.py 退出码 $code" -ForegroundColor Red
    exit $code
}

Write-Host ''
Write-Host '============================================' -ForegroundColor Green
Write-Host '  ✅ 凭证配置完成'                             -ForegroundColor Green
Write-Host ''
Write-Host '  下一步：'
Write-Host '  1. 启动飞书监听器：scripts\interactive\run_listener_win.bat start'
Write-Host '  2. 手动触发每日选题：powershell -File scripts\daily-topics.ps1'
Write-Host '  3. 注册定时任务（如未注册）：powershell -File scripts\setup.ps1'
Write-Host '============================================'
