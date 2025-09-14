# Backup CLI

Enterprise-grade backup and restore tool for the BI Platform.

## Features

- **Database Support**: MongoDB and PostgreSQL
- **Cloud Storage**: AWS S3 integration with automatic upload
- **Integrity Verification**: SHA256 checksums for all backups
- **Compression**: Gzip compression for PostgreSQL backups
- **Encryption**: KMS encryption support (planned)
- **Cross-Platform**: Works on Linux, macOS, and Windows

## Installation

```bash
# Build from source
go build -o backup-cli

# Or install directly
go install
```

## Usage

### Backup Operations

```bash
# Backup MongoDB
./backup-cli backup --db mongo --mongo-uri "mongodb://localhost:27017/mydb"

# Backup PostgreSQL
./backup-cli backup --db postgres --pg-uri "postgres://user:pass@localhost:5432/mydb"

# Backup both databases
./backup-cli backup --db both --mongo-uri "..." --pg-uri "..."

# With S3 upload
./backup-cli backup --db mongo --mongo-uri "..." --s3-bucket my-backups --s3-region us-east-1
```

### Restore Operations

```bash
# Restore from local file
./backup-cli restore --file /tmp/backups/mongo_mydb_20240315-120000.archive --mongo-uri "..."

# Restore from S3
./backup-cli restore --s3-key mongo_mydb_20240315-120000.archive --s3-bucket my-backups --mongo-uri "..."
```

### Verification

```bash
# Verify backup integrity
./backup-cli verify --file /tmp/backups/mongo_mydb_20240315-120000.archive

# Generate checksum if missing
./backup-cli verify --file backup.archive --generate
```

### List Backups

```bash
# List local backups
./backup-cli list --local

# List S3 backups
./backup-cli list --s3 --s3-bucket my-backups

# List both
./backup-cli list --local --s3 --s3-bucket my-backups
```

## Configuration

Environment variables:
- `MONGO_URI`: Default MongoDB connection URI
- `POSTGRES_URI`: Default PostgreSQL connection URI
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_REGION`: Default AWS region

## Dependencies

The tool requires the following external commands to be available in PATH:
- `mongodump` and `mongorestore` for MongoDB operations
- `pg_dump` and `psql` for PostgreSQL operations
- `gzip` and `zcat` for compression (usually available on Unix systems)

## Security

- Backup files are verified with SHA256 checksums
- S3 uploads support IAM roles and credentials
- KMS encryption support (coming soon)
- Network connections use SSL/TLS when configured