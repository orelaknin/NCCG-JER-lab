$ExcludedUsers = @("Administrator", "Public", "Default", "sshd", "WDAGUtilityAccount", "laduser", "defaultuser0")
$ProfilePath = "C:\Users"
$ProfileList = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
$LogFile = "C:\Logs\ProfileCleanup.log"

# Create log directory if it doesn't exist
$LogDir = Split-Path $LogFile -Parent
if (-not (Test-Path $LogDir)) {
    New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
}

# Get the SID of the current user to exclude
$CurrentUserSID = (Get-WmiObject -Class Win32_UserProfile | Where-Object { $_.Loaded -eq $true } | Select-Object -First 1).SID
if (-not $CurrentUserSID) {
    $CurrentUserSID = (Get-WmiObject Win32_ComputerSystem | Select-Object -ExpandProperty UserName -ErrorAction SilentlyContinue).Split('\')[1]
    $CurrentUserSID = (Get-WmiObject -Class Win32_UserAccount | Where-Object { $_.Name -eq $CurrentUserSID } | Select-Object -ExpandProperty SID)
}

# Get all user profiles from the registry
$Profiles = Get-ChildItem $ProfileList | ForEach-Object {
    $ProfileImagePath = (Get-ItemProperty -Path $_.PSPath -Name ProfileImagePath -ErrorAction SilentlyContinue).ProfileImagePath
    [PSCustomObject]@{
        SID = $_.PSChildName
        ProfilePath = $ProfileImagePath
    }
}

# Define the range of corrupt RIDs (last four digits)
$CorruptRIDs = 1004..1020

# Filter profiles to delete
foreach ($Profile in $Profiles) {
    $Username = if ($Profile.ProfilePath) { Split-Path $Profile.ProfilePath -Leaf } else { $null }
    $RID = [int]($Profile.SID -split '-' | Select-Object -Last 1)

    # Skip if SID matches current user, user is excluded, or RID is not in corrupt range
    if ($Profile.SID -eq $CurrentUserSID) { continue }
    if ($ExcludedUsers -contains $Username) { continue }
    if ($CorruptRIDs -notcontains $RID) { continue }

    # Delete the profile folder and log the action
    if ($Profile.ProfilePath -and (Test-Path $Profile.ProfilePath)) {
        Remove-Item -Path $Profile.ProfilePath -Recurse -Force -ErrorAction SilentlyContinue
        "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) - $($Profile.SID) - $Username deleted" | Out-File $LogFile -Append
    }

    # Delete the registry entry and log the action
    $RegPath = Join-Path $ProfileList $Profile.SID
    if (Test-Path $RegPath) {
        Remove-Item -Path $RegPath -Recurse -Force -ErrorAction SilentlyContinue
        "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) - $($Profile.SID) - $Username registry entry deleted" | Out-File $LogFile -Append
    }
}