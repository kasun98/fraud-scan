$StuckNamespaces = @("kafka", "observability", "fraud-detection", "keda")

foreach ($NS in $StuckNamespaces) {
    Write-Host "--- Force-clearing $NS ---" -ForegroundColor Cyan
    
    # 1. Get the namespace data directly into a variable
    $nsData = kubectl get namespace $NS -o json | ConvertFrom-Json
    
    if ($nsData) {
        # 2. Clear the finalizers in memory
        $nsData.spec.finalizers = @()
        
        # 3. Convert back to a clean JSON string
        $body = $nsData | ConvertTo-Json -Depth 10
        
        # 4. Send the string directly as the body (No files = No BOM errors)
        try {
            Invoke-RestMethod -Method Put `
                -Uri "http://localhost:8001/api/v1/namespaces/$NS/finalize" `
                -ContentType "application/json" `
                -Body $body
            Write-Host "Success: $NS is gone." -ForegroundColor Green
        } catch {
            Write-Host "Failed to clear $NS. Check if 'kubectl proxy' is running." -ForegroundColor Red
            $_.Exception.Message
        }
    } else {
        Write-Host "Namespace $NS not found, skipping..." -ForegroundColor Gray
    }
}