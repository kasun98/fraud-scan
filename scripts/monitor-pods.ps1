while ($true) {
  Clear-Host

  Write-Host "=== PODS ===" -ForegroundColor Cyan
  kubectl get pods -n fraud-detection `
    --no-headers `
    -o custom-columns="NAME:.metadata.name,READY:.status.containerStatuses[0].ready,STATUS:.status.phase"

  Write-Host "`n=== KEDA (lag-based scaling) ===" -ForegroundColor Yellow
  kubectl get scaledobject -n fraud-detection

  Write-Host "`n=== REPLICAS ===" -ForegroundColor Green
  kubectl get deployment -n fraud-detection `
    --no-headers `
    -o custom-columns="SERVICE:.metadata.name,DESIRED:.spec.replicas,READY:.status.readyReplicas"

  Start-Sleep 4
}