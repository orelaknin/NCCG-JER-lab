# Enhanced Profile Cleanup Script with Duplicate User Detection
# This script identifies and removes corrupt/unused user profiles with extensive safety measures
# NEW: Detects multiple SIDs for same user and keeps only the most recent

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

# NEW: Duplicate User Settings
$HandleDuplicateUsers = $true  # Detect and handle multiple SIDs for same user
$KeepMostRecentDuplicate = $true  # Keep only the most recently used profile for duplicates
$AutoDeleteOlderDuplicates = $false  # Auto-delete older duplicates (if false, requires corruption)

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
        "DUPLICATE" { Write-Host $LogEntry -ForegroundColor Magenta }
        default { Write-Host $LogEntry }
    }
}

Write-Log "=== Profile Cleanup Script Started ===" "INFO"
if ($DryRun) {
    Write-Log "DRY RUN MODE - No profiles will be deleted" "WARNING"
}
if ($HandleDuplicateUsers) {
    Write-Log "DUPLICATE DETECTION ENABLED - Will identify multiple SIDs for same user" "INFO"
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
    
    # Get last use time
    $LastUseTime = $null
    if ($RegKey.PSObject.Properties.Name -contains 'LocalProfileLoadTimeLow') {
        try {
            $LastUseTime = [DateTime]::FromFileTime([Int64]$RegKey.LocalProfileLoadTimeLow)
        } catch {
            $LastUseTime = $null
        }
    }
    
    [PSCustomObject]@{
        SID = $_.PSChildName
        ProfilePath = $RegKey.ProfileImagePath
        State = $RegKey.State
        LastUseTime = $LastUseTime
        Username = if ($RegKey.ProfileImagePath) { Split-Path $RegKey.ProfileImagePath -Leaf } else { "UNKNOWN" }
    }
}

Write-Log "Total profiles in registry: $($Profiles.Count)" "INFO"
#endregion

#region Detect Duplicate Users (Multiple SIDs for Same Username)
$DuplicateReport = @{}
$ProfilesToKeep = @{}

if ($HandleDuplicateUsers) {
    Write-Log "`n=== DUPLICATE USER DETECTION ===" "INFO"
    
    # Group profiles by base username (strip .COMPUTERNAME suffixes for analysis)
    $ProfilesByBaseUsername = $Profiles | Where-Object { 
        $_.SID.StartsWith($LocalMachineSID) -and 
        $_.SID -notmatch '^S-1-5-(18|19|20)$'
    } | Group-Object -Property { 
        # Extract base username (remove .DESKTOP-XXX or .bak suffixes)
        $un = $_.Username
        if ($un -match '^(.+?)\.(DESKTOP-|bak|tmp)') { $matches[1] } else { $un }
    }
    
    foreach ($UserGroup in $ProfilesByBaseUsername) {
        $BaseUsername = $UserGroup.Name
        $UserProfiles = $UserGroup.Group
        
        if ($UserProfiles.Count -gt 1) {
            Write-Log "`nFOUND DUPLICATE: '$BaseUsername' has $($UserProfiles.Count) profiles" "DUPLICATE"
            
            # Sort by last use time (most recent first)
            $SortedProfiles = $UserProfiles | Sort-Object -Property LastUseTime -Descending
            
            $DuplicateReport[$BaseUsername] = @{
                TotalCount = $UserProfiles.Count
                Profiles = $SortedProfiles
                MostRecent = $SortedProfiles[0]
            }
            
            # Display details
            for ($i = 0; $i -lt $SortedProfiles.Count; $i++) {
                $prof = $SortedProfiles[$i]
                $isMostRecent = ($i -eq 0)
                $lastUse = if ($prof.LastUseTime) { $prof.LastUseTime.ToString('yyyy-MM-dd HH:mm:ss') } else { "NEVER" }
                $exists = if ($prof.ProfilePath -and (Test-Path $prof.ProfilePath)) { "YES" } else { "NO" }
                $marker = if ($isMostRecent) { " [KEEP - MOST RECENT]" } else { " [CANDIDATE FOR REMOVAL]" }
                
                Write-Log "  [$($i+1)] SID: $($prof.SID)" "DUPLICATE"
                Write-Log "      User: $($prof.Username)" "DUPLICATE"
                Write-Log "      Path: $($prof.ProfilePath) (Exists: $exists)" "DUPLICATE"
                Write-Log "      Last Used: $lastUse$marker" "DUPLICATE"
                
                # Mark the most recent one to keep
                if ($isMostRecent -and $KeepMostRecentDuplicate) {
                    $ProfilesToKeep[$prof.SID] = $true
                }
            }
        }
    }
    
    if ($DuplicateReport.Count -eq 0) {
        Write-Log "No duplicate users detected" "INFO"
    } else {
        Write-Log "`nTotal users with duplicates: $($DuplicateReport.Count)" "DUPLICATE"
    }
    Write-Log "=== END DUPLICATE DETECTION ===`n" "INFO"
}
#endregion

#region Profile Analysis and Deletion
$ProfilesAnalyzed = 0
$ProfilesSkipped = 0
$ProfilesDeleted = 0
$ProfilesMarkedForDeletion = 0

foreach ($Profile in $Profiles) {
    $ProfilesAnalyzed++
    $Username = $Profile.Username
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
    
    # Skip if user is in excluded list (base username check)
    $BaseUsername = if ($Username -match '^(.+?)\.(DESKTOP-|bak|tmp)') { $matches[1] } else { $Username }
    if ($ExcludedUsers -contains $BaseUsername) {
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
    
    # NEW: Skip if this is marked as the profile to keep (most recent duplicate)
    if ($ProfilesToKeep.ContainsKey($Profile.SID)) {
        $SkipReason = "Most recent profile for user with duplicates"
        Write-Log "SKIPPED: $($Profile.SID) - $Username - $SkipReason" "INFO"
        $ProfilesSkipped++
        continue
    }
    
    # Check last use time
    if ($InactiveDays -gt 0 -and $Profile.LastUseTime) {
        $DaysSinceUse = (Get-Date) - $Profile.LastUseTime
        if ($DaysSinceUse.Days -lt $InactiveDays) {
            # Exception: If AutoDeleteOlderDuplicates is enabled and this is a duplicate, proceed
            if (-not ($AutoDeleteOlderDuplicates -and $DuplicateReport.Keys -contains $BaseUsername)) {
                $SkipReason = "Used within last $InactiveDays days (Last use: $($Profile.LastUseTime.ToString('yyyy-MM-dd')))"
                Write-Log "SKIPPED: $($Profile.SID) - $Username - $SkipReason" "INFO"
                $ProfilesSkipped++
                continue
            }
        }
    }
    
    #endregion
    
    #region Corruption Detection
    
    if ($RequireCorruptionCheck -or -not $AutoDeleteOlderDuplicates) {
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
        if ($Username -match '\.(bak|tmp|\d{3})$' -or $Username -match '\.[A-Z0-9-]+$') {
            $CorruptionReasons += "Temporary/backup profile name pattern"
        }
        
        # NEW: Check 6: Duplicate user (older profile)
        if ($DuplicateReport.Keys -contains $BaseUsername -and -not $ProfilesToKeep.ContainsKey($Profile.SID)) {
            $CorruptionReasons += "Older duplicate profile for user '$BaseUsername'"
            
            # If AutoDeleteOlderDuplicates is enabled, mark for deletion even without other corruption
            if ($AutoDeleteOlderDuplicates) {
                $ShouldDelete = $true
            }
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
                    Write-Log "  [OK] Profile folder deleted: $($Profile.ProfilePath)" "SUCCESS"
                } catch {
                    Write-Log "  [FAIL] Failed to delete folder: $($_.Exception.Message)" "ERROR"
                    $DeletionSuccess = $false
                }
            }
            
            # Delete the registry entry
            $RegPath = Join-Path $ProfileList $Profile.SID
            if (Test-Path $RegPath) {
                try {
                    Remove-Item -Path $RegPath -Recurse -Force -ErrorAction Stop
                    Write-Log "  [OK] Registry entry deleted: $RegPath" "SUCCESS"
                } catch {
                    Write-Log "  [FAIL] Failed to delete registry entry: $($_.Exception.Message)" "ERROR"
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

if ($HandleDuplicateUsers -and $DuplicateReport.Count -gt 0) {
    Write-Log "`n=== DUPLICATE USER SUMMARY ===" "DUPLICATE"
    foreach ($BaseUsername in $DuplicateReport.Keys) {
        $dupInfo = $DuplicateReport[$BaseUsername]
        Write-Log "User '$BaseUsername': $($dupInfo.TotalCount) profiles found" "DUPLICATE"
        Write-Log "  Keeping: SID $($dupInfo.MostRecent.SID) (Last used: $($dupInfo.MostRecent.LastUseTime))" "DUPLICATE"
    }
}

if ($DryRun) {
    Write-Log "`n*** DRY RUN MODE - No profiles were actually deleted ***" "WARNING"
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
