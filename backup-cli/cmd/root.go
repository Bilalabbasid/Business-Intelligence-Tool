package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "backup-cli",
	Short: "Enterprise backup and restore CLI for BI Platform",
	Long: `backup-cli is a production-grade tool for backing up and restoring 
MongoDB and PostgreSQL databases with cloud storage integration and encryption support.

Features:
- Backup MongoDB and PostgreSQL databases
- Upload to AWS S3 or Google Cloud Storage
- KMS encryption and decryption
- Backup verification and integrity checks
- Scheduled backup support
- Cross-region disaster recovery`,
}

func Execute() error {
	return rootCmd.Execute()
}

func init() {
	rootCmd.AddCommand(backupCmd)
	rootCmd.AddCommand(restoreCmd)
	rootCmd.AddCommand(verifyCmd)
	rootCmd.AddCommand(listCmd)
}