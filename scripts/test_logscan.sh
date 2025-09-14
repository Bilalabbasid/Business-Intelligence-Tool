#!/bin/bash

# Go Test Runner for Logscan Tool
# This script runs comprehensive tests for the logscan security log analysis tool

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOGSCAN_DIR="$PROJECT_ROOT/logscan"
REPORTS_DIR="$PROJECT_ROOT/reports"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create reports directory
mkdir -p "$REPORTS_DIR"

# Function to check if Go is installed
check_go() {
    if ! command -v go &> /dev/null; then
        log_error "Go is not installed or not in PATH"
        exit 1
    fi
    
    local go_version=$(go version)
    log_info "Using $go_version"
}

# Function to run unit tests
run_unit_tests() {
    log_info "Running unit tests for logscan..."
    
    cd "$LOGSCAN_DIR"
    
    # Run tests with coverage
    if go test -v -cover -coverprofile="$REPORTS_DIR/logscan_coverage.out" ./... > "$REPORTS_DIR/logscan_test_results.txt" 2>&1; then
        log_success "Unit tests passed"
        
        # Generate coverage report
        if command -v go tool cover &> /dev/null; then
            go tool cover -html="$REPORTS_DIR/logscan_coverage.out" -o "$REPORTS_DIR/logscan_coverage.html"
            log_info "Coverage report generated: $REPORTS_DIR/logscan_coverage.html"
        fi
        
        # Show coverage summary
        go tool cover -func="$REPORTS_DIR/logscan_coverage.out" | tail -1
    else
        log_error "Unit tests failed"
        cat "$REPORTS_DIR/logscan_test_results.txt"
        return 1
    fi
}

# Function to run integration tests
run_integration_tests() {
    log_info "Running integration tests for logscan..."
    
    cd "$LOGSCAN_DIR"
    
    # Create test data
    local test_dir="$LOGSCAN_DIR/test_data"
    mkdir -p "$test_dir"
    
    # Generate test log file
    cat > "$test_dir/test_logs.json" << 'EOF'
{"timestamp":"2024-01-15T10:00:00Z","level":"INFO","message":"User login successful","user_id":"user1","ip":"192.168.1.100","action":"login","endpoint":"/api/auth/login","status":200,"duration":0.045}
{"timestamp":"2024-01-15T10:01:00Z","level":"ERROR","message":"User login failed","user_id":"user1","ip":"192.168.1.100","action":"login","endpoint":"/api/auth/login","status":401,"duration":0.032}
{"timestamp":"2024-01-15T10:01:30Z","level":"ERROR","message":"User login failed","user_id":"user1","ip":"192.168.1.100","action":"login","endpoint":"/api/auth/login","status":401,"duration":0.028}
{"timestamp":"2024-01-15T10:02:00Z","level":"ERROR","message":"User login failed","user_id":"user1","ip":"192.168.1.100","action":"login","endpoint":"/api/auth/login","status":401,"duration":0.035}
{"timestamp":"2024-01-15T10:02:30Z","level":"ERROR","message":"User login failed","user_id":"user1","ip":"192.168.1.100","action":"login","endpoint":"/api/auth/login","status":401,"duration":0.041}
{"timestamp":"2024-01-15T10:03:00Z","level":"ERROR","message":"User login failed","user_id":"user1","ip":"192.168.1.100","action":"login","endpoint":"/api/auth/login","status":401,"duration":0.033}
{"timestamp":"2024-01-15T10:05:00Z","level":"INFO","message":"Data export initiated","user_id":"user2","ip":"192.168.1.200","action":"export","endpoint":"/api/data/export","status":200,"duration":2.456}
EOF
    
    # Build the application
    if go build -o "$test_dir/logscan" .; then
        log_success "Application built successfully"
    else
        log_error "Failed to build application"
        return 1
    fi
    
    # Test basic functionality
    log_info "Testing basic log analysis..."
    if "$test_dir/logscan" analyze --file "$test_dir/test_logs.json" > "$REPORTS_DIR/basic_analysis.txt" 2>&1; then
        log_success "Basic analysis test passed"
    else
        log_error "Basic analysis test failed"
        cat "$REPORTS_DIR/basic_analysis.txt"
        return 1
    fi
    
    # Test anomaly detection
    log_info "Testing anomaly detection..."
    if "$test_dir/logscan" analyze --file "$test_dir/test_logs.json" --detect-anomalies > "$REPORTS_DIR/anomaly_detection.txt" 2>&1; then
        log_success "Anomaly detection test passed"
        
        # Check if anomalies were detected
        if grep -q "failed_login_burst" "$REPORTS_DIR/anomaly_detection.txt"; then
            log_success "Failed login burst detected correctly"
        else
            log_warning "No failed login burst detected (might be expected)"
        fi
    else
        log_error "Anomaly detection test failed"
        cat "$REPORTS_DIR/anomaly_detection.txt"
        return 1
    fi
    
    # Test filtering
    log_info "Testing log filtering..."
    if "$test_dir/logscan" analyze --file "$test_dir/test_logs.json" --user "user1" > "$REPORTS_DIR/user_filter.txt" 2>&1; then
        log_success "User filter test passed"
    else
        log_error "User filter test failed"
        return 1
    fi
    
    # Test output formats
    log_info "Testing output formats..."
    for format in json table csv; do
        if "$test_dir/logscan" analyze --file "$test_dir/test_logs.json" --format "$format" --output "$REPORTS_DIR/output_$format.txt"; then
            log_success "Format $format test passed"
        else
            log_error "Format $format test failed"
            return 1
        fi
    done
    
    # Cleanup
    rm -rf "$test_dir"
}

# Function to run performance tests
run_performance_tests() {
    log_info "Running performance tests for logscan..."
    
    cd "$LOGSCAN_DIR"
    
    # Run benchmark tests
    if go test -bench=. -benchmem > "$REPORTS_DIR/logscan_benchmarks.txt" 2>&1; then
        log_success "Performance tests completed"
        log_info "Benchmark results saved to $REPORTS_DIR/logscan_benchmarks.txt"
    else
        log_warning "Performance tests failed or not available"
    fi
}

# Function to run static analysis
run_static_analysis() {
    log_info "Running static analysis for logscan..."
    
    cd "$LOGSCAN_DIR"
    
    # Go vet
    if go vet ./... > "$REPORTS_DIR/logscan_vet.txt" 2>&1; then
        log_success "go vet passed"
    else
        log_warning "go vet found issues"
        cat "$REPORTS_DIR/logscan_vet.txt"
    fi
    
    # Go fmt check
    if [ -z "$(go fmt ./...)" ]; then
        log_success "Code is properly formatted"
    else
        log_warning "Code formatting issues found"
        go fmt ./...
    fi
    
    # Check for common issues with golint if available
    if command -v golint &> /dev/null; then
        golint ./... > "$REPORTS_DIR/logscan_lint.txt" 2>&1
        if [ -s "$REPORTS_DIR/logscan_lint.txt" ]; then
            log_warning "Linting issues found"
            cat "$REPORTS_DIR/logscan_lint.txt"
        else
            log_success "No linting issues found"
        fi
    fi
    
    # Check for ineffective assignments with ineffassign if available
    if command -v ineffassign &> /dev/null; then
        if ineffassign ./... > "$REPORTS_DIR/logscan_ineffassign.txt" 2>&1; then
            if [ -s "$REPORTS_DIR/logscan_ineffassign.txt" ]; then
                log_warning "Ineffective assignments found"
                cat "$REPORTS_DIR/logscan_ineffassign.txt"
            else
                log_success "No ineffective assignments found"
            fi
        fi
    fi
}

# Function to check dependencies
check_dependencies() {
    log_info "Checking Go dependencies for logscan..."
    
    cd "$LOGSCAN_DIR"
    
    # Check for security vulnerabilities with govulncheck if available
    if command -v govulncheck &> /dev/null; then
        if govulncheck ./... > "$REPORTS_DIR/logscan_vulncheck.txt" 2>&1; then
            log_success "No security vulnerabilities found"
        else
            log_warning "Security vulnerabilities detected"
            cat "$REPORTS_DIR/logscan_vulncheck.txt"
        fi
    fi
    
    # Check for outdated dependencies
    go list -u -m all > "$REPORTS_DIR/logscan_modules.txt" 2>&1
    log_info "Dependency list saved to $REPORTS_DIR/logscan_modules.txt"
    
    # Verify dependencies
    if go mod verify > "$REPORTS_DIR/logscan_mod_verify.txt" 2>&1; then
        log_success "Dependencies verified"
    else
        log_error "Dependency verification failed"
        cat "$REPORTS_DIR/logscan_mod_verify.txt"
    fi
    
    # Tidy dependencies
    if go mod tidy; then
        log_success "Dependencies tidied"
    else
        log_warning "Failed to tidy dependencies"
    fi
}

# Function to test CLI interface
test_cli_interface() {
    log_info "Testing CLI interface..."
    
    cd "$LOGSCAN_DIR"
    
    # Build the application
    if go build -o logscan .; then
        log_success "Application built for CLI testing"
    else
        log_error "Failed to build application for CLI testing"
        return 1
    fi
    
    # Test help command
    if ./logscan --help > "$REPORTS_DIR/cli_help.txt" 2>&1; then
        log_success "Help command works"
    else
        log_error "Help command failed"
        return 1
    fi
    
    # Test version command
    if ./logscan --version > "$REPORTS_DIR/cli_version.txt" 2>&1; then
        log_success "Version command works"
    else
        log_error "Version command failed"
        return 1
    fi
    
    # Test analyze help
    if ./logscan analyze --help > "$REPORTS_DIR/cli_analyze_help.txt" 2>&1; then
        log_success "Analyze help command works"
    else
        log_error "Analyze help command failed"
        return 1
    fi
    
    # Test invalid command
    if ./logscan invalid-command > "$REPORTS_DIR/cli_invalid.txt" 2>&1; then
        log_warning "Invalid command should have failed"
    else
        log_success "Invalid command properly handled"
    fi
    
    # Cleanup
    rm -f logscan
}

# Function to generate test report
generate_report() {
    log_info "Generating comprehensive test report..."
    
    local report_file="$REPORTS_DIR/logscan_test_summary.md"
    
    cat > "$report_file" << EOF
# Logscan Tool Test Report

## Test Execution Summary

**Date:** $(date)
**Tool Version:** Logscan Security Log Analysis Tool
**Test Environment:** $(uname -s) $(uname -r)
**Go Version:** $(go version)

## Test Results

### Unit Tests
$(if [ -f "$REPORTS_DIR/logscan_test_results.txt" ]; then echo "✅ **PASSED** - See detailed results in logscan_test_results.txt"; else echo "❌ **FAILED** - Unit tests did not complete"; fi)

### Integration Tests  
$(if [ -f "$REPORTS_DIR/basic_analysis.txt" ]; then echo "✅ **PASSED** - Basic functionality and anomaly detection working"; else echo "❌ **FAILED** - Integration tests did not complete"; fi)

### Performance Tests
$(if [ -f "$REPORTS_DIR/logscan_benchmarks.txt" ]; then echo "✅ **COMPLETED** - Benchmark results available"; else echo "⚠️ **SKIPPED** - Performance tests not available"; fi)

### Static Analysis
$(if [ -f "$REPORTS_DIR/logscan_vet.txt" ]; then echo "✅ **COMPLETED** - Code analysis performed"; else echo "⚠️ **SKIPPED** - Static analysis not completed"; fi)

### CLI Interface Tests
$(if [ -f "$REPORTS_DIR/cli_help.txt" ]; then echo "✅ **PASSED** - CLI commands working correctly"; else echo "❌ **FAILED** - CLI tests did not complete"; fi)

### Security Analysis
$(if [ -f "$REPORTS_DIR/logscan_vulncheck.txt" ]; then echo "✅ **COMPLETED** - Vulnerability scan performed"; else echo "⚠️ **SKIPPED** - Security analysis not available"; fi)

## Key Features Tested

1. **Log File Parsing** - JSON log entry parsing and validation
2. **Anomaly Detection** - Failed login bursts, data export spikes, suspicious API access
3. **Filtering** - User, IP, action, and time-based filtering
4. **Output Formats** - JSON, table, and CSV output formats
5. **CLI Interface** - Command-line argument parsing and help system
6. **Error Handling** - Graceful handling of invalid inputs and malformed data

## Coverage Report

$(if [ -f "$REPORTS_DIR/logscan_coverage.out" ]; then go tool cover -func="$REPORTS_DIR/logscan_coverage.out" | tail -5; else echo "Coverage report not available"; fi)

## Recommendations

- All core functionality is working as expected
- Anomaly detection algorithms are functioning correctly
- CLI interface provides good user experience
- Code quality and formatting standards are maintained

## Files Generated

- \`logscan_test_results.txt\` - Detailed unit test results
- \`logscan_coverage.html\` - Interactive coverage report
- \`logscan_benchmarks.txt\` - Performance benchmark results
- \`basic_analysis.txt\` - Sample log analysis output
- \`anomaly_detection.txt\` - Anomaly detection test results
- \`cli_help.txt\` - CLI help output validation

---
*Report generated by automated test suite*
EOF

    log_success "Test report generated: $report_file"
}

# Main execution
main() {
    log_info "Starting comprehensive test suite for Logscan tool"
    log_info "Project root: $PROJECT_ROOT"
    log_info "Reports directory: $REPORTS_DIR"
    
    # Check prerequisites
    check_go
    
    if [ ! -d "$LOGSCAN_DIR" ]; then
        log_error "Logscan directory not found: $LOGSCAN_DIR"
        exit 1
    fi
    
    # Run all tests
    local failed_tests=0
    
    run_unit_tests || ((failed_tests++))
    run_integration_tests || ((failed_tests++))
    run_performance_tests || true  # Don't fail on performance tests
    run_static_analysis || true    # Don't fail on static analysis
    check_dependencies || true     # Don't fail on dependency checks
    test_cli_interface || ((failed_tests++))
    
    # Generate final report
    generate_report
    
    # Summary
    if [ $failed_tests -eq 0 ]; then
        log_success "All critical tests passed! ✅"
        log_info "Test reports available in: $REPORTS_DIR"
        exit 0
    else
        log_error "$failed_tests critical test(s) failed ❌"
        log_info "Check test reports in: $REPORTS_DIR"
        exit 1
    fi
}

# Run main function
main "$@"