#!/bin/bash

echo "🚀 Verifying Business Intelligence Tool Setup..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if service is running
check_service() {
    local service_name=$1
    local port=$2
    local endpoint=$3
    
    echo -e "${BLUE}🔍 Checking $service_name...${NC}"
    
    if nc -z localhost $port 2>/dev/null; then
        if [ -n "$endpoint" ]; then
            if curl -s "$endpoint" | grep -q "ok\|healthy\|success"; then
                echo -e "${GREEN}✅ $service_name running and responding${NC}"
                return 0
            else
                echo -e "${YELLOW}⚠️ $service_name running but not responding properly${NC}"
                return 1
            fi
        else
            echo -e "${GREEN}✅ $service_name running on port $port${NC}"
            return 0
        fi
    else
        echo -e "${RED}❌ $service_name not running on port $port${NC}"
        return 1
    fi
}

# 1. Check Backend (Django)
echo -e "${BLUE}🔍 Checking Django Backend...${NC}"
if curl -s http://127.0.0.1:8000/api/health/ | grep -q "healthy\|ok"; then
    echo -e "${GREEN}✅ Backend API running and healthy${NC}"
    backend_running=true
else
    echo -e "${RED}❌ Backend API not responding${NC}"
    backend_running=false
fi

# 2. Check Database Services
echo -e "${BLUE}🔍 Checking Database Services...${NC}"

# PostgreSQL
if nc -z localhost 5432 2>/dev/null; then
    echo -e "${GREEN}✅ PostgreSQL running on port 5432${NC}"
else
    echo -e "${RED}❌ PostgreSQL not running${NC}"
fi

# MongoDB
if nc -z localhost 27017 2>/dev/null; then
    echo -e "${GREEN}✅ MongoDB running on port 27017${NC}"
    # Check MongoDB connection
    if command -v mongo >/dev/null 2>&1; then
        if mongo --eval "db.stats()" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ MongoDB connection successful${NC}"
        else
            echo -e "${YELLOW}⚠️ MongoDB running but connection failed${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️ mongo command not available, cannot test connection${NC}"
    fi
else
    echo -e "${RED}❌ MongoDB not running${NC}"
fi

# Redis
if nc -z localhost 6379 2>/dev/null; then
    echo -e "${GREEN}✅ Redis running on port 6379${NC}"
else
    echo -e "${RED}❌ Redis not running${NC}"
fi

# 3. Check API Endpoints
if [ "$backend_running" = true ]; then
    echo -e "${BLUE}🔍 Checking API Endpoints...${NC}"
    
    endpoints=("health" "auth/user" "v1/analytics/sales" "v1/branches")
    
    for endpoint in "${endpoints[@]}"; do
        response=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/$endpoint/)
        if [ "$response" = "200" ] || [ "$response" = "401" ]; then
            echo -e "${GREEN}✅ API /api/$endpoint/ accessible (HTTP $response)${NC}"
        else
            echo -e "${RED}❌ API /api/$endpoint/ failed (HTTP $response)${NC}"
        fi
    done
else
    echo -e "${YELLOW}⚠️ Skipping API endpoint checks - backend not running${NC}"
fi

# 4. Check Frontend
echo -e "${BLUE}🔍 Checking Frontend...${NC}"
if nc -z localhost 3000 2>/dev/null; then
    if curl -s http://127.0.0.1:3000 | grep -q "<html\|<div"; then
        echo -e "${GREEN}✅ Frontend running and serving content${NC}"
    else
        echo -e "${YELLOW}⚠️ Frontend running but not serving expected content${NC}"
    fi
else
    echo -e "${RED}❌ Frontend not running on port 3000${NC}"
fi

# 5. Check Go Tools
echo -e "${BLUE}🔍 Checking Go Tools...${NC}"

if [ -f "backup-cli/backup-cli" ] || [ -f "backup-cli/backup-cli.exe" ]; then
    echo -e "${GREEN}✅ Backup CLI tool built${NC}"
else
    echo -e "${RED}❌ Backup CLI tool not built${NC}"
fi

if [ -f "logscan/logscan" ] || [ -f "logscan/logscan.exe" ]; then
    echo -e "${GREEN}✅ Logscan tool built${NC}"
else
    echo -e "${RED}❌ Logscan tool not built${NC}"
fi

# 6. Check Project Structure
echo -e "${BLUE}🔍 Checking Project Structure...${NC}"

required_dirs=("bi_tool" "bi-frontend" "backup-cli" "logscan" "docs" "scripts")
for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ Directory $dir exists${NC}"
    else
        echo -e "${RED}❌ Directory $dir missing${NC}"
    fi
done

required_files=("docker-compose.yml" "README.md" ".github/workflows/ci-cd.yml")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ File $file exists${NC}"
    else
        echo -e "${RED}❌ File $file missing${NC}"
    fi
done

# 7. Check Python Environment
echo -e "${BLUE}🔍 Checking Python Environment...${NC}"
if command -v python >/dev/null 2>&1; then
    python_version=$(python --version 2>&1)
    echo -e "${GREEN}✅ Python available: $python_version${NC}"
    
    # Check if in virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        echo -e "${GREEN}✅ Virtual environment active: $VIRTUAL_ENV${NC}"
    else
        echo -e "${YELLOW}⚠️ No virtual environment detected${NC}"
    fi
else
    echo -e "${RED}❌ Python not available${NC}"
fi

# 8. Check Node.js Environment
echo -e "${BLUE}🔍 Checking Node.js Environment...${NC}"
if command -v node >/dev/null 2>&1; then
    node_version=$(node --version)
    npm_version=$(npm --version)
    echo -e "${GREEN}✅ Node.js available: $node_version${NC}"
    echo -e "${GREEN}✅ npm available: $npm_version${NC}"
else
    echo -e "${RED}❌ Node.js not available${NC}"
fi

# 9. Check Docker
echo -e "${BLUE}🔍 Checking Docker...${NC}"
if command -v docker >/dev/null 2>&1; then
    docker_version=$(docker --version)
    echo -e "${GREEN}✅ Docker available: $docker_version${NC}"
    
    if docker info >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Docker daemon running${NC}"
    else
        echo -e "${RED}❌ Docker daemon not running${NC}"
    fi
else
    echo -e "${RED}❌ Docker not available${NC}"
fi

# 10. Check Git
echo -e "${BLUE}🔍 Checking Git Repository...${NC}"
if git status >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Git repository initialized${NC}"
    
    # Check for uncommitted changes
    if git diff-index --quiet HEAD --; then
        echo -e "${GREEN}✅ No uncommitted changes${NC}"
    else
        echo -e "${YELLOW}⚠️ Uncommitted changes detected${NC}"
    fi
else
    echo -e "${RED}❌ Not a git repository${NC}"
fi

echo ""
echo "================================================"
echo -e "${BLUE}🎯 Verification Complete!${NC}"
echo ""

# Summary
echo -e "${BLUE}📊 Summary:${NC}"
echo "- Backend API: $([ "$backend_running" = true ] && echo -e "${GREEN}Running${NC}" || echo -e "${RED}Not Running${NC}")"
echo "- Database Services: Check individual results above"
echo "- Frontend: Check results above"
echo "- Go Tools: Check build status above"
echo "- Development Environment: Check Python/Node.js/Docker status above"

echo ""
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo "1. If services are not running, start them with: docker-compose up -d"
echo "2. If Go tools not built, run: cd backup-cli && go build && cd ../logscan && go build"
echo "3. If frontend issues, run: cd bi-frontend && npm install && npm run dev"
echo "4. If backend issues, check Django logs and database connections"

exit 0