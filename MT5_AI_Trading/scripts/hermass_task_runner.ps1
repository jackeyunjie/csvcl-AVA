param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("update-h1", "update-m15", "rebuild-d1", "check")]
    [string]$Action,

    [string[]]$Symbols = @("EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US_30", "US_500", "US_TECH100"),
    [int]$Days = 0,
    [string]$Python = "C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312\python.exe",
    [string]$Vault = "D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE",
    [switch]$NoContraction,
    [switch]$ConfirmFullRebuild
)

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectDir "logs\tasks"
$LockDir = Join-Path $ProjectDir "locks"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path $LockDir | Out-Null

$LockPath = Join-Path $LockDir "$Action.lock"
$LogPath = Join-Path $LogDir ("{0}_{1}.log" -f $Action, (Get-Date -Format "yyyyMMdd_HHmmss"))

if (Test-Path -LiteralPath $LockPath) {
    $existing = Get-Item -LiteralPath $LockPath
    $lockText = Get-Content -LiteralPath $LockPath -Raw -ErrorAction SilentlyContinue
    $existingPid = $null
    if ($lockText -match 'pid=(\d+)') {
        $existingPid = [int]$Matches[1]
    }
    $isRunning = $false
    if ($existingPid) {
        $isRunning = [bool](Get-Process -Id $existingPid -ErrorAction SilentlyContinue)
    }
    if ($isRunning) {
        "[$(Get-Date -Format s)] skipped because action is already running: $Action pid=$existingPid lock=$LockPath" | Tee-Object -FilePath $LogPath
        exit 0
    }
    if ($existing.LastWriteTime -gt (Get-Date).AddHours(-3)) {
        "[$(Get-Date -Format s)] removing stale lock without running process: $LockPath" | Tee-Object -FilePath $LogPath
    }
    Remove-Item -LiteralPath $LockPath -Force
}

try {
    Set-Content -LiteralPath $LockPath -Value ("pid={0}; started={1}" -f $PID, (Get-Date -Format s)) -Encoding UTF8
    Set-Location -LiteralPath $ProjectDir

    $ArgsList = @("hermass_state_ops.py", $Action, "--symbols") + $Symbols + @("--report", "--obsidian-vault", $Vault)
    if ($Action -eq "update-h1") {
        $ArgsList += @("--days", ($(if ($Days -gt 0) { $Days } else { 120 })))
    }
    if ($Action -eq "update-m15") {
        $ArgsList += @("--days", ($(if ($Days -gt 0) { $Days } else { 30 })))
    }
    if ($Action -eq "rebuild-d1" -and $ConfirmFullRebuild) {
        $ArgsList += "--confirm-full-rebuild"
    }
    if ($NoContraction) {
        $ArgsList += "--no-contraction"
    }

    "[$(Get-Date -Format s)] $Python $($ArgsList -join ' ')" | Tee-Object -FilePath $LogPath
    & $Python @ArgsList *>&1 | Tee-Object -FilePath $LogPath -Append
    exit $LASTEXITCODE
}
catch {
    "[$(Get-Date -Format s)] ERROR: $($_.Exception.Message)" | Tee-Object -FilePath $LogPath -Append
    exit 1
}
finally {
    Remove-Item -LiteralPath $LockPath -Force -ErrorAction SilentlyContinue
}
