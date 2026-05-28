# Lansweeper Asset Owner Registry Update Script (CSV Version)
# This script reads asset owner information from a CSV file and updates the local registry
# No Excel installation required

param(
    [Parameter(Mandatory=$false)]
    [string]$CsvFilePath = "\\ladjitfstech.ger.corp.intel.com\Lansweeper_win10_to_11\owner_to_update_31_7.csv",
    
    [Parameter(Mandatory=$false)]
    [switch]$ForceUpdate = $true
)

# Function to write to event log for troubleshooting
function Write-EventLogEntry {
    param(
        [string]$Message,
        [string]$EntryType = "Information"
    )
    
    $LogName = "Application"
    $Source = "LansweeperAssetOwner"
    
    # Create event source if it doesn't exist
    if (-not [System.Diagnostics.EventLog]::SourceExists($Source)) {
        try {
            New-EventLog -LogName $LogName -Source $Source -ErrorAction SilentlyContinue
        } catch {
            # Silently continue if we can't create the source
        }
    }
    
    try {
        Write-EventLog -LogName $LogName -Source $Source -EntryType $EntryType -EventId 1000 -Message $Message
    } catch {
        # Silently continue if we can't write to event log
    }
}

# Function to get current computer name
function Get-ComputerName {
    return $env:COMPUTERNAME
}

# Function to create registry key if it doesn't exist
function Ensure-RegistryPath {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        try {
            New-Item -Path $Path -Force | Out-Null
            Write-EventLogEntry "Created registry path: $Path"
            return $true
        } catch {
            Write-EventLogEntry "Failed to create registry path: $Path. Error: $($_.Exception.Message)" "Error"
            return $false
        }
    }
    return $true
}

# Function to set registry value
function Set-OwnerRegistry {
    param(
        [string]$Owner,
        [string]$AssetName,
        [switch]$ForceUpdate
    )
    
    $RegistryPath = "HKLM:\SOFTWARE\Lansweeper\Custom"
    
    if (Ensure-RegistryPath $RegistryPath) {
        try {
            # Check if the Owner value already exists
            $ExistingOwner = $null
            try {
                $ExistingOwner = Get-ItemProperty -Path $RegistryPath -Name "Owner" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Owner
                Write-EventLogEntry "Registry value ($ExistingOwner)"
            } catch {
                # Value doesn't exist, which is fine
            }
            
            if ($ExistingOwner) {
                if ($ExistingOwner -eq $Owner) {
                    Write-EventLogEntry "Registry value already exists with same owner ($Owner). No update needed for asset: $AssetName"
                    return $true
                } elseif (-not $ForceUpdate) {
                    Write-EventLogEntry "Registry value already exists with different owner ($ExistingOwner vs $Owner). Use -ForceUpdate to overwrite for asset: $AssetName" "Warning"
                    return $false
                } else {
                    Write-EventLogEntry "Forcing update from existing owner ($ExistingOwner) to new owner ($Owner) for asset: $AssetName"
                }
            }
            
            Set-ItemProperty -Path $RegistryPath -Name "Owner" -Value $Owner -Type String
            Write-EventLogEntry "Successfully updated registry with owner: $Owner for asset: $AssetName"
            return $true
        } catch {
            Write-EventLogEntry "Failed to set registry value. Error: $($_.Exception.Message)" "Error"
            return $false
        }
    }
    return $false
}

# Main execution
try {
    Write-EventLogEntry "Starting Asset Owner Registry Update Script (CSV Version)"
    
    $CurrentComputer = Get-ComputerName
    Write-EventLogEntry "Current computer name: $CurrentComputer"
    
    # Check if CSV file exists and is accessible
    if (-not (Test-Path $CsvFilePath)) {
        Write-EventLogEntry "CSV file not found or not accessible: $CsvFilePath" "Warning"
        exit 1
    }
    
    Write-EventLogEntry "CSV file found: $CsvFilePath"
    
    # Import CSV file
    try {
        $AssetData = Import-Csv -Path $CsvFilePath
        Write-EventLogEntry "Successfully imported CSV file with $($AssetData.Count) rows"
    } catch {
        Write-EventLogEntry "Failed to import CSV file. Error: $($_.Exception.Message)" "Error"
        exit 1
    }
    
    # Validate required columns exist
    if (-not $AssetData[0].PSObject.Properties.Name -contains "AssetName") {
        Write-EventLogEntry "CSV file is missing required 'AssetName' column" "Error"
        exit 1
    }
    
    if (-not $AssetData[0].PSObject.Properties.Name -contains "Owners") {
        Write-EventLogEntry "CSV file is missing required 'Owners' column" "Error"
        exit 1
    }
    
    Write-EventLogEntry "CSV file validation passed - required columns found"
    
    # Search for current computer in the asset list
    $OwnerFound = $false
    $MatchingAsset = $AssetData | Where-Object { $_.AssetName -eq $CurrentComputer } | Select-Object -First 1
    
    if ($MatchingAsset) {
        $Owner = $MatchingAsset.Owners
        
        if ($Owner -and $Owner.Trim() -ne "") {
            Write-EventLogEntry "Found match: Asset=$CurrentComputer, Owner=$Owner"
            
            if (Set-OwnerRegistry -Owner $Owner.Trim() -AssetName $CurrentComputer -ForceUpdate:$ForceUpdate) {
                Write-EventLogEntry "Successfully processed asset owner update"
                $OwnerFound = $true
            } else {
                Write-EventLogEntry "Failed to update registry" "Error"
            }
        } else {
            Write-EventLogEntry "Owner field is empty for asset: $CurrentComputer" "Warning"
        }
    } else {
        Write-EventLogEntry "No matching asset found for computer: $CurrentComputer" "Warning"
    }
    
    if (-not $OwnerFound) {
        Write-EventLogEntry "Asset owner was not updated for computer: $CurrentComputer" "Warning"
    }
    
} catch {
    Write-EventLogEntry "Script execution failed. Error: $($_.Exception.Message)" "Error"
    exit 1
}

Write-EventLogEntry "Asset Owner Registry Update Script completed successfully"
exit 0