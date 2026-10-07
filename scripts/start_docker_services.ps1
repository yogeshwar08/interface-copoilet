$dockerExe = "C:\Users\yoges\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe"

if (Test-Path $dockerExe) {
    Write-Host "Found Docker Desktop at: $dockerExe"
    Write-Host "Checking if Docker is already running..."
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Starting Docker Desktop process..."
        Start-Process $dockerExe
        Write-Host "Waiting for Docker engine to initialize..."
        $maxWait = 90
        $waited = 0
        while ($waited -lt $maxWait) {
            docker info 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Docker daemon is now ONLINE!"
                break
            }
            Start-Sleep -Seconds 4
            $waited += 4
            Write-Host "Waiting for Docker engine... ($waited s / $maxWait s)"
        }
    } else {
        Write-Host "Docker daemon is already ONLINE!"
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Starting PostgreSQL 16 and Jaeger containers..."
        docker compose -f "c:\Users\yoges\OneDrive\Desktop\agentic-enterprise-copilot\docker-compose.yml" up -d postgres jaeger
        docker compose -f "c:\Users\yoges\OneDrive\Desktop\agentic-enterprise-copilot\docker-compose.yml" ps
    } else {
        Write-Host "Docker engine did not respond in time. Please check the Docker Desktop window."
    }
} else {
    Write-Host "Docker Desktop executable not found at $dockerExe"
}
