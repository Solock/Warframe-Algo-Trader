$root = "C:\Users\sofia\Documents\WarframeTools\Warframe-Algo-Trader"

Start-Process powershell -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-File","$root\start_backend.ps1" -RedirectStandardOutput "$root\backend.log" -RedirectStandardError "$root\backend_err.log" -WindowStyle Hidden
Start-Process powershell -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-File","$root\start_frontend.ps1" -RedirectStandardOutput "$root\frontend.log" -RedirectStandardError "$root\frontend_err.log" -WindowStyle Hidden

Write-Output "Serveurs lances. Attends ~10 secondes puis ouvre http://127.0.0.1:3000"
