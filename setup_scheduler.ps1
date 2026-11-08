# setup_scheduler.ps1 - Configure le Task Scheduler pour le bot et la promotion
# A executer en tant qu'administrateur

$projectDir = "D:\Cahine youtube economique"
$pythonExe = "$projectDir\.venv\Scripts\python.exe"

# 1. Bot principal - 6h00 tous les jours
$action1 = New-ScheduledTaskAction -Execute $pythonExe -Argument "bot.py" -WorkingDirectory $projectDir
$trigger1 = New-ScheduledTaskTrigger -Daily -At "06:00"
$settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "PlyChanBot_Daily" -Action $action1 -Trigger $trigger1 -Settings $settings1 -Force
Write-Host "Task 'PlyChanBot_Daily' cree (6h00 tous les jours)"

# 2. Promotion - 9h00, 13h00, 18h00
$action2 = New-ScheduledTaskAction -Execute $pythonExe -Argument "pipeline/promotion_agent.py" -WorkingDirectory $projectDir
$trigger2a = New-ScheduledTaskTrigger -Daily -At "09:00"
$trigger2b = New-ScheduledTaskTrigger -Daily -At "13:00"
$trigger2c = New-ScheduledTaskTrigger -Daily -At "18:00"
$settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "PlyChanPromo" -Action $action2 -Trigger $trigger2a,$trigger2b,$trigger2c -Settings $settings2 -Force
Write-Host "Task 'PlyChanPromo' cree (9h, 13h, 18h tous les jours)"

# 3. Sync uploads - 12h00 (pour uploader les videos manquees)
$action3 = New-ScheduledTaskAction -Execute $pythonExe -Argument "sync_uploads.py" -WorkingDirectory $projectDir
$trigger3 = New-ScheduledTaskTrigger -Daily -At "12:00"
$settings3 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "PlyChanSync" -Action $action3 -Trigger $trigger3 -Settings $settings3 -Force
Write-Host "Task 'PlyChanSync' cree (12h00 tous les jours)"

Write-Host ""
Write-Host "=== CONFIGURATION TERMINEE ==="
Write-Host "3 taches planifiees :"
Write-Host "  - PlyChanBot_Daily : 6h00 (pipeline complet)"
Write-Host "  - PlyChanPromo : 9h, 13h, 18h (promotion)"
Write-Host "  - PlyChanSync : 12h00 (upload manquants)"
Write-Host ""
Write-Host "Pour verifier: Get-ScheduledTask | Where-Object { \$_.TaskName -like 'PlyChan*' }"
PYEOF