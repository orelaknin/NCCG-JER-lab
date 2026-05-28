# Enhanced Profile Cleanup Script with Multiple Safety Checks
# This script identifies and removes corrupt/unused user profiles with extensive safety measures

#region Configuration
$ExcludedUsers = @("Administrator", "Public", "Default", "sshd", "WDAGUtilityAccount", "laduser", "defaultuser0", "nduser", "lab_lansweeper", "sys_ethfwcigeneric")
$ProfilePath = "C:\Users"
$ProfileList = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
$LogFile = "C:\Logs\ProfileCleanup_Enhanced.log"
$DiagnosticLog = "C:\Logs\ProfileDiagnostic.log"

# Safety Settings
$DryRun = $true  # Set to $false to actually delete profiles
$InactiveDays = 90  # Only delete profiles not used in X days
$RequireCorruptionCheck = $true  # Require profiles to show signs of corruption

# Corruption detection can include:
# - Missing NTUSER.DAT file
# - Empty profile folder
# - Profile folder doesn't exist but registry entry does
# - Registry State field indicates corruption
$CorruptionChecks = @{
    CheckMissingNTUSER = $true
    CheckEmptyFolder = $true
    CheckMissingFolder = $true
    CheckRegistryState = $true
}
#endregion

#region Initialize Logging
$LogDir = Split-Path $LogFile -Parent
if (-not (Test-Path $LogDir)) {
    New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
}

function Write-Log {
    param($Message, $Level = "INFO")
    $Timestamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    $LogEntry = "$Timestamp - [$Level] - $Message"
    $LogEntry | Out-File $LogFile -Append
    
    switch ($Level) {
        "ERROR" { Write-Host $LogEntry -ForegroundColor Red }
        "WARNING" { Write-Host $LogEntry -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $LogEntry -ForegroundColor Green }
        "INFO" { Write-Host $LogEntry -ForegroundColor Cyan }
        default { Write-Host $LogEntry }
    }
}

Write-Log "=== Profile Cleanup Script Started ===" "INFO"
if ($DryRun) {
    Write-Log "DRY RUN MODE - No profiles will be deleted" "WARNING"
}
#endregion

#region Get Current User and Loaded Profiles
Write-Log "Getting current user and loaded profiles..." "INFO"

# Get the SID of the current user to exclude
$CurrentUserSID = (Get-WmiObject -Class Win32_UserProfile | Where-Object { $_.Loaded -eq $true } | Select-Object -First 1).SID
if (-not $CurrentUserSID) {
    $CurrentUserSID = (Get-WmiObject Win32_ComputerSystem | Select-Object -ExpandProperty UserName -ErrorAction SilentlyContinue).Split('\')[1]
    $CurrentUserSID = (Get-WmiObject -Class Win32_UserAccount | Where-Object { $_.Name -eq $CurrentUserSID } | Select-Object -ExpandProperty SID)
}
Write-Log "Current User SID: $CurrentUserSID" "INFO"

# Get local machine SID prefix (everything except the last RID)
# Example: S-1-5-21-1753665887-1522915299-136686024-1001 -> S-1-5-21-1753665887-1522915299-136686024
$LocalMachineSID = ($CurrentUserSID -split '-')[0..6] -join '-'
Write-Log "Local Machine SID Prefix: $LocalMachineSID" "INFO"

# Get all currently loaded profiles (users logged in)
$LoadedProfiles = Get-WmiObject -Class Win32_UserProfile | Where-Object { $_.Loaded -eq $true } | Select-Object -ExpandProperty SID
Write-Log "Loaded Profiles: $($LoadedProfiles.Count)" "INFO"
#endregion

#region Get All Profiles from Registry
Write-Log "Reading all profiles from registry..." "INFO"

$Profiles = Get-ChildItem $ProfileList | ForEach-Object {
    $RegKey = Get-ItemProperty -Path $_.PSPath -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        SID = $_.PSChildName
        ProfilePath = $RegKey.ProfileImagePath
        State = $RegKey.State
        LastUseTime = $RegKey.LocalProfileLoadTimeLow
    }
}

Write-Log "Total profiles in registry: $($Profiles.Count)" "INFO"
#endregion

#region Profile Analysis and Deletion
$ProfilesAnalyzed = 0
$ProfilesSkipped = 0
$ProfilesDeleted = 0
$ProfilesMarkedForDeletion = 0

foreach ($Profile in $Profiles) {
    $ProfilesAnalyzed++
    $Username = if ($Profile.ProfilePath) { Split-Path $Profile.ProfilePath -Leaf } else { "UNKNOWN" }
    $ShouldDelete = $false
    $SkipReason = ""
    $CorruptionReasons = @()
    
    #region Safety Checks - Skip if any match
    
    # Skip system accounts (S-1-5-18, S-1-5-19, S-1-5-20)
    if ($Profile.SID -match '^S-1-5-(18|19|20)$') {
        $SkipReason = "System account"
        $ProfilesSkipped++
        continue
    }
    
    # Skip if SID matches current user
    if ($Profile.SID -eq $CurrentUserSID) {
        $SkipReason = "Current user"
        Write-Log "SKIPPED: $($Profile.SID) - $Username - $SkipReason" "INFO"
        $ProfilesSkipped++
        continue
    }
    
    # Skip domain users (SID doesn't match local machine SID prefix)
    if (-not $Profile.SID.StartsWith($LocalMachineSID)) {
        $SkipReason = "Domain user account"
        Write-Log "SKIPPED: $($Profile.SID) - $Username - $SkipReason" "INFO"
        $ProfilesSkipped++
        continue
    }
    
    # Skip if user is in excluded list
    if ($ExcludedUsers -contains $Username) {
        $SkipReason = "Excluded user"
        Write-Log "SKIPPED: $($Profile.SID) - $Username - $SkipReason" "INFO"
        $ProfilesSkipped++
        continue
    }
    
    # Skip if profile is currently loaded (user logged in)
    if ($LoadedProfiles -contains $Profile.SID) {
        $SkipReason = "Profile currently loaded"
        Write-Log "SKIPPED: $($Profile.SID) - $Username - $SkipReason" "WARNING"
        $ProfilesSkipped++
        continue
    }
    
    # Check last use time
    if ($InactiveDays -gt 0) {
        try {
            $RegPath = Join-Path $ProfileList $Profile.SID
            $ProfileKey = Get-ItemProperty -Path $RegPath -ErrorAction Stop
            if ($ProfileKey.PSObject.Properties.Name -contains 'LocalProfileLoadTimeLow') {
                # Convert FileTime to DateTime
                $LastUseTime = [DateTime]::FromFileTime([Int64]$ProfileKey.LocalProfileLoadTimeLow)
                $DaysSinceUse = (Get-Date) - $LastUseTime
                if ($DaysSinceUse.Days -lt $InactiveDays) {
                    $SkipReason = "Used within last $InactiveDays days (Last use: $($LastUseTime.ToString('yyyy-MM-dd')))"
                    Write-Log "SKIPPED: $($Profile.SID) - $Username - $SkipReason" "INFO"
                    $ProfilesSkipped++
                    continue
                }
            }
        } catch {
            # If we can't determine last use time, skip for safety
            $SkipReason = "Cannot verify last use time - skipping for safety"
            Write-Log "SKIPPED: $($Profile.SID) - $Username - $SkipReason" "WARNING"
            $ProfilesSkipped++
            continue
        }
    }
    
    #endregion
    
    #region Corruption Detection
    
    if ($RequireCorruptionCheck) {
        # Check 1: Registry State field (non-zero = corrupt)
        if ($CorruptionChecks.CheckRegistryState -and $Profile.State -ne $null -and $Profile.State -ne 0) {
            $CorruptionReasons += "Registry State=$($Profile.State) (indicates corruption)"
        }
        
        # Check 2: Missing profile path in registry
        if (-not $Profile.ProfilePath) {
            $CorruptionReasons += "No ProfileImagePath in registry"
        }
        
        # Check 3: Profile folder doesn't exist
        if ($CorruptionChecks.CheckMissingFolder -and $Profile.ProfilePath -and -not (Test-Path $Profile.ProfilePath)) {
            $CorruptionReasons += "Profile folder does not exist at $($Profile.ProfilePath)"
        }
        
        # Check 4: Profile folder exists but is missing critical files or empty
        if ($Profile.ProfilePath -and (Test-Path $Profile.ProfilePath)) {
            # Check for NTUSER.DAT (essential user registry hive)
            if ($CorruptionChecks.CheckMissingNTUSER -and -not (Test-Path (Join-Path $Profile.ProfilePath "NTUSER.DAT"))) {
                $CorruptionReasons += "Missing NTUSER.DAT file"
            }
            
            # Check if folder is empty
            if ($CorruptionChecks.CheckEmptyFolder) {
                $ItemCount = (Get-ChildItem -Path $Profile.ProfilePath -ErrorAction SilentlyContinue).Count
                if ($ItemCount -eq 0) {
                    $CorruptionReasons += "Profile folder is empty"
                }
            }
        }
        
        # Check 5: Temporary profile (username pattern indicates temp profile)
        # Matches: .bak, .tmp, .000, or .COMPUTERNAME (e.g., nduser.DESKTOP-FMT0J4K)
        if ($Username -match '\.(bak|tmp|\d{3})$' -or $Username -match '\.[A-Z0-9-]+$') {
            $CorruptionReasons += "Temporary/backup profile name pattern"
        }
        
        # Decide if should delete based on corruption
        if ($CorruptionReasons.Count -gt 0) {
            $ShouldDelete = $true
        } else {
            $SkipReason = "No corruption detected - profile appears valid"
            Write-Log "SKIPPED: $($Profile.SID) - $Username - $SkipReason" "INFO"
            $ProfilesSkipped++
            continue
        }
    } else {
        # If not requiring corruption check, mark for deletion (with all safety checks passed)
        $ShouldDelete = $true
        $CorruptionReasons += "Marked for deletion (corruption check disabled)"
    }
    
    #endregion
    
    #region Perform Deletion or Log Intent
    
    if ($ShouldDelete) {
        $ProfilesMarkedForDeletion++
        $CorruptionSummary = $CorruptionReasons -join " | "
        
        if ($DryRun) {
            Write-Log "WOULD DELETE: $($Profile.SID) - $Username" "WARNING"
            Write-Log "  Path: $($Profile.ProfilePath)" "WARNING"
            Write-Log "  Reasons: $CorruptionSummary" "WARNING"
        } else {
            Write-Log "DELETING: $($Profile.SID) - $Username" "WARNING"
            Write-Log "  Reasons: $CorruptionSummary" "WARNING"
            
            $DeletionSuccess = $true
            
            # Delete the profile folder
            if ($Profile.ProfilePath -and (Test-Path $Profile.ProfilePath)) {
                try {
                    Remove-Item -Path $Profile.ProfilePath -Recurse -Force -ErrorAction Stop
                    Write-Log "  ✓ Profile folder deleted: $($Profile.ProfilePath)" "SUCCESS"
                } catch {
                    Write-Log "  ✗ Failed to delete folder: $($_.Exception.Message)" "ERROR"
                    $DeletionSuccess = $false
                }
            }
            
            # Delete the registry entry
            $RegPath = Join-Path $ProfileList $Profile.SID
            if (Test-Path $RegPath) {
                try {
                    Remove-Item -Path $RegPath -Recurse -Force -ErrorAction Stop
                    Write-Log "  ✓ Registry entry deleted: $RegPath" "SUCCESS"
                } catch {
                    Write-Log "  ✗ Failed to delete registry entry: $($_.Exception.Message)" "ERROR"
                    $DeletionSuccess = $false
                }
            }
            
            if ($DeletionSuccess) {
                $ProfilesDeleted++
            }
        }
    }
    
    #endregion
}
#endregion

#region Summary Report
Write-Log "`n=== CLEANUP SUMMARY ===" "INFO"
Write-Log "Profiles Analyzed: $ProfilesAnalyzed" "INFO"
Write-Log "Profiles Skipped (Protected): $ProfilesSkipped" "INFO"
Write-Log "Profiles Marked for Deletion: $ProfilesMarkedForDeletion" "WARNING"

if ($DryRun) {
    Write-Log "*** DRY RUN MODE - No profiles were actually deleted ***" "WARNING"
    Write-Log "To perform actual deletion, set `$DryRun = `$false" "WARNING"
} else {
    Write-Log "Profiles Successfully Deleted: $ProfilesDeleted" "SUCCESS"
    if ($ProfilesMarkedForDeletion -ne $ProfilesDeleted) {
        $Failed = $ProfilesMarkedForDeletion - $ProfilesDeleted
        Write-Log "Profiles Failed to Delete: $Failed" "ERROR"
    }
}

Write-Log "`nLog file: $LogFile" "INFO"
Write-Log "=== Profile Cleanup Script Completed ===" "INFO"
#endregion
