$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')
Set-Location 'C:\Users\sofia\Documents\WarframeTools\Warframe-Algo-Trader'
python -m uvicorn inventoryApi:app --reload
