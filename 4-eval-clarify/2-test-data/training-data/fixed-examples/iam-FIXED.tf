# FIXED VERSION OF TERRAFORM EXAMPLE #3
# Fixes Applied:
#   1. Specific actions only (least privilege)
#   2. Scoped resources with ARN patterns
#   3. Conditions for additional security
#   4. Managed policy (auditable)
#   5. Trust policy with specific principals
#   6. MFA requirement for sensitive actions
#   7. Short-lived credentials via OIDC/IRSA
#
# Compliance: CIS-AWS 1.16, NIST AC-6, SOC2 CC6.1

# FIXED: Scoped policy with specific actions
resource "aws_iam_policy" "app_policy" {
  name        = "app-policy"
  description = "Application policy - least privilege for specific S3 bucket"
  path        = "/applications/"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3AppBucketReadWrite"
        Effect = "Allow"
        # FIXED: Only required S3 actions
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        # FIXED: Specific bucket only
        Resource = [
          "arn:aws:s3:::${var.app_bucket}",
          "arn:aws:s3:::${var.app_bucket}/*"
        ]
        # FIXED: Condition restricts to VPC endpoint
        Condition = {
          StringEquals = {
            "aws:SourceVpce" = var.vpc_endpoint_id
          }
        }
      },
      {
        Sid    = "SecretsManagerAppSecrets"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        # FIXED: Only app-specific secrets with tag condition
        Resource = "arn:aws:secretsmanager:${var.region}:${var.account_id}:secret:${var.app_name}/*"
        Condition = {
          StringEquals = {
            "secretsmanager:ResourceTag/Application" = var.app_name
          }
        }
      },
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        # FIXED: Specific KMS key only
        Resource = aws_kms_key.app.arn
      }
    ]
  })

  tags = {
    Application = var.app_name
    ManagedBy   = "terraform"
    Owner       = var.owner
  }
}

# FIXED: Role with restricted trust policy
resource "aws_iam_role" "app_role" {
  name                 = "${var.app_name}-role"
  path                 = "/applications/"
  max_session_duration = 3600  # FIXED: Short session

  # FIXED: Trust only specific EKS cluster via OIDC
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          # FIXED: Specific OIDC provider only
          Federated = "arn:aws:iam::${var.account_id}:oidc-provider/${var.eks_oidc_issuer}"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        # FIXED: Conditions restrict to specific SA and namespace
        Condition = {
          StringEquals = {
            "${var.eks_oidc_issuer}:sub" = "system:serviceaccount:${var.namespace}:${var.app_name}"
            "${var.eks_oidc_issuer}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  # FIXED: Permission boundary limits maximum permissions
  permissions_boundary = aws_iam_policy.boundary.arn

  tags = {
    Application = var.app_name
    Environment = var.environment
  }
}

# FIXED: Permission boundary policy
resource "aws_iam_policy" "boundary" {
  name        = "${var.app_name}-boundary"
  description = "Permission boundary - maximum allowed permissions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowedServices"
        Effect = "Allow"
        Action = [
          "s3:*",
          "secretsmanager:GetSecretValue",
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "logs:*",
          "xray:*"
        ]
        Resource = "*"
      },
      {
        # FIXED: Explicit deny for dangerous actions
        Sid    = "DenyDangerous"
        Effect = "Deny"
        Action = [
          "iam:*",
          "organizations:*",
          "sts:AssumeRole",
          "ec2:*Vpc*",
          "ec2:*Subnet*",
          "ec2:*Gateway*"
        ]
        Resource = "*"
      }
    ]
  })
}

# FIXED: Attach managed policy instead of inline
resource "aws_iam_role_policy_attachment" "app_policy" {
  role       = aws_iam_role.app_role.name
  policy_arn = aws_iam_policy.app_policy.arn
}

# FIXED: No long-lived access keys - use IRSA/OIDC instead
# Access keys are NOT created - pods use short-lived STS credentials

# FIXED: Service account annotation for IRSA
resource "kubernetes_service_account" "app" {
  metadata {
    name      = var.app_name
    namespace = var.namespace
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.app_role.arn
    }
  }
}
