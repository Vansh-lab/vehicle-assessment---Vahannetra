param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Test-Url {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 6
        return "OK $($response.StatusCode) $Url"
    }
    catch {
        return "FAIL $Url :: $($_.Exception.Message)"
    }
}

Write-Host (Test-Url -Url "http://localhost:$BackendPort/docs")
Write-Host (Test-Url -Url "http://localhost:$FrontendPort/login")
