# FIXED VERSION OF TERRAFORM EXAMPLE #1
# Fixes Applied:
#   1. Server-side encryption with KMS
#   2. Public access block enabled
#   3. Versioning enabled
#   4. Access logging enabled
#   5. Lifecycle rules for cost management
#   6. Required tags for tracking
#
# Compliance: CIS-AWS 2.1.1, 2.1.5, NIST SC-28, PCI-DSS 3.4

# FIXED: S3 bucket with secure defaults
resource "aws_s3_bucket" "data" {
  bucket = "company-data-bucket"

  # FIXED: Required tags for resource tracking
  tags = {
    Environment  = var.environment
    Owner        = "security-team"
    CostCenter   = "engineering"
    DataClass    = "confidential"
    Compliance   = "pci-dss"
  }
}

# FIXED: Server-side encryption with customer-managed KMS key
resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# FIXED: Block all public access
resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# FIXED: Enable versioning for recovery
resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}

# FIXED: Enable access logging
resource "aws_s3_bucket_logging" "data" {
  bucket = aws_s3_bucket.data.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "data-bucket-logs/"
}

# FIXED: Lifecycle rules for cost management
resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "archive-old-versions"
    status = "Enabled"

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# FIXED: KMS key for encryption
resource "aws_kms_key" "s3" {
  description             = "KMS key for S3 bucket encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Environment = var.environment
    Purpose     = "s3-encryption"
  }
}
