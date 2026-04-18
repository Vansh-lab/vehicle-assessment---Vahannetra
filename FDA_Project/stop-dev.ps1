param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"

$ports = @($BackendPort, $FrontendPort)
foreach ($port in $ports) {
    $listeners = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    if (-not $listeners) {
        Write-Host "No process listening on port $port"
        continue
    }

    $processIds = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $processIds) {
        try {
            Stop-Process -Id $processId -Force
            Write-Host "Stopped PID $processId on port $port"
        }
        catch {
            Write-Host "Failed to stop PID $processId on port ${port}: $($_.Exception.Message)"
        }
    }
}
