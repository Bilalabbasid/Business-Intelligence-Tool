package cmd

import (
	"context"
	"crypto/sha256"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/spf13/cobra"
)

var restoreCmd = &cobra.Command{
	Use:   "restore",
	Short: "Restore database from backup",
	Long:  `Restore MongoDB or PostgreSQL database from backup file or S3`,
	Run:   runRestore,
}

var (
	restoreFile     string
	restoreS3Key    string
	restoreDbType   string
	targetMongoURI  string
	targetPgURI     string
	skipVerify      bool
)

func init() {
	restoreCmd.Flags().StringVar(&restoreFile, "file", "", "Local backup file to restore from")
	restoreCmd.Flags().StringVar(&restoreS3Key, "s3-key", "", "S3 key of backup file to restore")
	restoreCmd.Flags().StringVar(&restoreDbType, "db", "", "Database type: mongo or postgres (auto-detected if not specified)")
	restoreCmd.Flags().StringVar(&targetMongoURI, "mongo-uri", "", "Target MongoDB URI for restore")
	restoreCmd.Flags().StringVar(&targetPgURI, "pg-uri", "", "Target PostgreSQL URI for restore")
	restoreCmd.Flags().StringVar(&s3Bucket, "s3-bucket", "", "S3 bucket containing backup")
	restoreCmd.Flags().StringVar(&s3Region, "s3-region", "us-east-1", "S3 region")
	restoreCmd.Flags().BoolVar(&skipVerify, "skip-verify", false, "Skip backup verification before restore")
}

func runRestore(cmd *cobra.Command, args []string) {
	var filePath string
	var err error
	
	// Download from S3 if S3 key is provided
	if restoreS3Key != "" {
		if s3Bucket == "" {
			log.Fatal("S3 bucket must be specified when using S3 key")
		}
		filePath, err = downloadFromS3(restoreS3Key, s3Bucket, s3Region)
		if err != nil {
			log.Fatalf("Failed to download from S3: %v", err)
		}
		defer os.Remove(filePath) // Clean up downloaded file
		fmt.Printf("Downloaded backup from S3: %s\n", restoreS3Key)
	} else if restoreFile != "" {
		filePath = restoreFile
	} else {
		log.Fatal("Must specify either --file or --s3-key")
	}
	
	// Verify backup integrity unless skipped
	if !skipVerify {
		if err := verifyBackup(filePath); err != nil {
			log.Fatalf("Backup verification failed: %v", err)
		}
		fmt.Println("Backup verification successful")
	}
	
	// Auto-detect database type if not specified
	if restoreDbType == "" {
		restoreDbType = detectDatabaseType(filePath)
		if restoreDbType == "" {
			log.Fatal("Could not detect database type from filename. Please specify --db")
		}
	}
	
	// Perform restore based on database type
	switch restoreDbType {
	case "mongo":
		if err := restoreMongoDB(filePath); err != nil {
			log.Fatalf("MongoDB restore failed: %v", err)
		}
		fmt.Println("MongoDB restore completed successfully")
	case "postgres":
		if err := restorePostgreSQL(filePath); err != nil {
			log.Fatalf("PostgreSQL restore failed: %v", err)
		}
		fmt.Println("PostgreSQL restore completed successfully")
	default:
		log.Fatalf("Unsupported database type: %s", restoreDbType)
	}
}

func downloadFromS3(key, bucket, region string) (string, error) {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String(region),
	})
	if err != nil {
		return "", fmt.Errorf("failed to create AWS session: %v", err)
	}
	
	svc := s3.New(sess)
	
	// Create temporary file
	tmpFile, err := os.CreateTemp("", "backup-restore-*")
	if err != nil {
		return "", fmt.Errorf("failed to create temporary file: %v", err)
	}
	defer tmpFile.Close()
	
	// Download from S3
	result, err := svc.GetObjectWithContext(context.Background(), &s3.GetObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		os.Remove(tmpFile.Name())
		return "", fmt.Errorf("failed to download from S3: %v", err)
	}
	defer result.Body.Close()
	
	// Copy to temporary file
	if _, err := io.Copy(tmpFile, result.Body); err != nil {
		os.Remove(tmpFile.Name())
		return "", fmt.Errorf("failed to write downloaded data: %v", err)
	}
	
	return tmpFile.Name(), nil
}

func verifyBackup(filePath string) error {
	checksumPath := filePath + ".sha256"
	
	// Check if checksum file exists
	if _, err := os.Stat(checksumPath); os.IsNotExist(err) {
		// If S3 key was used, try to download checksum file
		if restoreS3Key != "" && s3Bucket != "" {
			checksumKey := restoreS3Key + ".sha256"
			downloadedChecksum, err := downloadFromS3(checksumKey, s3Bucket, s3Region)
			if err != nil {
				return fmt.Errorf("checksum file not found and could not download from S3: %v", err)
			}
			checksumPath = downloadedChecksum
			defer os.Remove(downloadedChecksum)
		} else {
			return fmt.Errorf("checksum file not found: %s", checksumPath)
		}
	}
	
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
	
	if strings.TrimSpace(string(expectedChecksum)) != actualChecksum {
		return fmt.Errorf("checksum mismatch: expected %s, got %s", 
			strings.TrimSpace(string(expectedChecksum)), actualChecksum)
	}
	
	return nil
}

func detectDatabaseType(filePath string) string {
	filename := filepath.Base(filePath)
	if strings.Contains(filename, "mongo") {
		return "mongo"
	}
	if strings.Contains(filename, "postgres") {
		return "postgres"
	}
	return ""
}

func restoreMongoDB(filePath string) error {
	if targetMongoURI == "" {
		targetMongoURI = os.Getenv("MONGO_URI")
	}
	if targetMongoURI == "" {
		return fmt.Errorf("MongoDB URI not provided (use --mongo-uri or MONGO_URI env var)")
	}
	
	// Build mongorestore command
	args := []string{
		"--uri", targetMongoURI,
		"--archive", filePath,
		"--drop", // Drop collections before restoring
	}
	
	// Check if file is gzipped
	if strings.HasSuffix(filePath, ".gz") || strings.Contains(filePath, ".archive") {
		args = append(args, "--gzip")
	}
	
	cmd := exec.Command("mongorestore", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	
	return cmd.Run()
}

func restorePostgreSQL(filePath string) error {
	if targetPgURI == "" {
		targetPgURI = os.Getenv("POSTGRES_URI")
	}
	if targetPgURI == "" {
		return fmt.Errorf("PostgreSQL URI not provided (use --pg-uri or POSTGRES_URI env var)")
	}
	
	var cmd *exec.Cmd
	
	// Handle compressed files
	if strings.HasSuffix(filePath, ".gz") {
		// Use zcat to decompress and pipe to psql
		zcatCmd := exec.Command("zcat", filePath)
		psqlCmd := exec.Command("psql", targetPgURI)
		
		psqlCmd.Stdin, _ = zcatCmd.StdoutPipe()
		psqlCmd.Stdout = os.Stdout
		psqlCmd.Stderr = os.Stderr
		
		if err := psqlCmd.Start(); err != nil {
			return fmt.Errorf("failed to start psql: %v", err)
		}
		
		if err := zcatCmd.Run(); err != nil {
			return fmt.Errorf("failed to decompress backup: %v", err)
		}
		
		return psqlCmd.Wait()
	} else {
		// Direct restore from uncompressed file
		cmd = exec.Command("psql", targetPgURI, "-f", filePath)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		
		return cmd.Run()
	}
}