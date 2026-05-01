Write-Host "Starting load test..." -ForegroundColor Cyan

# 10 tps - idle
helm upgrade transaction-simulator helm/charts/transaction-simulator `
  --namespace fraud-detection `
  --set simulator.transactionsPerSecond=10 `
  --set replicaCount=1

Write-Host "10 tps - waiting 60s for baseline" -ForegroundColor Gray
Start-Sleep 60

# 50 tps - lag starts building
helm upgrade transaction-simulator helm/charts/transaction-simulator `
  --namespace fraud-detection `
  --set simulator.transactionsPerSecond=50 `
  --set replicaCount=2

Write-Host "50 tps - waiting 60s, watch KEDA scale to 2-3 pods" -ForegroundColor Yellow
Start-Sleep 60

# 150 tps - heavy load
helm upgrade transaction-simulator helm/charts/transaction-simulator `
  --namespace fraud-detection `
  --set simulator.transactionsPerSecond=100 `
  --set replicaCount=3

Write-Host "150 tps - waiting 90s, watch KEDA scale to 4-5 pods" -ForegroundColor Red
Start-Sleep 90

# Back to idle
helm upgrade transaction-simulator helm/charts/transaction-simulator `
  --namespace fraud-detection `
  --set simulator.transactionsPerSecond=10 `
  --set replicaCount=1

Write-Host "Back to 10 tps - watching KEDA scale back down" -ForegroundColor Green
Write-Host "Done." -ForegroundColor Cyan