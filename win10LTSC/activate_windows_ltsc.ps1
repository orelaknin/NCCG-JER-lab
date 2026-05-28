# Windows LTSC KMS Activation Script
# Run this script as Administrator

Write-Host "Starting Windows LTSC KMS Activation..." -ForegroundColor Cyan
Write-Host ""

# Change to System32 directory
Set-Location C:\Windows\System32

# Step 1: Install product key
Write-Host "Step 1: Installing product key..." -ForegroundColor Yellow
$result1 = cscript slmgr.vbs /ipk M7XTQ-FN8P6-TTKYV-9D4CC-J462D
Write-Host $result1
Write-Host ""

# Step 2: Set KMS server
Write-Host "Step 2: Setting KMS server..." -ForegroundColor Yellow
$result2 = cscript slmgr.vbs /skms kms.intel.com
Write-Host $result2
Write-Host ""

# Step 3: Activate Windows
Write-Host "Step 3: Activating Windows..." -ForegroundColor Yellow
$result3 = cscript slmgr.vbs /ato
Write-Host $result3
Write-Host ""

Write-Host "Activation process completed!" -ForegroundColor Green
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
