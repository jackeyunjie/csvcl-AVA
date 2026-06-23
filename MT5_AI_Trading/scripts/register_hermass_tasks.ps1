param(
    [switch]$IncludeD1Rebuild
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$H1 = Join-Path $ScriptDir "hermass_update_h1.cmd"
$M15 = Join-Path $ScriptDir "hermass_update_m15.cmd"

foreach ($path in @($H1, $M15)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing wrapper script: $path"
    }
}
if ($IncludeD1Rebuild) {
    $D1 = Join-Path $ScriptDir "hermass_rebuild_d1.cmd"
    if (-not (Test-Path -LiteralPath $D1)) {
        throw "Missing wrapper script: $D1"
    }
}

$H1Action = 'cmd.exe /c ""{0}""' -f $H1
$M15Action = 'cmd.exe /c ""{0}""' -f $M15
if ($IncludeD1Rebuild) {
    $D1Action = 'cmd.exe /c ""{0}""' -f $D1
}

& schtasks.exe /Create /TN Hermass_Update_H1 /SC HOURLY /MO 1 /ST 00:02 /F /TR $H1Action
if ($LASTEXITCODE -ne 0) { throw "Failed to register Hermass_Update_H1" }

& schtasks.exe /Create /TN Hermass_Update_M15 /SC MINUTE /MO 15 /ST 00:07 /F /TR $M15Action
if ($LASTEXITCODE -ne 0) { throw "Failed to register Hermass_Update_M15" }

if ($IncludeD1Rebuild) {
    & schtasks.exe /Create /TN Hermass_Rebuild_D1 /SC DAILY /ST 06:15 /F /TR $D1Action
    if ($LASTEXITCODE -ne 0) { throw "Failed to register Hermass_Rebuild_D1" }
    & schtasks.exe /Change /TN Hermass_Rebuild_D1 /DISABLE
    if ($LASTEXITCODE -ne 0) { throw "Failed to disable Hermass_Rebuild_D1" }
}

& schtasks.exe /Query /TN Hermass_Update_H1 /V /FO LIST
& schtasks.exe /Query /TN Hermass_Update_M15 /V /FO LIST
if ($IncludeD1Rebuild) {
    & schtasks.exe /Query /TN Hermass_Rebuild_D1 /V /FO LIST
}
