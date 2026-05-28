# PowerShell script to create a scheduled task that displays a pop-up message on user login and self-destructs after 24 hours

# Define the message content
$message = "*** URGENT ALERT! *** Windows 11 Upgrade Scheduled for 19.8 . Save your work and restart when prompted. For concerns or to reschedule, contact your site’s IT support:HA-Sharrouf Marrouf, JER-Aknin Orel, PTK- Magar Gocha or Avtalion DoriX."

# Define the scheduled task parameters for the pop-up
$taskName = "LoginPopupMessage"
$taskDescription = "Displays a pop-up message to users upon login"
$action = New-ScheduledTaskAction -Execute "msg.exe" -Argument "* `"$message`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -GroupId "Users" -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 24)

# Create the pop-up task with a 24-hour expiration
Register-ScheduledTask -TaskName $taskName -Description $taskDescription -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force

# Create a cleanup task to delete the pop-up task after 24 hours
$cleanupTaskName = "CleanupLoginPopup"
$cleanupTaskDescription = "Deletes the LoginPopupMessage task after 24 hours"
$cleanupAction = New-ScheduledTaskAction -Execute "schtasks.exe" -Argument "/Delete /TN $taskName /F"
$cleanupTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddHours(1)
$cleanupPrincipal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$cleanupSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Register the cleanup task
Register-ScheduledTask -TaskName $cleanupTaskName -Description $cleanupTaskDescription -Action $cleanupAction -Trigger $cleanupTrigger -Principal $cleanupPrincipal -Settings $cleanupSettings -Force