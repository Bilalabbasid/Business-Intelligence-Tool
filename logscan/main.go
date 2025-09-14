package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"sort"
	"strings"
	"time"

	"github.com/spf13/cobra"
)

type LogEntry struct {
	Timestamp string                 `json:"timestamp"`
	Level     string                 `json:"level"`
	Message   string                 `json:"message"`
	UserID    string                 `json:"user_id"`
	IP        string                 `json:"ip"`
	Action    string                 `json:"action"`
	Endpoint  string                 `json:"endpoint"`
	Status    int                    `json:"status"`
	Duration  float64                `json:"duration"`
	Extra     map[string]interface{} `json:"extra"`
}

type AnomalyResult struct {
	Type        string    `json:"type"`
	Description string    `json:"description"`
	Count       int       `json:"count"`
	TimeWindow  string    `json:"time_window"`
	FirstSeen   time.Time `json:"first_seen"`
	LastSeen    time.Time `json:"last_seen"`
	Entries     []LogEntry `json:"entries"`
}

var (
	inputFile    string
	outputFile   string
	userFilter   string
	ipFilter     string
	actionFilter string
	timeRange    string
	detectAnomalies bool
	verbose      bool
	format       string
)

var rootCmd = &cobra.Command{
	Use:   "logscan",
	Short: "Enterprise log analysis and anomaly detection tool",
	Long: `logscan analyzes JSON log files to detect suspicious patterns and security anomalies.

Features:
- Filter logs by user, IP, action, or time range
- Detect failed login bursts
- Identify unusual data export patterns
- Find suspicious API access patterns
- Generate detailed security reports`,
	Run: runLogScan,
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func init() {
	rootCmd.Flags().StringVarP(&inputFile, "input", "i", "", "Input log file (JSON lines format)")
	rootCmd.Flags().StringVarP(&outputFile, "output", "o", "", "Output file for results (default: stdout)")
	rootCmd.Flags().StringVar(&userFilter, "user", "", "Filter by user ID")
	rootCmd.Flags().StringVar(&ipFilter, "ip", "", "Filter by IP address")
	rootCmd.Flags().StringVar(&actionFilter, "action", "", "Filter by action type")
	rootCmd.Flags().StringVar(&timeRange, "time-range", "", "Time range (e.g., '2024-01-01,2024-01-02')")
	rootCmd.Flags().BoolVar(&detectAnomalies, "anomalies", false, "Enable anomaly detection")
	rootCmd.Flags().BoolVarP(&verbose, "verbose", "v", false, "Verbose output")
	rootCmd.Flags().StringVar(&format, "format", "json", "Output format: json, table, csv")
	
	rootCmd.MarkFlagRequired("input")
}

func runLogScan(cmd *cobra.Command, args []string) {
	if verbose {
		log.Printf("Reading log file: %s", inputFile)
	}
	
	entries, err := readLogFile(inputFile)
	if err != nil {
		log.Fatalf("Failed to read log file: %v", err)
	}
	
	if verbose {
		log.Printf("Loaded %d log entries", len(entries))
	}
	
	// Apply filters
	filtered := applyFilters(entries)
	
	if verbose {
		log.Printf("After filtering: %d entries", len(filtered))
	}
	
	var results interface{}
	
	if detectAnomalies {
		anomalies := detectSecurityAnomalies(filtered)
		results = anomalies
		if verbose {
			log.Printf("Detected %d anomalies", len(anomalies))
		}
	} else {
		results = filtered
	}
	
	// Output results
	if err := outputResults(results); err != nil {
		log.Fatalf("Failed to output results: %v", err)
	}
}

func readLogFile(filename string) ([]LogEntry, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	
	var entries []LogEntry
	decoder := json.NewDecoder(file)
	
	for decoder.More() {
		var entry LogEntry
		if err := decoder.Decode(&entry); err != nil {
			if verbose {
				log.Printf("Warning: Failed to decode line: %v", err)
			}
			continue
		}
		entries = append(entries, entry)
	}
	
	return entries, nil
}

func applyFilters(entries []LogEntry) []LogEntry {
	var filtered []LogEntry
	
	for _, entry := range entries {
		if userFilter != "" && entry.UserID != userFilter {
			continue
		}
		
		if ipFilter != "" && entry.IP != ipFilter {
			continue
		}
		
		if actionFilter != "" && entry.Action != actionFilter {
			continue
		}
		
		if timeRange != "" {
			if !isInTimeRange(entry.Timestamp, timeRange) {
				continue
			}
		}
		
		filtered = append(filtered, entry)
	}
	
	return filtered
}

func isInTimeRange(timestamp, timeRange string) bool {
	parts := strings.Split(timeRange, ",")
	if len(parts) != 2 {
		return true // Invalid range, include all
	}
	
	startTime, err1 := time.Parse("2006-01-02", strings.TrimSpace(parts[0]))
	endTime, err2 := time.Parse("2006-01-02", strings.TrimSpace(parts[1]))
	
	if err1 != nil || err2 != nil {
		return true // Invalid dates, include all
	}
	
	// Try to parse the entry timestamp
	entryTime, err := time.Parse(time.RFC3339, timestamp)
	if err != nil {
		// Try alternative format
		entryTime, err = time.Parse("2006-01-02T15:04:05", timestamp)
		if err != nil {
			return true // Can't parse, include
		}
	}
	
	return entryTime.After(startTime) && entryTime.Before(endTime.Add(24*time.Hour))
}

func detectSecurityAnomalies(entries []LogEntry) []AnomalyResult {
	var anomalies []AnomalyResult
	
	// Detect failed login bursts
	failedLogins := detectFailedLoginBursts(entries)
	anomalies = append(anomalies, failedLogins...)
	
	// Detect data export spikes
	dataExports := detectDataExportSpikes(entries)
	anomalies = append(anomalies, dataExports...)
	
	// Detect suspicious API access patterns
	apiAnomalies := detectSuspiciousAPIAccess(entries)
	anomalies = append(anomalies, apiAnomalies...)
	
	// Detect IP-based anomalies
	ipAnomalies := detectIPAnomalies(entries)
	anomalies = append(anomalies, ipAnomalies...)
	
	return anomalies
}

func detectFailedLoginBursts(entries []LogEntry) []AnomalyResult {
	var anomalies []AnomalyResult
	
	// Group failed logins by user and time window (5-minute windows)
	userFailures := make(map[string]map[string][]LogEntry)
	
	for _, entry := range entries {
		if entry.Action == "login" && entry.Status >= 400 {
			if userFailures[entry.UserID] == nil {
				userFailures[entry.UserID] = make(map[string][]LogEntry)
			}
			
			// Create 5-minute time buckets
			entryTime, err := time.Parse(time.RFC3339, entry.Timestamp)
			if err != nil {
				continue
			}
			
			bucket := entryTime.Truncate(5 * time.Minute).Format(time.RFC3339)
			userFailures[entry.UserID][bucket] = append(userFailures[entry.UserID][bucket], entry)
		}
	}
	
	// Look for bursts (>= 5 failures in 5 minutes)
	for userID, buckets := range userFailures {
		for bucket, failures := range buckets {
			if len(failures) >= 5 {
				bucketTime, _ := time.Parse(time.RFC3339, bucket)
				
				anomaly := AnomalyResult{
					Type:        "failed_login_burst",
					Description: fmt.Sprintf("User %s had %d failed login attempts in 5 minutes", userID, len(failures)),
					Count:       len(failures),
					TimeWindow:  "5 minutes",
					FirstSeen:   bucketTime,
					LastSeen:    bucketTime.Add(5 * time.Minute),
					Entries:     failures,
				}
				
				anomalies = append(anomalies, anomaly)
			}
		}
	}
	
	return anomalies
}

func detectDataExportSpikes(entries []LogEntry) []AnomalyResult {
	var anomalies []AnomalyResult
	
	// Look for users with many data export actions
	userExports := make(map[string][]LogEntry)
	
	for _, entry := range entries {
		if strings.Contains(strings.ToLower(entry.Action), "export") ||
		   strings.Contains(strings.ToLower(entry.Endpoint), "export") ||
		   strings.Contains(strings.ToLower(entry.Message), "export") {
			userExports[entry.UserID] = append(userExports[entry.UserID], entry)
		}
	}
	
	// Flag users with > 10 exports in the dataset
	for userID, exports := range userExports {
		if len(exports) > 10 {
			sort.Slice(exports, func(i, j int) bool {
				return exports[i].Timestamp < exports[j].Timestamp
			})
			
			firstTime, _ := time.Parse(time.RFC3339, exports[0].Timestamp)
			lastTime, _ := time.Parse(time.RFC3339, exports[len(exports)-1].Timestamp)
			
			anomaly := AnomalyResult{
				Type:        "data_export_spike",
				Description: fmt.Sprintf("User %s performed %d data exports", userID, len(exports)),
				Count:       len(exports),
				TimeWindow:  fmt.Sprintf("%.1f hours", lastTime.Sub(firstTime).Hours()),
				FirstSeen:   firstTime,
				LastSeen:    lastTime,
				Entries:     exports[:10], // Limit entries in output
			}
			
			anomalies = append(anomalies, anomaly)
		}
	}
	
	return anomalies
}

func detectSuspiciousAPIAccess(entries []LogEntry) []AnomalyResult {
	var anomalies []AnomalyResult
	
	// Look for rapid API access patterns
	userRequests := make(map[string][]LogEntry)
	
	for _, entry := range entries {
		if entry.Endpoint != "" {
			userRequests[entry.UserID] = append(userRequests[entry.UserID], entry)
		}
	}
	
	// Check for users with > 100 API requests
	for userID, requests := range userRequests {
		if len(requests) > 100 {
			sort.Slice(requests, func(i, j int) bool {
				return requests[i].Timestamp < requests[j].Timestamp
			})
			
			firstTime, _ := time.Parse(time.RFC3339, requests[0].Timestamp)
			lastTime, _ := time.Parse(time.RFC3339, requests[len(requests)-1].Timestamp)
			
			duration := lastTime.Sub(firstTime)
			if duration.Minutes() < 60 { // > 100 requests in < 1 hour
				anomaly := AnomalyResult{
					Type:        "suspicious_api_access",
					Description: fmt.Sprintf("User %s made %d API requests in %.1f minutes", userID, len(requests), duration.Minutes()),
					Count:       len(requests),
					TimeWindow:  fmt.Sprintf("%.1f minutes", duration.Minutes()),
					FirstSeen:   firstTime,
					LastSeen:    lastTime,
					Entries:     requests[:10], // Limit entries
				}
				
				anomalies = append(anomalies, anomaly)
			}
		}
	}
	
	return anomalies
}

func detectIPAnomalies(entries []LogEntry) []AnomalyResult {
	var anomalies []AnomalyResult
	
	// Look for IPs with many different user sessions
	ipUsers := make(map[string]map[string]bool)
	ipEntries := make(map[string][]LogEntry)
	
	for _, entry := range entries {
		if entry.IP != "" && entry.UserID != "" {
			if ipUsers[entry.IP] == nil {
				ipUsers[entry.IP] = make(map[string]bool)
			}
			ipUsers[entry.IP][entry.UserID] = true
			ipEntries[entry.IP] = append(ipEntries[entry.IP], entry)
		}
	}
	
	// Flag IPs with > 5 different users
	for ip, users := range ipUsers {
		if len(users) > 5 {
			entries := ipEntries[ip]
			if len(entries) > 0 {
				sort.Slice(entries, func(i, j int) bool {
					return entries[i].Timestamp < entries[j].Timestamp
				})
				
				firstTime, _ := time.Parse(time.RFC3339, entries[0].Timestamp)
				lastTime, _ := time.Parse(time.RFC3339, entries[len(entries)-1].Timestamp)
				
				var userList []string
				for user := range users {
					userList = append(userList, user)
				}
				
				anomaly := AnomalyResult{
					Type:        "ip_multiple_users",
					Description: fmt.Sprintf("IP %s accessed by %d different users: %s", ip, len(users), strings.Join(userList, ", ")),
					Count:       len(entries),
					TimeWindow:  fmt.Sprintf("%.1f hours", lastTime.Sub(firstTime).Hours()),
					FirstSeen:   firstTime,
					LastSeen:    lastTime,
					Entries:     entries[:10], // Limit entries
				}
				
				anomalies = append(anomalies, anomaly)
			}
		}
	}
	
	return anomalies
}

func outputResults(results interface{}) error {
	var output []byte
	var err error
	
	switch format {
	case "json":
		output, err = json.MarshalIndent(results, "", "  ")
	case "table":
		output = []byte(formatAsTable(results))
	case "csv":
		output = []byte(formatAsCSV(results))
	default:
		output, err = json.MarshalIndent(results, "", "  ")
	}
	
	if err != nil {
		return err
	}
	
	if outputFile != "" {
		return os.WriteFile(outputFile, output, 0644)
	}
	
	fmt.Print(string(output))
	return nil
}

func formatAsTable(results interface{}) string {
	// Simple table formatting for anomalies
	if anomalies, ok := results.([]AnomalyResult); ok {
		var sb strings.Builder
		sb.WriteString(fmt.Sprintf("%-20s %-10s %-15s %s\n", "TYPE", "COUNT", "TIME WINDOW", "DESCRIPTION"))
		sb.WriteString(strings.Repeat("-", 80) + "\n")
		
		for _, anomaly := range anomalies {
			sb.WriteString(fmt.Sprintf("%-20s %-10d %-15s %s\n",
				anomaly.Type, anomaly.Count, anomaly.TimeWindow, anomaly.Description))
		}
		
		return sb.String()
	}
	
	return "Table format not supported for this data type\n"
}

func formatAsCSV(results interface{}) string {
	if anomalies, ok := results.([]AnomalyResult); ok {
		var sb strings.Builder
		sb.WriteString("Type,Count,TimeWindow,Description,FirstSeen,LastSeen\n")
		
		for _, anomaly := range anomalies {
			sb.WriteString(fmt.Sprintf("%s,%d,%s,\"%s\",%s,%s\n",
				anomaly.Type, anomaly.Count, anomaly.TimeWindow,
				strings.ReplaceAll(anomaly.Description, "\"", "\"\""),
				anomaly.FirstSeen.Format(time.RFC3339),
				anomaly.LastSeen.Format(time.RFC3339)))
		}
		
		return sb.String()
	}
	
	return "CSV format not supported for this data type\n"
}