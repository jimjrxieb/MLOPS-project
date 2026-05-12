# FAULTY TERRAFORM EXAMPLE #1
# Common Mistakes: Insecure S3 Bucket Configuration
# Issues:
#   1. No server-side encryption
#   2. No public access block
#   3. No versioning enabled
#   4. No logging enabled
#   5. Missing lifecycle rules
#   6. No tags for resource tracking
#
# Severity: CRITICAL (data breach risk, Capital One pattern)
# Compliance: CIS-AWS 2.1.1, 2.1.5, NIST SC-28

resource "aws_s3_bucket" "data" {
  bucket = "company-data-bucket"

  # BUG #6: No tags - resource sprawl, no cost tracking
}

# BUG #1: No encryption - data at rest exposed
# Missing: aws_s3_bucket_server_side_encryption_configuration

# BUG #2: No public access block - potential data leak
# Missing: aws_s3_bucket_public_access_block

# BUG #3: No versioning - no recovery from accidental deletion
# Missing: aws_s3_bucket_versioning

# BUG #4: No logging - no audit trail
# Missing: aws_s3_bucket_logging

# BUG #5: No lifecycle rules - storage cost explosion
# Missing: aws_s3_bucket_lifecycle_configuration
