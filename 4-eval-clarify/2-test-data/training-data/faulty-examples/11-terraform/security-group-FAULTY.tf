# FAULTY TERRAFORM EXAMPLE #2
# Common Mistakes: Insecure Security Group Configuration
# Issues:
#   1. Ingress from 0.0.0.0/0 (world-open)
#   2. All ports open (0-65535)
#   3. No egress restrictions
#   4. Missing description
#   5. No lifecycle rules
#
# Severity: CRITICAL (direct attack vector)
# Compliance: CIS-AWS 5.2, NIST SC-7

resource "aws_security_group" "app" {
  name        = "app-sg"
  vpc_id      = var.vpc_id

  # BUG #1 & #2: Wide open to the world on all ports
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # CRITICAL: World accessible
  }

  # BUG #3: No egress restrictions - data exfiltration risk
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # BUG #4: Missing description
  # BUG #5: No lifecycle prevent_destroy
}
