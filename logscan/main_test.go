package main

import (
	"testing"
	"os"
	"path/filepath"
	"encoding/json"
	"strings"
	"time"
)

// Test data structures
func createTestLogEntries() []LogEntry {
	return []LogEntry{
		{
			Timestamp: time.Now().Add(-1*time.Hour).Format(time.RFC3339),
			Level:     "INFO",
			Message:   "User login successful",
			UserID:    "user123",
			IP:        "192.168.1.100",
			Action:    "login",
			Endpoint:  "/api/auth/login",
			Status:    200,
			Duration:  0.045,
		},
		{
			Timestamp: time.Now().Add(-50*time.Minute).Format(time.RFC3339),
			Level:     "ERROR",
			Message:   "User login failed",
			UserID:    "user123",
			IP:        "192.168.1.100",
			Action:    "login",
			Endpoint:  "/api/auth/login",
			Status:    401,
			Duration:  0.032,
		},
		{
			Timestamp: time.Now().Add(-49*time.Minute).Format(time.RFC3339),
			Level:     "ERROR",
			Message:   "User login failed",
			UserID:    "user123",
			IP:        "192.168.1.100",
			Action:    "login",
			Endpoint:  "/api/auth/login",
			Status:    401,
			Duration:  0.028,
		},
		{
			Timestamp: time.Now().Add(-48*time.Minute).Format(time.RFC3339),
			Level:     "ERROR",
			Message:   "User login failed",
			UserID:    "user123",
			IP:        "192.168.1.100",
			Action:    "login",
			Endpoint:  "/api/auth/login",
			Status:    401,
			Duration:  0.035,
		},
		{
			Timestamp: time.Now().Add(-47*time.Minute).Format(time.RFC3339),
			Level:     "ERROR",
			Message:   "User login failed",
			UserID:    "user123",
			IP:        "192.168.1.100",
			Action:    "login",
			Endpoint:  "/api/auth/login",
			Status:    401,
			Duration:  0.041,
		},
		{
			Timestamp: time.Now().Add(-46*time.Minute).Format(time.RFC3339),
			Level:     "ERROR",
			Message:   "User login failed",
			UserID:    "user123",
			IP:        "192.168.1.100",
			Action:    "login",
			Endpoint:  "/api/auth/login",
			Status:    401,
			Duration:  0.033,
		},
		{
			Timestamp: time.Now().Add(-30*time.Minute).Format(time.RFC3339),
			Level:     "INFO",
			Message:   "Data export initiated",
			UserID:    "user456",
			IP:        "192.168.1.200",
			Action:    "export",
			Endpoint:  "/api/data/export",
			Status:    200,
			Duration:  2.456,
		},
	}
}

func createTestLogFile(entries []LogEntry) (string, error) {
	tmpFile, err := os.CreateTemp("", "test-logs-*.json")
	if err != nil {
		return "", err
	}
	defer tmpFile.Close()

	encoder := json.NewEncoder(tmpFile)
	for _, entry := range entries {
		if err := encoder.Encode(entry); err != nil {
			return "", err
		}
	}

	return tmpFile.Name(), nil
}

func TestReadLogFile(t *testing.T) {
	testEntries := createTestLogEntries()
	testFile, err := createTestLogFile(testEntries)
	if err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}
	defer os.Remove(testFile)

	entries, err := readLogFile(testFile)
	if err != nil {
		t.Fatalf("Failed to read log file: %v", err)
	}

	if len(entries) != len(testEntries) {
		t.Errorf("Expected %d entries, got %d", len(testEntries), len(entries))
	}

	// Verify first entry
	if entries[0].UserID != "user123" {
		t.Errorf("Expected UserID 'user123', got '%s'", entries[0].UserID)
	}
}

func TestApplyFilters(t *testing.T) {
	testEntries := createTestLogEntries()

	// Test user filter
	userFilter = "user123"
	ipFilter = ""
	actionFilter = ""
	timeRange = ""

	filtered := applyFilters(testEntries)
	
	for _, entry := range filtered {
		if entry.UserID != "user123" {
			t.Errorf("User filter failed: got UserID '%s', expected 'user123'", entry.UserID)
		}
	}

	// Test IP filter
	userFilter = ""
	ipFilter = "192.168.1.200"
	
	filtered = applyFilters(testEntries)
	
	for _, entry := range filtered {
		if entry.IP != "192.168.1.200" {
			t.Errorf("IP filter failed: got IP '%s', expected '192.168.1.200'", entry.IP)
		}
	}

	// Test action filter
	userFilter = ""
	ipFilter = ""
	actionFilter = "export"
	
	filtered = applyFilters(testEntries)
	
	for _, entry := range filtered {
		if entry.Action != "export" {
			t.Errorf("Action filter failed: got Action '%s', expected 'export'", entry.Action)
		}
	}

	// Reset filters
	userFilter = ""
	ipFilter = ""
	actionFilter = ""
	timeRange = ""
}

func TestDetectFailedLoginBursts(t *testing.T) {
	// Create entries with failed login burst
	burstEntries := []LogEntry{}
	baseTime := time.Now().Add(-1 * time.Hour)
	
	// Create 6 failed logins within 5 minutes
	for i := 0; i < 6; i++ {
		entry := LogEntry{
			Timestamp: baseTime.Add(time.Duration(i) * time.Minute).Format(time.RFC3339),
			Level:     "ERROR",
			Message:   "User login failed",
			UserID:    "attacker",
			IP:        "192.168.1.100",
			Action:    "login",
			Status:    401,
		}
		burstEntries = append(burstEntries, entry)
	}

	anomalies := detectFailedLoginBursts(burstEntries)

	if len(anomalies) == 0 {
		t.Error("Expected to detect failed login burst, but none found")
	}

	if len(anomalies) > 0 {
		anomaly := anomalies[0]
		if anomaly.Type != "failed_login_burst" {
			t.Errorf("Expected type 'failed_login_burst', got '%s'", anomaly.Type)
		}
		if anomaly.Count < 5 {
			t.Errorf("Expected count >= 5, got %d", anomaly.Count)
		}
	}
}

func TestDetectDataExportSpikes(t *testing.T) {
	// Create entries with data export spike
	exportEntries := []LogEntry{}
	
	// Create 12 export actions for same user
	for i := 0; i < 12; i++ {
		entry := LogEntry{
			Timestamp: time.Now().Add(time.Duration(-i) * time.Minute).Format(time.RFC3339),
			Level:     "INFO",
			Message:   "Data export completed",
			UserID:    "bulk_exporter",
			IP:        "192.168.1.100",
			Action:    "export",
			Status:    200,
		}
		exportEntries = append(exportEntries, entry)
	}

	anomalies := detectDataExportSpikes(exportEntries)

	if len(anomalies) == 0 {
		t.Error("Expected to detect data export spike, but none found")
	}

	if len(anomalies) > 0 {
		anomaly := anomalies[0]
		if anomaly.Type != "data_export_spike" {
			t.Errorf("Expected type 'data_export_spike', got '%s'", anomaly.Type)
		}
		if anomaly.Count != 12 {
			t.Errorf("Expected count 12, got %d", anomaly.Count)
		}
	}
}

func TestDetectSuspiciousAPIAccess(t *testing.T) {
	// Create entries with high API usage
	apiEntries := []LogEntry{}
	
	// Create 120 API requests within short time frame
	for i := 0; i < 120; i++ {
		entry := LogEntry{
			Timestamp: time.Now().Add(time.Duration(-i) * time.Second).Format(time.RFC3339),
			Level:     "INFO",
			Message:   "API request",
			UserID:    "api_user",
			IP:        "192.168.1.100",
			Action:    "api_call",
			Endpoint:  "/api/data",
			Status:    200,
		}
		apiEntries = append(apiEntries, entry)
	}

	anomalies := detectSuspiciousAPIAccess(apiEntries)

	if len(anomalies) == 0 {
		t.Error("Expected to detect suspicious API access, but none found")
	}

	if len(anomalies) > 0 {
		anomaly := anomalies[0]
		if anomaly.Type != "suspicious_api_access" {
			t.Errorf("Expected type 'suspicious_api_access', got '%s'", anomaly.Type)
		}
		if anomaly.Count != 120 {
			t.Errorf("Expected count 120, got %d", anomaly.Count)
		}
	}
}

func TestDetectIPAnomalies(t *testing.T) {
	// Create entries with one IP used by many users
	ipEntries := []LogEntry{}
	
	// Create entries for 7 different users from same IP
	users := []string{"user1", "user2", "user3", "user4", "user5", "user6", "user7"}
	for _, user := range users {
		entry := LogEntry{
			Timestamp: time.Now().Format(time.RFC3339),
			Level:     "INFO",
			Message:   "User login",
			UserID:    user,
			IP:        "192.168.1.100",
			Action:    "login",
			Status:    200,
		}
		ipEntries = append(ipEntries, entry)
	}

	anomalies := detectIPAnomalies(ipEntries)

	if len(anomalies) == 0 {
		t.Error("Expected to detect IP anomaly, but none found")
	}

	if len(anomalies) > 0 {
		anomaly := anomalies[0]
		if anomaly.Type != "ip_multiple_users" {
			t.Errorf("Expected type 'ip_multiple_users', got '%s'", anomaly.Type)
		}
		if !strings.Contains(anomaly.Description, "7 different users") {
			t.Errorf("Expected description to mention 7 users, got: %s", anomaly.Description)
		}
	}
}

func TestFormatAsTable(t *testing.T) {
	anomaly := AnomalyResult{
		Type:        "test_anomaly",
		Description: "Test anomaly description",
		Count:       5,
		TimeWindow:  "5 minutes",
		FirstSeen:   time.Now(),
		LastSeen:    time.Now(),
		Entries:     []LogEntry{},
	}

	anomalies := []AnomalyResult{anomaly}
	table := formatAsTable(anomalies)

	if !strings.Contains(table, "test_anomaly") {
		t.Error("Table output should contain anomaly type")
	}

	if !strings.Contains(table, "Test anomaly description") {
		t.Error("Table output should contain anomaly description")
	}
}

func TestFormatAsCSV(t *testing.T) {
	anomaly := AnomalyResult{
		Type:        "test_anomaly",
		Description: "Test anomaly description",
		Count:       5,
		TimeWindow:  "5 minutes",
		FirstSeen:   time.Now(),
		LastSeen:    time.Now(),
		Entries:     []LogEntry{},
	}

	anomalies := []AnomalyResult{anomaly}
	csv := formatAsCSV(anomalies)

	if !strings.Contains(csv, "Type,Count,TimeWindow") {
		t.Error("CSV output should contain header")
	}

	if !strings.Contains(csv, "test_anomaly,5") {
		t.Error("CSV output should contain anomaly data")
	}
}

func TestIsInTimeRange(t *testing.T) {
	// Test valid time range
	testTime := "2024-01-15T10:00:00Z"
	timeRange := "2024-01-15,2024-01-16"
	
	result := isInTimeRange(testTime, timeRange)
	if !result {
		t.Error("Time should be within range")
	}

	// Test time outside range
	timeRange = "2024-01-10,2024-01-12"
	result = isInTimeRange(testTime, timeRange)
	if result {
		t.Error("Time should be outside range")
	}

	// Test invalid range format
	timeRange = "invalid-range"
	result = isInTimeRange(testTime, timeRange)
	if !result {
		t.Error("Invalid range should return true (include all)")
	}
}

// Benchmark tests
func BenchmarkReadLogFile(b *testing.B) {
	testEntries := createTestLogEntries()
	testFile, err := createTestLogFile(testEntries)
	if err != nil {
		b.Fatalf("Failed to create test file: %v", err)
	}
	defer os.Remove(testFile)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := readLogFile(testFile)
		if err != nil {
			b.Fatalf("Failed to read log file: %v", err)
		}
	}
}

func BenchmarkDetectAnomalies(b *testing.B) {
	testEntries := createTestLogEntries()
	
	// Add more entries for realistic benchmark
	for i := 0; i < 1000; i++ {
		entry := LogEntry{
			Timestamp: time.Now().Add(time.Duration(-i) * time.Second).Format(time.RFC3339),
			Level:     "INFO",
			Message:   "Normal log entry",
			UserID:    "user" + string(rune(i%100)),
			IP:        "192.168.1." + string(rune(100+i%50)),
			Action:    "action",
			Status:    200,
		}
		testEntries = append(testEntries, entry)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		detectSecurityAnomalies(testEntries)
	}
}

// Integration test with actual file I/O
func TestEndToEndProcessing(t *testing.T) {
	testEntries := createTestLogEntries()
	testFile, err := createTestLogFile(testEntries)
	if err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}
	defer os.Remove(testFile)

	// Set up test parameters
	inputFile = testFile
	detectAnomalies = true
	format = "json"
	outputFile = ""
	userFilter = ""
	ipFilter = ""
	actionFilter = ""
	timeRange = ""
	verbose = false

	// This would normally be called by cobra, but we'll simulate it
	entries, err := readLogFile(inputFile)
	if err != nil {
		t.Fatalf("Failed to read log file: %v", err)
	}

	filtered := applyFilters(entries)
	anomalies := detectSecurityAnomalies(filtered)

	// Should detect the failed login burst we created in test data
	foundBurst := false
	for _, anomaly := range anomalies {
		if anomaly.Type == "failed_login_burst" {
			foundBurst = true
			break
		}
	}

	if !foundBurst {
		t.Error("End-to-end processing should detect failed login burst from test data")
	}
}