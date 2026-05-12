# Expected fix for CKV_AWS_19: S3 bucket encryption
# JADE should generate something similar to this

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Validation criteria:
# - Must reference aws_s3_bucket.data.id
# - Must use aws_s3_bucket_server_side_encryption_configuration resource
# - Must specify sse_algorithm (AES256 or aws:kms)
# - HCL must be syntactically valid
