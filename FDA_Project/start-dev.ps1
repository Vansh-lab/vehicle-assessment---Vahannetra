param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot "vehicle_assessment_backend"
$frontendDir = Join-Path $repoRoot "vahannetra_frontend"
$workspaceRoot = Split-Path -Parent $repoRoot
$pythonExe = Join-Path $workspaceRoot ".venv/Scripts/python.exe"

function Assert-PortFree {
    param([int]$Port)
    $listeners = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($listeners) {
        $owners = ($listeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
        throw "Port $Port is already in use by PID(s): $owners. Run .\\stop-dev.ps1 -BackendPort $BackendPort -FrontendPort $FrontendPort first."
    }
}

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

function Wait-ForUrl {
    param(
        [string]$Url,
        [int]$MaxAttempts = 20,
        [int]$DelaySeconds = 1
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $result = Test-Url -Url $Url
        if ($result.StartsWith("OK ")) {
            return $result
        }
        Start-Sleep -Seconds $DelaySeconds
    }

    return Test-Url -Url $Url
}

if (-not (Test-Path $backendDir)) {
    throw "Backend folder not found: $backendDir"
}
if (-not (Test-Path $frontendDir)) {
    throw "Frontend folder not found: $frontendDir"
}
if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}

Assert-PortFree -Port $BackendPort
Assert-PortFree -Port $FrontendPort

$backendCmd = "Set-Location '$backendDir'; & '$pythonExe' -m uvicorn app.main:app --host 0.0.0.0 --port $BackendPort"
$frontendCmd = "Set-Location '$frontendDir'; `$env:NEXT_PUBLIC_USE_BACKEND='true'; `$env:NEXT_PUBLIC_API_BASE_URL='http://localhost:$BackendPort'; npm run dev -- --hostname 0.0.0.0 --port $FrontendPort"

Start-Process powershell -ArgumentList @('-NoExit', '-Command', $backendCmd)
Start-Process powershell -ArgumentList @('-NoExit', '-Command', $frontendCmd)

Write-Host "Backend starting at http://localhost:$BackendPort"
Write-Host "Frontend starting at http://localhost:$FrontendPort"
Write-Host "Login credentials: ops@insurer.com / password123"
Write-Host (Wait-ForUrl -Url "http://localhost:$BackendPort/docs" -MaxAttempts 30 -DelaySeconds 1)
Write-Host (Wait-ForUrl -Url "http://localhost:$FrontendPort/login" -MaxAttempts 30 -DelaySeconds 1)
