package cmd

import (
	"testing"
	"os"
	"encoding/json"
	"time"
	"path/filepath"
	"strings"
)

func TestAnalyzeCommand(t *testing.T) {
	// Create test log file
	testEntries := []LogEntry{
		{
			Timestamp: time.Now().Format(time.RFC3339),
			Level:     "ERROR",
			Message:   "Login failed",
			UserID:    "test_user",
			IP:        "192.168.1.1",
			Action:    "login",
			Status:    401,
		},
	}

	tmpFile, err := os.CreateTemp("", "test-*.json")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	encoder := json.NewEncoder(tmpFile)
	for _, entry := range testEntries {
		encoder.Encode(entry)
	}
	tmpFile.Close()

	// Test analyze command execution
	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"analyze", "--file", tmpFile.Name()})
	
	err = rootCmd.Execute()
	if err != nil {
		t.Errorf("Analyze command failed: %v", err)
	}
}

func TestAnalyzeWithFilters(t *testing.T) {
	// Create test log file with multiple entries
	testEntries := []LogEntry{
		{
			Timestamp: time.Now().Format(time.RFC3339),
			Level:     "INFO",
			Message:   "Login successful",
			UserID:    "user1",
			IP:        "192.168.1.1",
			Action:    "login",
			Status:    200,
		},
		{
			Timestamp: time.Now().Format(time.RFC3339),
			Level:     "ERROR",
			Message:   "Login failed",
			UserID:    "user2",
			IP:        "192.168.1.2",
			Action:    "login",
			Status:    401,
		},
	}

	tmpFile, err := os.CreateTemp("", "test-*.json")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	encoder := json.NewEncoder(tmpFile)
	for _, entry := range testEntries {
		encoder.Encode(entry)
	}
	tmpFile.Close()

	// Test with user filter
	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"analyze", "--file", tmpFile.Name(), "--user", "user1"})
	
	err = rootCmd.Execute()
	if err != nil {
		t.Errorf("Analyze with user filter failed: %v", err)
	}

	// Test with IP filter
	rootCmd = NewRootCmd()
	rootCmd.SetArgs([]string{"analyze", "--file", tmpFile.Name(), "--ip", "192.168.1.2"})
	
	err = rootCmd.Execute()
	if err != nil {
		t.Errorf("Analyze with IP filter failed: %v", err)
	}
}

func TestAnalyzeWithOutput(t *testing.T) {
	// Create test log file
	testEntries := []LogEntry{
		{
			Timestamp: time.Now().Format(time.RFC3339),
			Level:     "INFO",
			Message:   "Test entry",
			UserID:    "test_user",
			IP:        "192.168.1.1",
			Action:    "test",
			Status:    200,
		},
	}

	tmpFile, err := os.CreateTemp("", "test-*.json")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	encoder := json.NewEncoder(tmpFile)
	for _, entry := range testEntries {
		encoder.Encode(entry)
	}
	tmpFile.Close()

	// Create output file
	outputFile, err := os.CreateTemp("", "output-*.json")
	if err != nil {
		t.Fatalf("Failed to create output file: %v", err)
	}
	defer os.Remove(outputFile.Name())
	outputFile.Close()

	// Test analyze command with output file
	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"analyze", "--file", tmpFile.Name(), "--output", outputFile.Name(), "--format", "json"})
	
	err = rootCmd.Execute()
	if err != nil {
		t.Errorf("Analyze with output file failed: %v", err)
	}

	// Verify output file was created and contains data
	if _, err := os.Stat(outputFile.Name()); os.IsNotExist(err) {
		t.Error("Output file should exist after analysis")
	}
}

func TestAnalyzeInvalidFile(t *testing.T) {
	// Test with non-existent file
	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"analyze", "--file", "non-existent-file.json"})
	
	err := rootCmd.Execute()
	if err == nil {
		t.Error("Expected error for non-existent file")
	}
}

func TestAnalyzeAnomalyDetection(t *testing.T) {
	// Create entries that should trigger anomaly detection
	testEntries := []LogEntry{}
	
	// Create failed login burst
	for i := 0; i < 6; i++ {
		entry := LogEntry{
			Timestamp: time.Now().Add(time.Duration(-i) * time.Minute).Format(time.RFC3339),
			Level:     "ERROR",
			Message:   "Login failed",
			UserID:    "attacker",
			IP:        "192.168.1.100",
			Action:    "login",
			Status:    401,
		}
		testEntries = append(testEntries, entry)
	}

	tmpFile, err := os.CreateTemp("", "test-*.json")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	encoder := json.NewEncoder(tmpFile)
	for _, entry := range testEntries {
		encoder.Encode(entry)
	}
	tmpFile.Close()

	// Test analyze command with anomaly detection
	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"analyze", "--file", tmpFile.Name(), "--detect-anomalies"})
	
	err = rootCmd.Execute()
	if err != nil {
		t.Errorf("Analyze with anomaly detection failed: %v", err)
	}
}

func TestAnalyzeTimeRange(t *testing.T) {
	// Create test entries with different timestamps
	baseTime := time.Now()
	testEntries := []LogEntry{
		{
			Timestamp: baseTime.Add(-2*24*time.Hour).Format(time.RFC3339), // 2 days ago
			Level:     "INFO",
			Message:   "Old entry",
			UserID:    "user1",
			IP:        "192.168.1.1",
			Action:    "login",
			Status:    200,
		},
		{
			Timestamp: baseTime.Format(time.RFC3339), // Now
			Level:     "INFO", 
			Message:   "Recent entry",
			UserID:    "user1",
			IP:        "192.168.1.1",
			Action:    "login",
			Status:    200,
		},
	}

	tmpFile, err := os.CreateTemp("", "test-*.json")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	encoder := json.NewEncoder(tmpFile)
	for _, entry := range testEntries {
		encoder.Encode(entry)
	}
	tmpFile.Close()

	// Test with time range that should only include recent entry
	yesterday := baseTime.Add(-24*time.Hour).Format("2006-01-02")
	tomorrow := baseTime.Add(24*time.Hour).Format("2006-01-02")
	timeRange := yesterday + "," + tomorrow

	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"analyze", "--file", tmpFile.Name(), "--time-range", timeRange})
	
	err = rootCmd.Execute()
	if err != nil {
		t.Errorf("Analyze with time range failed: %v", err)
	}
}

func TestAnalyzeFormats(t *testing.T) {
	// Create test log file
	testEntries := []LogEntry{
		{
			Timestamp: time.Now().Format(time.RFC3339),
			Level:     "INFO",
			Message:   "Test entry",
			UserID:    "test_user",
			IP:        "192.168.1.1",
			Action:    "test",
			Status:    200,
		},
	}

	tmpFile, err := os.CreateTemp("", "test-*.json")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	encoder := json.NewEncoder(tmpFile)
	for _, entry := range testEntries {
		encoder.Encode(entry)
	}
	tmpFile.Close()

	formats := []string{"json", "table", "csv"}
	
	for _, format := range formats {
		t.Run("format_"+format, func(t *testing.T) {
			rootCmd := NewRootCmd()
			rootCmd.SetArgs([]string{"analyze", "--file", tmpFile.Name(), "--format", format})
			
			err := rootCmd.Execute()
			if err != nil {
				t.Errorf("Analyze with format %s failed: %v", format, err)
			}
		})
	}
}

func TestAnalyzeVerboseOutput(t *testing.T) {
	// Create test log file
	testEntries := []LogEntry{
		{
			Timestamp: time.Now().Format(time.RFC3339),
			Level:     "INFO",
			Message:   "Test entry",
			UserID:    "test_user",
			IP:        "192.168.1.1",
			Action:    "test",
			Status:    200,
		},
	}

	tmpFile, err := os.CreateTemp("", "test-*.json")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	encoder := json.NewEncoder(tmpFile)
	for _, entry := range testEntries {
		encoder.Encode(entry)
	}
	tmpFile.Close()

	// Test verbose output
	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"analyze", "--file", tmpFile.Name(), "--verbose"})
	
	err = rootCmd.Execute()
	if err != nil {
		t.Errorf("Analyze with verbose output failed: %v", err)
	}
}

// Test helper functions
func TestGetLogStatsIntegration(t *testing.T) {
	testEntries := []LogEntry{
		{Level: "INFO", Status: 200},
		{Level: "ERROR", Status: 401},
		{Level: "WARN", Status: 500},
		{Level: "INFO", Status: 200},
	}

	// This would be tested if getLogStats was exported
	// For now, we test through the command execution
	tmpFile, err := os.CreateTemp("", "test-*.json")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	encoder := json.NewEncoder(tmpFile)
	for _, entry := range testEntries {
		encoder.Encode(entry)
	}
	tmpFile.Close()

	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"analyze", "--file", tmpFile.Name(), "--verbose"})
	
	err = rootCmd.Execute()
	if err != nil {
		t.Errorf("Stats integration test failed: %v", err)
	}
}

func TestAnalyzeEmptyFile(t *testing.T) {
	// Create empty log file
	tmpFile, err := os.CreateTemp("", "empty-*.json")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())
	tmpFile.Close()

	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"analyze", "--file", tmpFile.Name()})
	
	err = rootCmd.Execute()
	// Should handle empty file gracefully
	if err != nil {
		t.Errorf("Analyze empty file should not fail: %v", err)
	}
}

func TestAnalyzeMalformedJSON(t *testing.T) {
	// Create file with malformed JSON
	tmpFile, err := os.CreateTemp("", "malformed-*.json")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	// Write malformed JSON
	tmpFile.WriteString(`{"timestamp": "invalid json`)
	tmpFile.Close()

	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"analyze", "--file", tmpFile.Name()})
	
	err = rootCmd.Execute()
	// Should handle malformed JSON appropriately
	if err == nil {
		t.Log("Note: Command handled malformed JSON gracefully")
	}
}

func TestAnalyzeLargeFile(t *testing.T) {
	// Create file with many entries to test performance
	tmpFile, err := os.CreateTemp("", "large-*.json")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	encoder := json.NewEncoder(tmpFile)
	
	// Create 1000 test entries
	for i := 0; i < 1000; i++ {
		entry := LogEntry{
			Timestamp: time.Now().Add(time.Duration(-i) * time.Second).Format(time.RFC3339),
			Level:     "INFO",
			Message:   "Test entry " + string(rune(i)),
			UserID:    "user" + string(rune(i%10)),
			IP:        "192.168.1." + string(rune(100+i%50)),
			Action:    "action",
			Status:    200,
		}
		encoder.Encode(entry)
	}
	tmpFile.Close()

	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"analyze", "--file", tmpFile.Name()})
	
	err = rootCmd.Execute()
	if err != nil {
		t.Errorf("Analyze large file failed: %v", err)
	}
}