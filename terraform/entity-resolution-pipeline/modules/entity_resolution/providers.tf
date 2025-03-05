terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Comment regarding Entity Resolution resources:
# As of this version, AWS Provider may not support aws_entityresolution* resources yet.
# You may need to use a custom provider or AWS CLI/SDK directly.
# This can be addressed by using local-exec provisioners or null resources.
