package cmd

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/spf13/cobra"
)

var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List available backups",
	Long:  `List available backups from local directory or S3 bucket`,
	Run:   runList,
}

var (
	listLocal bool
	listS3    bool
)

func init() {
	listCmd.Flags().BoolVar(&listLocal, "local", false, "List local backups")
	listCmd.Flags().BoolVar(&listS3, "s3", false, "List S3 backups")
	listCmd.Flags().StringVar(&outputDir, "output", "/tmp/backups", "Local backup directory")
	listCmd.Flags().StringVar(&s3Bucket, "s3-bucket", "", "S3 bucket to list")
	listCmd.Flags().StringVar(&s3Region, "s3-region", "us-east-1", "S3 region")
}

func runList(cmd *cobra.Command, args []string) {
	if !listLocal && !listS3 {
		// Default to both if neither specified
		listLocal = true
		listS3 = s3Bucket != ""
	}
	
	if listLocal {
		fmt.Println("=== Local Backups ===")
		listLocalBackups()
		fmt.Println()
	}
	
	if listS3 {
		if s3Bucket == "" {
			fmt.Println("S3 bucket not specified, skipping S3 listing")
			return
		}
		fmt.Println("=== S3 Backups ===")
		listS3Backups()
	}
}

func listLocalBackups() {
	if _, err := os.Stat(outputDir); os.IsNotExist(err) {
		fmt.Printf("Local backup directory does not exist: %s\n", outputDir)
		return
	}
	
	files, err := filepath.Glob(filepath.Join(outputDir, "*.archive"))
	if err != nil {
		fmt.Printf("Error reading backup directory: %v\n", err)
		return
	}
	
	sqlFiles, err := filepath.Glob(filepath.Join(outputDir, "*.sql*"))
	if err == nil {
		files = append(files, sqlFiles...)
	}
	
	if len(files) == 0 {
		fmt.Printf("No backup files found in %s\n", outputDir)
		return
	}
	
	fmt.Printf("Found %d backup files in %s:\n\n", len(files), outputDir)
	
	for _, file := range files {
		info, err := os.Stat(file)
		if err != nil {
			continue
		}
		
		// Determine database type and format info
		filename := filepath.Base(file)
		dbType := "Unknown"
		if strings.Contains(filename, "mongo") {
			dbType = "MongoDB"
		} else if strings.Contains(filename, "postgres") {
			dbType = "PostgreSQL"
		}
		
		// Check for checksum file
		checksumExists := "No"
		if _, err := os.Stat(file + ".sha256"); err == nil {
			checksumExists = "Yes"
		}
		
		fmt.Printf("File: %s\n", filename)
		fmt.Printf("  Type: %s\n", dbType)
		fmt.Printf("  Size: %s\n", formatFileSize(info.Size()))
		fmt.Printf("  Modified: %s\n", info.ModTime().Format("2006-01-02 15:04:05"))
		fmt.Printf("  Checksum: %s\n", checksumExists)
		fmt.Println()
	}
}

func listS3Backups() {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String(s3Region),
	})
	if err != nil {
		fmt.Printf("Failed to create AWS session: %v\n", err)
		return
	}
	
	svc := s3.New(sess)
	
	input := &s3.ListObjectsV2Input{
		Bucket: aws.String(s3Bucket),
	}
	
	result, err := svc.ListObjectsV2WithContext(context.Background(), input)
	if err != nil {
		fmt.Printf("Failed to list S3 objects: %v\n", err)
		return
	}
	
	// Filter backup files (exclude checksums for main listing)
	var backupFiles []*s3.Object
	for _, obj := range result.Contents {
		if !strings.HasSuffix(*obj.Key, ".sha256") {
			// Check if it looks like a backup file
			key := *obj.Key
			if strings.Contains(key, "mongo") || strings.Contains(key, "postgres") ||
				strings.HasSuffix(key, ".archive") || strings.HasSuffix(key, ".sql") ||
				strings.HasSuffix(key, ".sql.gz") {
				backupFiles = append(backupFiles, obj)
			}
		}
	}
	
	if len(backupFiles) == 0 {
		fmt.Printf("No backup files found in s3://%s\n", s3Bucket)
		return
	}
	
	fmt.Printf("Found %d backup files in s3://%s:\n\n", len(backupFiles), s3Bucket)
	
	for _, obj := range backupFiles {
		// Determine database type
		key := *obj.Key
		dbType := "Unknown"
		if strings.Contains(key, "mongo") {
			dbType = "MongoDB"
		} else if strings.Contains(key, "postgres") {
			dbType = "PostgreSQL"
		}
		
		// Check for checksum file
		checksumExists := "No"
		checksumKey := key + ".sha256"
		for _, checkObj := range result.Contents {
			if *checkObj.Key == checksumKey {
				checksumExists = "Yes"
				break
			}
		}
		
		fmt.Printf("Key: %s\n", key)
		fmt.Printf("  Type: %s\n", dbType)
		fmt.Printf("  Size: %s\n", formatFileSize(*obj.Size))
		fmt.Printf("  Modified: %s\n", obj.LastModified.Format("2006-01-02 15:04:05"))
		fmt.Printf("  Checksum: %s\n", checksumExists)
		fmt.Printf("  Storage Class: %s\n", aws.StringValue(obj.StorageClass))
		fmt.Println()
	}
}

func formatFileSize(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}