# FIXED VERSION OF TERRAFORM EXAMPLE #2
# Fixes Applied:
#   1. Ingress restricted to specific CIDR (VPC only)
#   2. Only required ports open (443, 8080)
#   3. Egress restricted to required destinations
#   4. Descriptions on all rules
#   5. Lifecycle rules to prevent accidental deletion
#
# Compliance: CIS-AWS 5.2, NIST SC-7, PCI-DSS 1.3

resource "aws_security_group" "app" {
  name        = "app-sg"
  description = "Security group for application tier - allows HTTPS from VPC only"
  vpc_id      = var.vpc_id

  # FIXED: Only HTTPS from internal VPC CIDR
  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]  # Internal only
  }

  # FIXED: Application port from specific subnets
  ingress {
    description     = "App port from private subnets"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]  # ALB only
  }

  # FIXED: Restricted egress - only what's needed
  egress {
    description = "HTTPS to AWS services"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Required for AWS API calls
  }

  egress {
    description     = "Database access"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.db.id]
  }

  # FIXED: Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
    create_before_destroy = true
  }

  tags = {
    Name        = "app-sg"
    Environment = var.environment
    ManagedBy   = "terraform"
    Compliance  = "cis-aws-5.2"
  }
}
