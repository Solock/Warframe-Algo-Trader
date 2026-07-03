$env:Path = 'C:\Program Files\nodejs;' + [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')
Set-Location 'C:\Users\sofia\Documents\WarframeTools\Warframe-Algo-Trader\my-app'
npm run dev
