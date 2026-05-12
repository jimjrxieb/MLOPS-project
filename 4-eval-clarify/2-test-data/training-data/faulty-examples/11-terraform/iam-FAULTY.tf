# FAULTY TERRAFORM EXAMPLE #3
# Common Mistakes: Overprivileged IAM Configuration
# Issues:
#   1. Wildcard (*) actions
#   2. Wildcard (*) resources
#   3. No condition restrictions
#   4. Inline policy (hard to audit)
#   5. Trust policy too permissive
#   6. No MFA requirement
#   7. Long-lived access keys
#
# Severity: CRITICAL (privilege escalation, lateral movement)
# Compliance: CIS-AWS 1.16, NIST AC-6, SOC2 CC6.1

# BUG #1 & #2: Wildcard everything - admin access
resource "aws_iam_policy" "app_policy" {
  name        = "app-policy"
  description = "Application policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # BUG: Full admin access to S3
        Effect   = "Allow"
        Action   = ["s3:*"]
        Resource = ["*"]
      },
      {
        # BUG: Can read ANY secret
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = ["*"]
      },
      {
        # BUG: Full EC2 access
        Effect   = "Allow"
        Action   = ["ec2:*"]
        Resource = ["*"]
      },
      {
        # BUG: Can assume ANY role - privilege escalation
        Effect   = "Allow"
        Action   = ["sts:AssumeRole"]
        Resource = ["*"]
      }
    ]
  })
}

# BUG #5: Trust policy allows any AWS account
resource "aws_iam_role" "app_role" {
  name = "app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          # BUG: Any AWS account can assume this role!
          AWS = "*"
        }
        Action = "sts:AssumeRole"
        # BUG #3 & #6: No conditions, no MFA
      }
    ]
  })
}

# BUG #7: Long-lived access key
resource "aws_iam_access_key" "app_key" {
  user = aws_iam_user.app.name
  # No rotation, no expiry
}

# BUG #4: Inline policy - hard to audit
resource "aws_iam_user_policy" "inline_admin" {
  name   = "inline-admin"
  user   = aws_iam_user.app.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"  # CRITICAL: Full AWS admin
      Resource = "*"
    }]
  })
}
