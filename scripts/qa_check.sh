#!/bin/bash

# QA Check Master Script
# Comprehensive verification of all BI Platform components (Parts 1-9)

set -e  # Exit on any error

# Configuration
PROJECT_ROOT=$(pwd)
LOG_FILE="$PROJECT_ROOT/reports/qa_check_$(date +%Y%m%d_%H%M%S).log"
REPORT_FILE="$PROJECT_ROOT/reports/qa_report_$(date +%Y%m%d_%H%M%S).md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Logging functions
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

success() {
    log "${GREEN}✓ $1${NC}"
    ((PASSED_CHECKS++))
}

error() {
    log "${RED}✗ $1${NC}"
    ((FAILED_CHECKS++))
}

warning() {
    log "${YELLOW}⚠ $1${NC}"
}

info() {
    log "${BLUE}ℹ $1${NC}"
}

check() {
    ((TOTAL_CHECKS++))
    info "Running: $1"
}

# Initialize report
init_report() {
    mkdir -p reports
    cat > "$REPORT_FILE" << EOF
# BI Platform QA Verification Report

**Generated:** $(date)
**Project:** Business Intelligence Platform
**Scope:** Parts 1-9 Full Verification

## Executive Summary

This report covers comprehensive testing and validation of all BI Platform components.

## Test Results

EOF
}

# Part 1-2: Backend & Database Verification
verify_backend() {
    log "\n${BLUE}=== PART 1-2: BACKEND & DATABASE VERIFICATION ===${NC}"
    
    check "Django project structure"
    if [ -d "bi_tool" ] && [ -f "bi_tool/manage.py" ]; then
        success "Django project structure exists"
    else
        error "Django project structure missing"
    fi
    
    check "Required Django apps"
    required_apps=("core" "analytics" "etl" "security" "pii" "dq")
    for app in "${required_apps[@]}"; do
        if [ -d "bi_tool/$app" ]; then
            success "Django app '$app' exists"
        else
            error "Django app '$app' missing"
        fi
    done
    
    check "Database models"
    if [ -f "bi_tool/analytics/models.py" ] && [ -f "bi_tool/security/models.py" ]; then
        success "Core database models exist"
    else
        error "Database models missing"
    fi
    
    check "API endpoints"
    if [ -f "bi_tool/api/urls.py" ] && [ -f "bi_tool/api/views.py" ]; then
        success "API endpoints defined"
    else
        error "API endpoints missing"
    fi
    
    check "Django settings configuration"
    if [ -f "bi_tool/bi_tool/settings.py" ]; then
        success "Django settings exist"
    else
        error "Django settings missing"
    fi
}

# Part 3-4: RBAC & Multi-Tenant Verification
verify_rbac() {
    log "\n${BLUE}=== PART 3-4: RBAC & MULTI-TENANT VERIFICATION ===${NC}"
    
    check "Security models for RBAC"
    if [ -f "bi_tool/security/models.py" ]; then
        if grep -q "class.*Role\|class.*UserProfile" "bi_tool/security/models.py"; then
            success "RBAC models defined"
        else
            error "RBAC models not found in security/models.py"
        fi
    else
        error "Security models file missing"
    fi
    
    check "Permission classes"
    if [ -f "bi_tool/security/permissions.py" ] || [ -f "bi_tool/core/permissions.py" ]; then
        success "Permission classes exist"
    else
        error "Permission classes missing"
    fi
    
    check "Multi-tenant support"
    if grep -r "branch\|tenant" bi_tool/*/models.py 2>/dev/null; then
        success "Multi-tenant models found"
    else
        warning "Multi-tenant support not clearly implemented"
    fi
}

# Part 5-6: ETL & Analytics Verification
verify_etl() {
    log "\n${BLUE}=== PART 5-6: ETL & ANALYTICS VERIFICATION ===${NC}"
    
    check "ETL models and tasks"
    if [ -f "bi_tool/etl/models.py" ] && [ -f "bi_tool/etl/tasks.py" ]; then
        success "ETL components exist"
    else
        error "ETL components missing"
    fi
    
    check "Analytics models"
    if [ -f "bi_tool/analytics/models.py" ]; then
        success "Analytics models exist"
    else
        error "Analytics models missing"
    fi
    
    check "Data quality checks"
    if [ -f "bi_tool/dq/models.py" ] && [ -f "bi_tool/dq/tasks.py" ]; then
        success "Data quality components exist"
    else
        error "Data quality components missing"
    fi
    
    check "Celery configuration"
    if [ -f "bi_tool/bi_tool/celery.py" ]; then
        success "Celery configuration exists"
    else
        warning "Celery configuration missing"
    fi
}

# Part 7: Visualization & Dashboards Verification
verify_frontend() {
    log "\n${BLUE}=== PART 7: VISUALIZATION & DASHBOARDS VERIFICATION ===${NC}"
    
    check "Frontend project structure"
    if [ -d "bi-frontend" ] && [ -f "bi-frontend/package.json" ]; then
        success "Frontend project exists"
    else
        error "Frontend project missing"
    fi
    
    check "React components"
    if [ -d "bi-frontend/src/components" ]; then
        success "React components directory exists"
    else
        error "React components missing"
    fi
    
    check "Chart components"
    if [ -d "bi-frontend/src/charts" ]; then
        success "Chart components exist"
    else
        warning "Chart components directory missing"
    fi
    
    check "Dashboard pages"
    if [ -d "bi-frontend/src/pages" ]; then
        success "Dashboard pages exist"
    else
        error "Dashboard pages missing"
    fi
}

# Part 8: Security & Compliance Verification
verify_security() {
    log "\n${BLUE}=== PART 8: SECURITY & COMPLIANCE VERIFICATION ===${NC}"
    
    check "Security app implementation"
    if [ -f "bi_tool/security/auth.py" ] && [ -f "bi_tool/security/audit.py" ]; then
        success "Security components implemented"
    else
        error "Security components missing"
    fi
    
    check "PII handling"
    if [ -f "bi_tool/pii/models.py" ] && [ -f "bi_tool/pii/encryption.py" ]; then
        success "PII handling components exist"
    else
        error "PII handling missing"
    fi
    
    check "DSAR handler"
    if [ -f "ops/dsar.py" ]; then
        success "DSAR handler implemented"
    else
        error "DSAR handler missing"
    fi
    
    check "Audit logging"
    if grep -r "audit\|logging" bi_tool/security/ 2>/dev/null; then
        success "Audit logging implemented"
    else
        warning "Audit logging not clearly implemented"
    fi
}

# Part 9: Ops & Incident Response Verification
verify_operations() {
    log "\n${BLUE}=== PART 9: OPERATIONS & INCIDENT RESPONSE VERIFICATION ===${NC}"
    
    check "Backup CLI tool"
    if [ -f "backup-cli/main.go" ] && [ -f "backup-cli/go.mod" ]; then
        success "Backup CLI implemented"
    else
        error "Backup CLI missing"
    fi
    
    check "Log scan tool"
    if [ -f "logscan/main.go" ] && [ -f "logscan/go.mod" ]; then
        success "Log scan tool implemented"
    else
        error "Log scan tool missing"
    fi
    
    check "Operational runbooks"
    runbooks=("incident_response.md" "backup_restore.md" "dsar.md" "alerts.md")
    missing_runbooks=()
    for runbook in "${runbooks[@]}"; do
        if [ ! -f "docs/runbooks/$runbook" ]; then
            missing_runbooks+=("$runbook")
        fi
    done
    
    if [ ${#missing_runbooks[@]} -eq 0 ]; then
        success "All operational runbooks exist"
    else
        error "Missing runbooks: ${missing_runbooks[*]}"
    fi
    
    check "Monitoring configuration"
    if [ -f "monitoring/alerts.yaml" ]; then
        success "Prometheus alerts configured"
    else
        error "Prometheus alerts missing"
    fi
}

# Docker & Kubernetes Verification
verify_deployment() {
    log "\n${BLUE}=== DEPLOYMENT & INFRASTRUCTURE VERIFICATION ===${NC}"
    
    check "Docker configuration"
    dockerfiles=("bi_tool/Dockerfile" "bi-frontend/Dockerfile")
    for dockerfile in "${dockerfiles[@]}"; do
        if [ -f "$dockerfile" ]; then
            success "Dockerfile exists: $dockerfile"
        else
            error "Missing Dockerfile: $dockerfile"
        fi
    done
    
    check "Docker Compose"
    if [ -f "docker-compose.yml" ]; then
        success "Docker Compose configuration exists"
    else
        error "Docker Compose configuration missing"
    fi
    
    check "CI/CD Pipeline"
    if [ -f ".github/workflows/ci-cd.yml" ]; then
        success "GitHub Actions workflow exists"
    else
        error "CI/CD pipeline missing"
    fi
}

# Documentation Verification
verify_documentation() {
    log "\n${BLUE}=== DOCUMENTATION VERIFICATION ===${NC}"
    
    check "Core documentation"
    docs=("README.md" "BUSINESS_VALUE.md" "CONTRIBUTING.md")
    for doc in "${docs[@]}"; do
        if [ -f "$doc" ]; then
            success "Documentation exists: $doc"
        else
            error "Missing documentation: $doc"
        fi
    done
    
    check "Technical documentation"
    tech_docs=("bi_tool/API_DOCUMENTATION.md" "bi_tool/ANALYTICS_MODELS.md")
    for doc in "${tech_docs[@]}"; do
        if [ -f "$doc" ]; then
            success "Technical doc exists: $(basename $doc)"
        else
            warning "Missing technical doc: $(basename $doc)"
        fi
    done
    
    check "Templates"
    if [ -d "docs/templates" ]; then
        success "Template directory exists"
    else
        error "Template directory missing"
    fi
}

# Run Python tests if available
run_python_tests() {
    log "\n${BLUE}=== PYTHON TESTS EXECUTION ===${NC}"
    
    check "Python test execution"
    cd bi_tool
    
    if command -v python &> /dev/null; then
        if python -m pytest --version &> /dev/null; then
            info "Running pytest..."
            if python -m pytest tests/ -v --tb=short 2>&1 | tee -a "$LOG_FILE"; then
                success "Python tests completed"
            else
                error "Python tests failed"
            fi
        else
            warning "pytest not available, skipping Python tests"
        fi
    else
        warning "Python not available, skipping Python tests"
    fi
    
    cd ..
}

# Run Go tests if available
run_go_tests() {
    log "\n${BLUE}=== GO TESTS EXECUTION ===${NC}"
    
    if command -v go &> /dev/null; then
        # Test backup-cli
        check "backup-cli Go tests"
        cd backup-cli
        if go test ./... 2>&1 | tee -a "$LOG_FILE"; then
            success "backup-cli tests passed"
        else
            error "backup-cli tests failed"
        fi
        cd ..
        
        # Test logscan
        check "logscan Go tests"
        cd logscan
        if go test ./... 2>&1 | tee -a "$LOG_FILE"; then
            success "logscan tests passed"
        else
            error "logscan tests failed"
        fi
        cd ..
    else
        warning "Go not available, skipping Go tests"
    fi
}

# Security scan
run_security_scan() {
    log "\n${BLUE}=== SECURITY SCANNING ===${NC}"
    
    check "Dependency vulnerability scan"
    
    # Python security scan
    cd bi_tool
    if command -v safety &> /dev/null; then
        if safety check 2>&1 | tee -a "$LOG_FILE"; then
            success "Python dependencies security scan passed"
        else
            warning "Python dependencies have security issues"
        fi
    else
        info "safety not installed, skipping Python security scan"
    fi
    cd ..
    
    # Node.js security scan
    cd bi-frontend
    if command -v npm &> /dev/null && [ -f "package.json" ]; then
        if npm audit 2>&1 | tee -a "$LOG_FILE"; then
            success "Node.js dependencies security scan passed"
        else
            warning "Node.js dependencies have security issues"
        fi
    else
        info "npm not available or package.json missing, skipping Node.js security scan"
    fi
    cd ..
    
    # Check for hardcoded secrets
    check "Hardcoded secrets scan"
    if command -v grep &> /dev/null; then
        secrets_found=false
        secret_patterns=("password.*=" "api_key.*=" "secret.*=" "token.*=" "key.*=.*['\"][a-zA-Z0-9]{20}")
        
        for pattern in "${secret_patterns[@]}"; do
            if grep -r -i "$pattern" --exclude-dir=node_modules --exclude-dir=.git --exclude="*.log" . 2>/dev/null; then
                secrets_found=true
            fi
        done
        
        if [ "$secrets_found" = false ]; then
            success "No obvious hardcoded secrets found"
        else
            error "Potential hardcoded secrets detected"
        fi
    fi
}

# Generate final report
generate_final_report() {
    log "\n${BLUE}=== GENERATING FINAL REPORT ===${NC}"
    
    cat >> "$REPORT_FILE" << EOF

## Summary

- **Total Checks:** $TOTAL_CHECKS
- **Passed:** $PASSED_CHECKS
- **Failed:** $FAILED_CHECKS
- **Success Rate:** $((PASSED_CHECKS * 100 / TOTAL_CHECKS))%

## Status by Component

| Component | Status |
|-----------|--------|
| Backend & Database | $([ $FAILED_CHECKS -eq 0 ] && echo "✅ PASS" || echo "❌ NEEDS WORK") |
| RBAC & Multi-Tenant | $([ $FAILED_CHECKS -eq 0 ] && echo "✅ PASS" || echo "❌ NEEDS WORK") |
| ETL & Analytics | $([ $FAILED_CHECKS -eq 0 ] && echo "✅ PASS" || echo "❌ NEEDS WORK") |
| Frontend & Dashboards | $([ $FAILED_CHECKS -eq 0 ] && echo "✅ PASS" || echo "❌ NEEDS WORK") |
| Security & Compliance | $([ $FAILED_CHECKS -eq 0 ] && echo "✅ PASS" || echo "❌ NEEDS WORK") |
| Operations & IR | $([ $FAILED_CHECKS -eq 0 ] && echo "✅ PASS" || echo "❌ NEEDS WORK") |
| Deployment | $([ $FAILED_CHECKS -eq 0 ] && echo "✅ PASS" || echo "❌ NEEDS WORK") |
| Documentation | $([ $FAILED_CHECKS -eq 0 ] && echo "✅ PASS" || echo "❌ NEEDS WORK") |

## Recommendations

EOF

    if [ $FAILED_CHECKS -gt 0 ]; then
        cat >> "$REPORT_FILE" << EOF
### Critical Issues Found

The following issues should be addressed before production deployment:

1. Review failed checks in the detailed log: \`$LOG_FILE\`
2. Implement missing components identified in verification
3. Complete security hardening for any flagged items
4. Ensure all tests pass before deployment

EOF
    else
        cat >> "$REPORT_FILE" << EOF
### All Checks Passed ✅

The BI Platform appears to be ready for production deployment. All critical components are implemented and verified.

EOF
    fi

    cat >> "$REPORT_FILE" << EOF
## Next Steps

1. **Manual Testing:** Perform manual UI testing and user acceptance testing
2. **Load Testing:** Run performance tests under expected load
3. **Security Review:** Conduct penetration testing and security audit
4. **Documentation Review:** Ensure all documentation is current and complete
5. **Deployment Planning:** Prepare production deployment checklist

---
*Report generated by qa_check.sh - $(date)*
EOF

    success "Final report generated: $REPORT_FILE"
}

# Main execution
main() {
    log "${GREEN}Starting BI Platform QA Verification${NC}"
    log "Log file: $LOG_FILE"
    log "Report file: $REPORT_FILE"
    
    init_report
    
    verify_backend
    verify_rbac
    verify_etl
    verify_frontend
    verify_security
    verify_operations
    verify_deployment
    verify_documentation
    
    run_python_tests
    run_go_tests
    run_security_scan
    
    generate_final_report
    
    log "\n${GREEN}=== QA VERIFICATION COMPLETE ===${NC}"
    log "Total Checks: $TOTAL_CHECKS"
    log "Passed: ${GREEN}$PASSED_CHECKS${NC}"
    log "Failed: ${RED}$FAILED_CHECKS${NC}"
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        log "\n${GREEN}🎉 All checks passed! The BI Platform is ready for deployment.${NC}"
        exit 0
    else
        log "\n${YELLOW}⚠️  Some checks failed. Review the report and logs before proceeding.${NC}"
        exit 1
    fi
}

# Execute main function
main "$@"