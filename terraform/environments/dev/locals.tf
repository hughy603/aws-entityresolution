locals {
  enable_notifications = var.environment == "prod"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Owner       = "platform-team"
  }
}
