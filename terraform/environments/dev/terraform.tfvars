project_name = "entity-resolution"
aws_region   = "us-west-2"

s3_bucket_name   = "dev-entity-resolution-data"
s3_input_prefix  = "input/"
s3_output_prefix = "output/"

er_workflow_name = "dev-matching-workflow"
er_schema_name   = "customer-matching"
er_entity_attributes = [
  "name",
  "address",
  "phone",
  "email"
]

# VPC Configuration (optional)
# subnet_ids = ["subnet-12345678", "subnet-87654321"]
# vpc_id     = "vpc-12345678"

# SNS Topic for notifications (optional)
# notification_topic_arn = "arn:aws:sns:us-west-2:123456789012:entity-resolution-notifications"

default_tags = {
  Environment = "dev"
  Project     = "entity-resolution"
  ManagedBy   = "terraform"
  Team        = "data-engineering"
}
