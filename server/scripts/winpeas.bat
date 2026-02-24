@echo off

echo === SYSTEM INFO ===

echo --- Users & Domain ---
echo %USERNAME% @ %USERDOMAIN%
wmic useraccount get name,domain /format:list | findstr "Name Domain"

echo --- Network ---
ipconfig | findstr "IPv4 Subnet Default Gateway"
netstat -an | findstr "ESTABLISHED LISTENING"

echo --- Startup ---
wmic startup get caption,command /format:list
schtasks /query /fo LIST /nh | findstr "TaskName"
net start | findstr /v "following services"

echo --- Scheduled Tasks with Possible Credentials ---
schtasks /query /fo LIST /v | findstr /i /c:"TaskName" /c:"Run As User" /c:"samba" /c:"Password" /c:"/RU" /c:"/RP"

echo --- Looking for tasks related to user samba ---
schtasks /query /fo LIST /v | findstr /i "samba"

echo --- Done ---
