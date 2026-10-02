param([switch] $OptimizedPreview)
$ErrorActionPreference = 'Stop'
$taskRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
$taskPgData = Join-Path $taskRoot '.local\postgres'
function Test-LegionPort([int] $Port) {
    $taskClient = [System.Net.Sockets.TcpClient]::new()
    try { $taskConnection = $taskClient.ConnectAsync('127.0.0.1', $Port); return $taskConnection.Wait(500) -and $taskClient.Connected } catch { return $false } finally { $taskClient.Dispose() }
}
if (-not (Test-LegionPort 55432)) {
    if (-not (Test-Path -LiteralPath $taskPgData)) { throw 'Initialize the isolated cluster with tools/setup_local_postgres.py first.' }
    Start-Process -FilePath 'C:\Program Files\PostgreSQL\18\bin\postgres.exe' -ArgumentList @('-D', $taskPgData, '-h', '127.0.0.1', '-p', '55432') -WindowStyle Hidden -WorkingDirectory $taskRoot -RedirectStandardOutput (Join-Path $taskRoot '.local\postgres-output.log') -RedirectStandardError (Join-Path $taskRoot '.local\postgres-errors.log') | Out-Null
}
for ($taskAttempt=0; $taskAttempt -lt 20 -and -not (Test-LegionPort 55432); $taskAttempt++) { Start-Sleep -Milliseconds 250 }
if (-not (Test-LegionPort 55432)) { throw 'The isolated PostgreSQL cluster did not become ready. See .local/postgres-errors.log.' }
if ($OptimizedPreview) {
    if (-not (Test-LegionPort 8002)) {
        $taskPreviousDebug=$env:DEBUG
        try { $env:DEBUG='false'; & $taskPython (Join-Path $taskRoot 'manage.py') collectstatic --noinput; if ($LASTEXITCODE -ne 0) { throw 'collectstatic failed.' } }
        finally { $env:DEBUG=$taskPreviousDebug }
        Start-Process -FilePath $taskPython -ArgumentList @('-u','tools/preview_server.py') -WindowStyle Hidden -WorkingDirectory $taskRoot -RedirectStandardOutput (Join-Path $taskRoot '.local\preview-output.log') -RedirectStandardError (Join-Path $taskRoot '.local\preview-errors.log') | Out-Null
    }
    Write-Output 'Optimized local site: http://127.0.0.1:8002/; Admin: http://127.0.0.1:8002/admin/'
} else {
    if (-not (Test-LegionPort 8000)) {
        Start-Process -FilePath $taskPython -ArgumentList @('manage.py', 'runserver', '127.0.0.1:8000') -WindowStyle Hidden -WorkingDirectory $taskRoot -RedirectStandardOutput (Join-Path $taskRoot '.local\django-output.log') -RedirectStandardError (Join-Path $taskRoot '.local\django-errors.log') | Out-Null
    }
    Write-Output 'Local site: http://127.0.0.1:8000/; Admin: http://127.0.0.1:8000/admin/'
}
