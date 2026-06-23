# Hermass Scheduled Task Plan

Run these after the wrapper scripts and data update methods pass acceptance.

Wrapper scripts implement working directory setup, logs, lock files, and real process exit codes.

Default registration only creates H1 and M15 update tasks:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\qoder\csvcl - AVA\MT5_AI_Trading\scripts\register_hermass_tasks.ps1"
```

## H1 hourly
```powershell
schtasks.exe /Create /TN Hermass_Update_H1 /SC HOURLY /MO 1 /ST 00:02 /F /TR "\"D:\qoder\csvcl - AVA\MT5_AI_Trading\scripts\hermass_update_h1.cmd\""
```

## M15 every 15 minutes
```powershell
schtasks.exe /Create /TN Hermass_Update_M15 /SC MINUTE /MO 15 /ST 00:07 /F /TR "\"D:\qoder\csvcl - AVA\MT5_AI_Trading\scripts\hermass_update_m15.cmd\""
```

H1 starts at minute 02 and M15 starts at minute 07 to reduce task overlap.

## D1 full rebuild

Do not register a live daily D1 rebuild by default. D1 rebuild rewrites `data/hermass_state.db`.
If a disabled on-demand D1 task is needed, register it explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\qoder\csvcl - AVA\MT5_AI_Trading\scripts\register_hermass_tasks.ps1" -IncludeD1Rebuild
```

The explicit D1 task target is:

```powershell
schtasks.exe /Create /TN Hermass_Rebuild_D1 /SC DAILY /ST 06:15 /F /TR "\"D:\qoder\csvcl - AVA\MT5_AI_Trading\scripts\hermass_rebuild_d1.cmd\""
schtasks.exe /Change /TN Hermass_Rebuild_D1 /DISABLE
```
