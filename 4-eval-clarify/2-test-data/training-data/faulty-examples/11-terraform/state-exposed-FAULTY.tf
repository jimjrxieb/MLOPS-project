# FAULTY: Terraform backend with publicly accessible S3 bucket and no encryption
terraform {
  backend "s3" {
    bucket = "acme-terraform-state"  # No versioning, no encryption
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
    # MISSING: encrypt = true
    # MISSING: dynamodb_table for locking
    # MISSING: kms_key_id for encryption
  }
}

# S3 bucket for state - PUBLIC AND UNENCRYPTED
resource "aws_s3_bucket" "terraform_state" {
  bucket = "acme-terraform-state"
  # ISSUE: No ACL restriction, defaults to public in older AWS provider versions
}

# MISSING: aws_s3_bucket_public_access_block
# MISSING: aws_s3_bucket_versioning
# MISSING: aws_s3_bucket_server_side_encryption_configuration
# MISSING: aws_dynamodb_table for state locking

output "state_bucket_arn" {
  value = aws_s3_bucket.terraform_state.arn
  # ISSUE: Outputs sensitive infrastructure info
}
