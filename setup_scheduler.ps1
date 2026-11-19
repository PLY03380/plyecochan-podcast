# setup_scheduler.ps1 - Configure le Task Scheduler pour le bot et la promotion
# A executer en tant qu'administrateur

$projectDir = "D:\Cahine youtube economique"
$pythonExe = "$projectDir\.venv\Scripts\python.exe"

# 1. Bot Shorts - 6h00 tous les jours
$action1 = New-ScheduledTaskAction -Execute $pythonExe -Argument "bot.py --short-only" -WorkingDirectory $projectDir
$trigger1 = New-ScheduledTaskTrigger -Daily -At "06:00"
$settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "PlyChanBot_Shorts" -Action $action1 -Trigger $trigger1 -Settings $settings1 -Force
Write-Host "Task 'PlyChanBot_Shorts' cree (6h00 tous les jours)"

# 2. Bot Longues - 7h00 tous les jours (apres les Shorts)
$action2 = New-ScheduledTaskAction -Execute $pythonExe -Argument "bot.py --long-only" -WorkingDirectory $projectDir
$trigger2 = New-ScheduledTaskTrigger -Daily -At "07:00"
$settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "PlyChanBot_Longs" -Action $action2 -Trigger $trigger2 -Settings $settings2 -Force
Write-Host "Task 'PlyChanBot_Longs' cree (7h00 tous les jours)"

# 3. Promotion - 9h00, 13h00, 18h00
$action3 = New-ScheduledTaskAction -Execute $pythonExe -Argument "pipeline/promotion_agent.py" -WorkingDirectory $projectDir
$trigger3a = New-ScheduledTaskTrigger -Daily -At "09:00"
$trigger3b = New-ScheduledTaskTrigger -Daily -At "13:00"
$trigger3c = New-ScheduledTaskTrigger -Daily -At "18:00"
$settings3 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "PlyChanPromo" -Action $action3 -Trigger $trigger3a,$trigger3b,$trigger3c -Settings $settings3 -Force
Write-Host "Task 'PlyChanPromo' cree (9h, 13h, 18h tous les jours)"

# 4. Sync uploads - 12h00 (pour uploader les videos manquees)
$action4 = New-ScheduledTaskAction -Execute $pythonExe -Argument "sync_uploads.py" -WorkingDirectory $projectDir
$trigger4 = New-ScheduledTaskTrigger -Daily -At "12:00"
$settings4 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "PlyChanSync" -Action $action4 -Trigger $trigger4 -Settings $settings4 -Force
Write-Host "Task 'PlyChanSync' cree (12h00 tous les jours)"

# Supprimer l'ancienne tache PlyChanBot_Daily si elle existe
Unregister-ScheduledTask -TaskName "PlyChanBot_Daily" -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Ancienne tache 'PlyChanBot_Daily' supprimee (si existante)"

Write-Host ""
Write-Host "=== CONFIGURATION TERMINEE ==="
Write-Host "4 taches planifiees :"
Write-Host "  - PlyChanBot_Shorts : 6h00 (Shorts uniquement, ~10 min)"
Write-Host "  - PlyChanBot_Longs : 7h00 (Longues uniquement, ~30 min)"
Write-Host "  - PlyChanPromo : 9h, 13h, 18h (promotion)"
Write-Host "  - PlyChanSync : 12h00 (upload manquants)"
Write-Host ""
Write-Host "Pour verifier: Get-ScheduledTask | Where-Object { \$_.TaskName -like 'PlyChan*' }"