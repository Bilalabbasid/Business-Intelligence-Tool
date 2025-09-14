package cmd

import (
	"crypto/sha256"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/spf13/cobra"
)

var verifyCmd = &cobra.Command{
	Use:   "verify",
	Short: "Verify backup file integrity",
	Long:  `Verify backup file integrity using SHA256 checksums`,
	Run:   runVerify,
}

var (
	verifyFile string
	generateChecksum bool
)

func init() {
	verifyCmd.Flags().StringVar(&verifyFile, "file", "", "Backup file to verify")
	verifyCmd.Flags().BoolVar(&generateChecksum, "generate", false, "Generate checksum file if missing")
	verifyCmd.MarkFlagRequired("file")
}

func runVerify(cmd *cobra.Command, args []string) {
	checksumPath := verifyFile + ".sha256"
	
	// Check if checksum file exists
	if _, err := os.Stat(checksumPath); os.IsNotExist(err) {
		if generateChecksum {
			fmt.Printf("Checksum file not found. Generating %s...\n", checksumPath)
			if err := createChecksum(verifyFile); err != nil {
				fmt.Printf("Error generating checksum: %v\n", err)
				os.Exit(1)
			}
			fmt.Printf("Checksum file generated: %s\n", checksumPath)
			return
		} else {
			fmt.Printf("Error: Checksum file not found: %s\n", checksumPath)
			fmt.Println("Use --generate to create a new checksum file")
			os.Exit(1)
		}
	}
	
	// Verify existing checksum
	if err := verifyChecksum(verifyFile, checksumPath); err != nil {
		fmt.Printf("Verification failed: %v\n", err)
		os.Exit(1)
	}
	
	fmt.Printf("✓ Backup file verification successful: %s\n", verifyFile)
}

func verifyChecksum(filePath, checksumPath string) error {
	// Read expected checksum
	expectedChecksum, err := os.ReadFile(checksumPath)
	if err != nil {
		return fmt.Errorf("failed to read checksum file: %v", err)
	}
	
	// Calculate actual checksum
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open backup file: %v", err)
	}
	defer file.Close()
	
	hash := sha256.New()
	if _, err := io.Copy(hash, file); err != nil {
		return fmt.Errorf("failed to calculate checksum: %v", err)
	}
	
	actualChecksum := fmt.Sprintf("%x", hash.Sum(nil))
	expectedStr := strings.TrimSpace(string(expectedChecksum))
	
	if expectedStr != actualChecksum {
		return fmt.Errorf("checksum mismatch:\n  Expected: %s\n  Actual:   %s", expectedStr, actualChecksum)
	}
	
	return nil
}