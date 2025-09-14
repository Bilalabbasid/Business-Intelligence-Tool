# Business Intelligence Tool Verification Script - PowerShell Version
# Run this script to verify your BI Tool setup

Write-Host "🚀 Verifying Business Intelligence Tool Setup..." -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue

# Function to test TCP connection
function Test-Port {
    param([string]$Server, [int]$Port)
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.ReceiveTimeout = 1000
        $tcpClient.SendTimeout = 1000
        $tcpClient.Connect($Server, $Port)
        $tcpClient.Close()
        return $true
    }
    catch {
        return $false
    }
}

# Function to check HTTP endpoint
function Test-Endpoint {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

Write-Host "🔍 Checking Services..." -ForegroundColor Cyan

# Check Backend (Django)
Write-Host "🔍 Checking Django Backend..." -ForegroundColor Cyan
if (Test-Port -Server "127.0.0.1" -Port 8000) {
    if (Test-Endpoint -Url "http://127.0.0.1:8000/api/health/") {
        Write-Host "✅ Backend API running and healthy" -ForegroundColor Green
        $backendRunning = $true
    } else {
        Write-Host "⚠️ Backend running but not responding properly" -ForegroundColor Yellow
        $backendRunning = $false
    }
} else {
    Write-Host "❌ Backend API not running on port 8000" -ForegroundColor Red
    $backendRunning = $false
}

# Check Database Services
Write-Host "🔍 Checking Database Services..." -ForegroundColor Cyan

# PostgreSQL
if (Test-Port -Server "127.0.0.1" -Port 5432) {
    Write-Host "✅ PostgreSQL running on port 5432" -ForegroundColor Green
} else {
    Write-Host "❌ PostgreSQL not running" -ForegroundColor Red
}

# MongoDB
if (Test-Port -Server "127.0.0.1" -Port 27017) {
    Write-Host "✅ MongoDB running on port 27017" -ForegroundColor Green
} else {
    Write-Host "❌ MongoDB not running" -ForegroundColor Red
}

# Redis
if (Test-Port -Server "127.0.0.1" -Port 6379) {
    Write-Host "✅ Redis running on port 6379" -ForegroundColor Green
} else {
    Write-Host "❌ Redis not running" -ForegroundColor Red
}

# Check API Endpoints
if ($backendRunning) {
    Write-Host "🔍 Checking API Endpoints..." -ForegroundColor Cyan
    
    $endpoints = @("health", "auth/user", "v1/analytics/sales", "v1/branches")
    
    foreach ($endpoint in $endpoints) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/$endpoint/" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            Write-Host "✅ API /api/$endpoint/ accessible (HTTP $($response.StatusCode))" -ForegroundColor Green
        }
        catch {
            if ($_.Exception.Response.StatusCode -eq 401) {
                Write-Host "✅ API /api/$endpoint/ accessible (HTTP 401 - Auth required)" -ForegroundColor Green
            } else {
                Write-Host "❌ API /api/$endpoint/ failed" -ForegroundColor Red
            }
        }
    }
} else {
    Write-Host "⚠️ Skipping API endpoint checks - backend not running" -ForegroundColor Yellow
}

# Check Frontend
Write-Host "🔍 Checking Frontend..." -ForegroundColor Cyan
if (Test-Port -Server "127.0.0.1" -Port 3000) {
    if (Test-Endpoint -Url "http://127.0.0.1:3000") {
        Write-Host "✅ Frontend running and serving content" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Frontend running but not serving expected content" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Frontend not running on port 3000" -ForegroundColor Red
}

# Check Go Tools
Write-Host "🔍 Checking Go Tools..." -ForegroundColor Cyan

if (Test-Path "backup-cli\backup-cli.exe" -PathType Leaf) {
    Write-Host "✅ Backup CLI tool built" -ForegroundColor Green
} else {
    Write-Host "❌ Backup CLI tool not built" -ForegroundColor Red
}

if (Test-Path "logscan\logscan.exe" -PathType Leaf) {
    Write-Host "✅ Logscan tool built" -ForegroundColor Green
} else {
    Write-Host "❌ Logscan tool not built" -ForegroundColor Red
}

# Check Project Structure
Write-Host "🔍 Checking Project Structure..." -ForegroundColor Cyan

$requiredDirs = @("bi_tool", "bi-frontend", "backup-cli", "logscan", "docs", "scripts")
foreach ($dir in $requiredDirs) {
    if (Test-Path $dir -PathType Container) {
        Write-Host "✅ Directory $dir exists" -ForegroundColor Green
    } else {
        Write-Host "❌ Directory $dir missing" -ForegroundColor Red
    }
}

$requiredFiles = @("docker-compose.yml", "README.md", ".github\workflows\ci-cd.yml")
foreach ($file in $requiredFiles) {
    if (Test-Path $file -PathType Leaf) {
        Write-Host "✅ File $file exists" -ForegroundColor Green
    } else {
        Write-Host "❌ File $file missing" -ForegroundColor Red
    }
}

# Check Python Environment
Write-Host "🔍 Checking Python Environment..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python available: $pythonVersion" -ForegroundColor Green
    
    if ($env:VIRTUAL_ENV) {
        Write-Host "✅ Virtual environment active: $env:VIRTUAL_ENV" -ForegroundColor Green
    } else {
        Write-Host "⚠️ No virtual environment detected" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Python not available" -ForegroundColor Red
}

# Check Node.js Environment
Write-Host "🔍 Checking Node.js Environment..." -ForegroundColor Cyan
try {
    $nodeVersion = node --version 2>&1
    $npmVersion = npm --version 2>&1
    Write-Host "✅ Node.js available: $nodeVersion" -ForegroundColor Green
    Write-Host "✅ npm available: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js not available" -ForegroundColor Red
}

# Check Docker
Write-Host "🔍 Checking Docker..." -ForegroundColor Cyan
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "✅ Docker available: $dockerVersion" -ForegroundColor Green
    
    try {
        docker info | Out-Null
        Write-Host "✅ Docker daemon running" -ForegroundColor Green
    } catch {
        Write-Host "❌ Docker daemon not running" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Docker not available" -ForegroundColor Red
}

# Check Git
Write-Host "🔍 Checking Git Repository..." -ForegroundColor Cyan
try {
    git status | Out-Null
    Write-Host "✅ Git repository initialized" -ForegroundColor Green
    
    $gitStatus = git status --porcelain
    if ([string]::IsNullOrEmpty($gitStatus)) {
        Write-Host "✅ No uncommitted changes" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Uncommitted changes detected" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Not a git repository or Git not available" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Blue
Write-Host "🎯 Verification Complete!" -ForegroundColor Blue
Write-Host ""

Write-Host "📊 Summary:" -ForegroundColor Blue
Write-Host "- Backend API: $(if ($backendRunning) { Write-Host "Running" -ForegroundColor Green -NoNewline } else { Write-Host "Not Running" -ForegroundColor Red -NoNewline })"
Write-Host ""
Write-Host "- Database Services: Check individual results above"
Write-Host "- Frontend: Check results above"
Write-Host "- Go Tools: Check build status above"
Write-Host "- Development Environment: Check Python/Node.js/Docker status above"

Write-Host ""
Write-Host "💡 Next Steps:" -ForegroundColor Yellow
Write-Host "1. If services are not running, start them with: docker-compose up -d"
Write-Host "2. If Go tools not built, run: cd backup-cli; go build; cd ../logscan; go build"
Write-Host "3. If frontend issues, run: cd bi-frontend; npm install; npm run dev"
Write-Host "4. If backend issues, check Django logs and database connections"
Write-Host "5. If Docker not available, install Docker Desktop from docker.com"