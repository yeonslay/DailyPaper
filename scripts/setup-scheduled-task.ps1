# DailyPaper 자동 실행 - Windows 작업 스케줄러 등록
# 화~토 매일 09:30에 run-yesterday (절전모드에서 깨워서)
# 관리자 권한 없이 실행 가능

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BatPath = Join-Path $ProjectRoot "scripts\run-yesterday.bat"
$TaskName = "DailyPaper-run-yesterday"
$Trigger = New-ScheduledTaskTrigger -Daily -At "09:30"
$Action = New-ScheduledTaskAction -Execute $BatPath -WorkingDirectory $ProjectRoot
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -WakeToRun

# 기존 작업이 있으면 제거 후 재등록
Unregister-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Trigger $Trigger -Action $Action -Settings $Settings

Write-Host "OK: $TaskName"
Write-Host "Runs daily at 09:30 Tue-Sat (wakes from sleep)"
Write-Host "Check: taskschd.msc"
