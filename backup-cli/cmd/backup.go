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
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/spf13/cobra"
)

var backupCmd = &cobra.Command{
	Use:   "backup",
	Short: "Create database backups",
	Long:  `Create backups of MongoDB and PostgreSQL databases with cloud storage upload`,
	Run:   runBackup,
}

var (
	dbType      string
	mongoURI    string
	pgURI       string
	outputDir   string
	s3Bucket    string
	s3Region    string
	encrypt     bool
	compress    bool
)

func init() {
	backupCmd.Flags().StringVar(&dbType, "db", "mongo", "Database type: mongo, postgres, or both")
	backupCmd.Flags().StringVar(&mongoURI, "mongo-uri", "", "MongoDB connection URI")
	backupCmd.Flags().StringVar(&pgURI, "pg-uri", "", "PostgreSQL connection URI")
	backupCmd.Flags().StringVar(&outputDir, "output", "/tmp/backups", "Output directory for backups")
	backupCmd.Flags().StringVar(&s3Bucket, "s3-bucket", "", "S3 bucket for backup storage")
	backupCmd.Flags().StringVar(&s3Region, "s3-region", "us-east-1", "S3 region")
	backupCmd.Flags().BoolVar(&encrypt, "encrypt", false, "Encrypt backup files")
	backupCmd.Flags().BoolVar(&compress, "compress", true, "Compress backup files")
}

func runBackup(cmd *cobra.Command, args []string) {
	timestamp := time.Now().Format("20060102-150405")
	
	// Ensure output directory exists
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		log.Fatalf("Failed to create output directory: %v", err)
	}
	
	var backupPaths []string
	
	// Backup MongoDB
	if dbType == "mongo" || dbType == "both" {
		if mongoURI == "" {
			mongoURI = os.Getenv("MONGO_URI")
		}
		if mongoURI == "" {
			log.Fatal("MongoDB URI not provided (use --mongo-uri or MONGO_URI env var)")
		}
		
		mongoPath, err := backupMongoDB(mongoURI, timestamp)
		if err != nil {
			log.Fatalf("MongoDB backup failed: %v", err)
		}
		backupPaths = append(backupPaths, mongoPath)
		fmt.Printf("MongoDB backup created: %s\n", mongoPath)
	}
	
	// Backup PostgreSQL
	if dbType == "postgres" || dbType == "both" {
		if pgURI == "" {
			pgURI = os.Getenv("POSTGRES_URI")
		}
		if pgURI == "" {
			log.Fatal("PostgreSQL URI not provided (use --pg-uri or POSTGRES_URI env var)")
		}
		
		pgPath, err := backupPostgreSQL(pgURI, timestamp)
		if err != nil {
			log.Fatalf("PostgreSQL backup failed: %v", err)
		}
		backupPaths = append(backupPaths, pgPath)
		fmt.Printf("PostgreSQL backup created: %s\n", pgPath)
	}
	
	// Upload to S3 if configured
	if s3Bucket != "" {
		for _, path := range backupPaths {
			if err := uploadToS3(path, s3Bucket, s3Region); err != nil {
				log.Printf("Failed to upload %s to S3: %v", path, err)
			} else {
				fmt.Printf("Backup uploaded to S3: s3://%s/%s\n", s3Bucket, filepath.Base(path))
			}
		}
	}
	
	fmt.Println("Backup completed successfully")
}

func backupMongoDB(uri, timestamp string) (string, error) {
	// Parse database name from URI (simplified)
	dbName := "default"
	if strings.Contains(uri, "/") {
		parts := strings.Split(uri, "/")
		if len(parts) > 1 && parts[len(parts)-1] != "" {
			dbName = strings.Split(parts[len(parts)-1], "?")[0]
		}
	}
	
	filename := fmt.Sprintf("mongo_%s_%s.archive", dbName, timestamp)
	outputPath := filepath.Join(outputDir, filename)
	
	// Build mongodump command
	args := []string{
		"--uri", uri,
		"--archive", outputPath,
	}
	
	if compress {
		args = append(args, "--gzip")
	}
	
	cmd := exec.Command("mongodump", args...)
	cmd.Stderr = os.Stderr
	
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("mongodump failed: %v", err)
	}
	
	// Calculate and store checksum
	if err := createChecksum(outputPath); err != nil {
		log.Printf("Warning: Failed to create checksum for %s: %v", outputPath, err)
	}
	
	return outputPath, nil
}

func backupPostgreSQL(uri, timestamp string) (string, error) {
	// Parse database name from URI
	dbName := "postgres"
	if strings.Contains(uri, "/") {
		parts := strings.Split(uri, "/")
		if len(parts) > 1 && parts[len(parts)-1] != "" {
			dbName = strings.Split(parts[len(parts)-1], "?")[0]
		}
	}
	
	filename := fmt.Sprintf("postgres_%s_%s.sql", dbName, timestamp)
	if compress {
		filename += ".gz"
	}
	outputPath := filepath.Join(outputDir, filename)
	
	// Build pg_dump command
	args := []string{
		uri,
		"--verbose",
		"--clean",
		"--if-exists",
		"--create",
	}
	
	cmd := exec.Command("pg_dump", args...)
	
	// Set up output redirection
	outFile, err := os.Create(outputPath)
	if err != nil {
		return "", fmt.Errorf("failed to create output file: %v", err)
	}
	defer outFile.Close()
	
	if compress {
		// Use gzip compression
		gzipCmd := exec.Command("gzip")
		gzipCmd.Stdin, _ = cmd.StdoutPipe()
		gzipCmd.Stdout = outFile
		gzipCmd.Stderr = os.Stderr
		
		if err := gzipCmd.Start(); err != nil {
			return "", fmt.Errorf("failed to start gzip: %v", err)
		}
		
		cmd.Stderr = os.Stderr
		if err := cmd.Start(); err != nil {
			return "", fmt.Errorf("failed to start pg_dump: %v", err)
		}
		
		if err := cmd.Wait(); err != nil {
			return "", fmt.Errorf("pg_dump failed: %v", err)
		}
		
		if err := gzipCmd.Wait(); err != nil {
			return "", fmt.Errorf("gzip failed: %v", err)
		}
	} else {
		cmd.Stdout = outFile
		cmd.Stderr = os.Stderr
		
		if err := cmd.Run(); err != nil {
			return "", fmt.Errorf("pg_dump failed: %v", err)
		}
	}
	
	// Calculate and store checksum
	if err := createChecksum(outputPath); err != nil {
		log.Printf("Warning: Failed to create checksum for %s: %v", outputPath, err)
	}
	
	return outputPath, nil
}

func createChecksum(filePath string) error {
	file, err := os.Open(filePath)
	if err != nil {
		return err
	}
	defer file.Close()
	
	hash := sha256.New()
	if _, err := io.Copy(hash, file); err != nil {
		return err
	}
	
	checksum := fmt.Sprintf("%x", hash.Sum(nil))
	checksumPath := filePath + ".sha256"
	
	return os.WriteFile(checksumPath, []byte(checksum), 0644)
}

func uploadToS3(filePath, bucket, region string) error {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String(region),
	})
	if err != nil {
		return fmt.Errorf("failed to create AWS session: %v", err)
	}
	
	svc := s3.New(sess)
	
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open file: %v", err)
	}
	defer file.Close()
	
	key := filepath.Base(filePath)
	
	_, err = svc.PutObjectWithContext(context.Background(), &s3.PutObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
		Body:   file,
	})
	
	if err != nil {
		return fmt.Errorf("failed to upload to S3: %v", err)
	}
	
	// Also upload checksum file
	checksumPath := filePath + ".sha256"
	if _, err := os.Stat(checksumPath); err == nil {
		if err := uploadToS3(checksumPath, bucket, region); err != nil {
			log.Printf("Warning: Failed to upload checksum file: %v", err)
		}
	}
	
	return nil
}