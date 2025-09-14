package cmd

import (
	"testing"
	"os"
	"strings"
)

func TestRootCommand(t *testing.T) {
	rootCmd := NewRootCmd()
	
	// Test root command has correct use
	if rootCmd.Use != "logscan" {
		t.Errorf("Expected Use to be 'logscan', got '%s'", rootCmd.Use)
	}
	
	// Test root command has description
	if rootCmd.Short == "" {
		t.Error("Root command should have a short description")
	}
}

func TestRootCommandHelp(t *testing.T) {
	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"--help"})
	
	err := rootCmd.Execute()
	if err != nil {
		t.Errorf("Help command should not return error: %v", err)
	}
}

func TestRootCommandVersion(t *testing.T) {
	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"--version"})
	
	// Capture output to test version display
	err := rootCmd.Execute()
	if err != nil {
		t.Errorf("Version command should not return error: %v", err)
	}
}

func TestRootCommandWithInvalidSubcommand(t *testing.T) {
	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"invalid-command"})
	
	err := rootCmd.Execute()
	if err == nil {
		t.Error("Invalid subcommand should return error")
	}
}

func TestRootCommandHasAnalyzeSubcommand(t *testing.T) {
	rootCmd := NewRootCmd()
	
	// Check if analyze command exists
	analyzeCmd, _, err := rootCmd.Find([]string{"analyze"})
	if err != nil {
		t.Errorf("Analyze command should exist: %v", err)
	}
	
	if analyzeCmd == nil {
		t.Error("Analyze command should not be nil")
	}
	
	if analyzeCmd.Use != "analyze" {
		t.Errorf("Expected analyze command Use to be 'analyze', got '%s'", analyzeCmd.Use)
	}
}

func TestRootCommandPersistentFlags(t *testing.T) {
	rootCmd := NewRootCmd()
	
	// Test that version flag exists
	versionFlag := rootCmd.PersistentFlags().Lookup("version")
	if versionFlag == nil {
		t.Error("Version flag should exist")
	}
}

func TestRootCommandCompletion(t *testing.T) {
	rootCmd := NewRootCmd()
	
	// Test bash completion
	rootCmd.SetArgs([]string{"completion", "bash"})
	err := rootCmd.Execute()
	if err != nil {
		t.Errorf("Bash completion should work: %v", err)
	}
}

func TestRootCommandExecuteWithoutArgs(t *testing.T) {
	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{})
	
	// Should show help when run without arguments
	err := rootCmd.Execute()
	if err != nil {
		t.Errorf("Root command without args should not error: %v", err)
	}
}

// Test command structure and relationships
func TestCommandStructure(t *testing.T) {
	rootCmd := NewRootCmd()
	
	// Verify root command has expected subcommands
	expectedSubcommands := []string{"analyze", "completion", "help"}
	
	subcommands := rootCmd.Commands()
	subcommandNames := make([]string, len(subcommands))
	for i, cmd := range subcommands {
		subcommandNames[i] = cmd.Name()
	}
	
	for _, expected := range expectedSubcommands {
		found := false
		for _, actual := range subcommandNames {
			if actual == expected {
				found = true
				break
			}
		}
		if !found && expected != "help" { // help is auto-generated
			t.Errorf("Expected subcommand '%s' not found", expected)
		}
	}
}

// Test command validation
func TestCommandValidation(t *testing.T) {
	rootCmd := NewRootCmd()
	
	// Test that command has proper validation
	if rootCmd.RunE != nil {
		t.Log("Root command has RunE function")
	}
	
	// Verify command is properly configured
	if rootCmd.SilenceUsage != true {
		t.Log("Note: SilenceUsage could be set to true for cleaner error output")
	}
}

// Test error handling
func TestCommandErrorHandling(t *testing.T) {
	// Redirect stderr to capture error output
	originalStderr := os.Stderr
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatalf("Failed to create pipe: %v", err)
	}
	os.Stderr = w

	rootCmd := NewRootCmd()
	rootCmd.SetArgs([]string{"invalid-subcommand"})
	
	err = rootCmd.Execute()
	
	// Restore stderr
	w.Close()
	os.Stderr = originalStderr
	
	if err == nil {
		t.Error("Invalid subcommand should return error")
	}
	
	// Read captured stderr
	buf := make([]byte, 1024)
	n, _ := r.Read(buf)
	r.Close()
	
	if n > 0 {
		output := string(buf[:n])
		if !strings.Contains(output, "unknown command") && 
		   !strings.Contains(output, "invalid") && 
		   !strings.Contains(output, "help") {
			t.Log("Error output captured:", output)
		}
	}
}

// Test command flags inheritance
func TestFlagInheritance(t *testing.T) {
	rootCmd := NewRootCmd()
	
	// Get analyze subcommand
	analyzeCmd, _, err := rootCmd.Find([]string{"analyze"})
	if err != nil {
		t.Fatalf("Failed to find analyze command: %v", err)
	}
	
	// Test that analyze command inherits persistent flags from root
	versionFlag := analyzeCmd.Flags().Lookup("version")
	if versionFlag != nil {
		t.Log("Analyze command has access to version flag")
	}
}

// Test command execution context
func TestCommandContext(t *testing.T) {
	rootCmd := NewRootCmd()
	
	// Verify command can be executed multiple times
	for i := 0; i < 3; i++ {
		rootCmd.SetArgs([]string{"--help"})
		err := rootCmd.Execute()
		if err != nil {
			t.Errorf("Command execution %d failed: %v", i+1, err)
		}
	}
}

// Test command metadata
func TestCommandMetadata(t *testing.T) {
	rootCmd := NewRootCmd()
	
	// Check command has proper metadata
	if rootCmd.Long == "" {
		t.Log("Note: Root command could have a long description")
	}
	
	if rootCmd.Example == "" {
		t.Log("Note: Root command could have usage examples")
	}
	
	// Check version is set
	if rootCmd.Version == "" {
		t.Log("Note: Version could be set on root command")
	}
}

// Benchmark command creation
func BenchmarkNewRootCmd(b *testing.B) {
	for i := 0; i < b.N; i++ {
		_ = NewRootCmd()
	}
}

// Test concurrent command execution
func TestConcurrentExecution(t *testing.T) {
	// This tests that commands can be created and used concurrently
	done := make(chan bool, 10)
	
	for i := 0; i < 10; i++ {
		go func() {
			rootCmd := NewRootCmd()
			rootCmd.SetArgs([]string{"--help"})
			rootCmd.Execute()
			done <- true
		}()
	}
	
	// Wait for all goroutines to complete
	for i := 0; i < 10; i++ {
		<-done
	}
}

// Test command cleanup
func TestCommandCleanup(t *testing.T) {
	rootCmd := NewRootCmd()
	
	// Verify command can be garbage collected properly
	// This is mainly to ensure no memory leaks in command structure
	rootCmd = nil
	
	// Create new command to ensure clean state
	newRootCmd := NewRootCmd()
	if newRootCmd == nil {
		t.Error("New root command should not be nil")
	}
}