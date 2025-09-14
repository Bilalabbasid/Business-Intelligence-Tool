Write-Host "🚀 Business Intelligence Tool Setup Verification" -ForegroundColor Blue
Write-Host "=============================================" -ForegroundColor Blue
Write-Host ""

# Function to test if a port is open
function Test-Port {
    param([string]$Host, [int]$Port)
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.ReceiveTimeout = 1000
        $tcpClient.SendTimeout = 1000
        $tcpClient.Connect($Host, $Port)
        $tcpClient.Close()
        return $true
    }
    catch {
        return $false
    }
}

# Check Python
Write-Host "🔍 Checking Python..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1 | Out-String
    Write-Host "✅ Python: $($pythonVersion.Trim())" -ForegroundColor Green
}
catch {
    Write-Host "❌ Python not found" -ForegroundColor Red
}

# Check Node.js
Write-Host "🔍 Checking Node.js..." -ForegroundColor Cyan
try {
    $nodeVersion = node --version 2>&1 | Out-String
    $npmVersion = npm --version 2>&1 | Out-String
    Write-Host "✅ Node.js: $($nodeVersion.Trim())" -ForegroundColor Green
    Write-Host "✅ npm: $($npmVersion.Trim())" -ForegroundColor Green
}
catch {
    Write-Host "❌ Node.js not found" -ForegroundColor Red
}

# Check Go
Write-Host "🔍 Checking Go..." -ForegroundColor Cyan
try {
    $goVersion = go version 2>&1 | Out-String
    Write-Host "✅ Go: $($goVersion.Trim())" -ForegroundColor Green
}
catch {
    Write-Host "❌ Go not found" -ForegroundColor Red
}

# Check Docker
Write-Host "🔍 Checking Docker..." -ForegroundColor Cyan
try {
    $dockerVersion = docker --version 2>&1 | Out-String
    Write-Host "✅ Docker: $($dockerVersion.Trim())" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker not found or not running" -ForegroundColor Red
}

# Check Git
Write-Host "🔍 Checking Git..." -ForegroundColor Cyan
try {
    git status | Out-Null 2>&1
    Write-Host "✅ Git repository initialized" -ForegroundColor Green
}
catch {
    Write-Host "❌ Git not available or not a repository" -ForegroundColor Red
}

# Check Project Structure
Write-Host "🔍 Checking Project Structure..." -ForegroundColor Cyan
$dirs = @("bi_tool", "bi-frontend", "backup-cli", "logscan", "docs", "scripts")
foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        Write-Host "✅ Directory: $dir" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $dir" -ForegroundColor Red
    }
}

$files = @("docker-compose.yml", "README.md")
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "✅ File: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
    }
}

# Check Services
Write-Host "🔍 Checking Services..." -ForegroundColor Cyan

if (Test-Port -Host "127.0.0.1" -Port 8000) {
    Write-Host "✅ Backend API (port 8000)" -ForegroundColor Green
} else {
    Write-Host "❌ Backend API not running" -ForegroundColor Red
}

if (Test-Port -Host "127.0.0.1" -Port 3000) {
    Write-Host "✅ Frontend (port 3000)" -ForegroundColor Green
} else {
    Write-Host "❌ Frontend not running" -ForegroundColor Red
}

if (Test-Port -Host "127.0.0.1" -Port 5432) {
    Write-Host "✅ PostgreSQL (port 5432)" -ForegroundColor Green
} else {
    Write-Host "❌ PostgreSQL not running" -ForegroundColor Red
}

if (Test-Port -Host "127.0.0.1" -Port 27017) {
    Write-Host "✅ MongoDB (port 27017)" -ForegroundColor Green
} else {
    Write-Host "❌ MongoDB not running" -ForegroundColor Red
}

if (Test-Port -Host "127.0.0.1" -Port 6379) {
    Write-Host "✅ Redis (port 6379)" -ForegroundColor Green
} else {
    Write-Host "❌ Redis not running" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎯 Verification Complete!" -ForegroundColor Blue
Write-Host ""
Write-Host "💡 To start all services:" -ForegroundColor Yellow
Write-Host "   docker-compose up -d" -ForegroundColor White
Write-Host ""
Write-Host "💡 To build Go tools:" -ForegroundColor Yellow
Write-Host "   cd backup-cli; go build" -ForegroundColor White
Write-Host "   cd logscan; go build" -ForegroundColor White
Write-Host ""
Write-Host ""