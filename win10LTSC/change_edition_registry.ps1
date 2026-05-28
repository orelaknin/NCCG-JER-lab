# Script to change Windows Edition Registry Values
# Must be run as Administrator

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Please right-click and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit
}

# Define the registry path
$registryPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion"

Write-Host "Modifying Windows Edition Registry Values..." -ForegroundColor Cyan
Write-Host "Registry Path: $registryPath" -ForegroundColor Gray
Write-Host ""

try {
    # Get current values
    Write-Host "Current Values:" -ForegroundColor Yellow
    $currentCompositionEditionID = Get-ItemPropertyValue -Path $registryPath -Name "CompositionEditionID" -ErrorAction SilentlyContinue
    $currentEditionID = Get-ItemPropertyValue -Path $registryPath -Name "EditionID" -ErrorAction SilentlyContinue
    $currentProductName = Get-ItemPropertyValue -Path $registryPath -Name "ProductName" -ErrorAction SilentlyContinue
    
    Write-Host "  CompositionEditionID: $currentCompositionEditionID"
    Write-Host "  EditionID: $currentEditionID"
    Write-Host "  ProductName: $currentProductName"
    Write-Host ""

    # Set new values
    Write-Host "Setting new values..." -ForegroundColor Green
    
    Set-ItemProperty -Path $registryPath -Name "CompositionEditionID" -Value "EnterpriseS" -Type String
    Write-Host "  CompositionEditionID set to: EnterpriseS" -ForegroundColor Green
    
    Set-ItemProperty -Path $registryPath -Name "EditionID" -Value "EnterpriseS" -Type String
    Write-Host "  EditionID set to: EnterpriseS" -ForegroundColor Green
    
    Set-ItemProperty -Path $registryPath -Name "ProductName" -Value "Windows 10 EnterpriseS" -Type String
    Write-Host "  ProductName set to: Windows 10 EnterpriseS" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "Registry values updated successfully!" -ForegroundColor Green
    
    # Verify new values
    Write-Host ""
    Write-Host "Verifying new values:" -ForegroundColor Yellow
    $newCompositionEditionID = Get-ItemPropertyValue -Path $registryPath -Name "CompositionEditionID"
    $newEditionID = Get-ItemPropertyValue -Path $registryPath -Name "EditionID"
    $newProductName = Get-ItemPropertyValue -Path $registryPath -Name "ProductName"
    
    Write-Host "  CompositionEditionID: $newCompositionEditionID"
    Write-Host "  EditionID: $newEditionID"
    Write-Host "  ProductName: $newProductName"
    
    Write-Host ""
    Write-Host "Note: You may need to restart your computer for changes to take full effect." -ForegroundColor Yellow
    
} catch {
    Write-Host "Error occurred: $_" -ForegroundColor Red
    Write-Host "Make sure you are running this script as Administrator." -ForegroundColor Yellow
}

Write-Host ""
pause
