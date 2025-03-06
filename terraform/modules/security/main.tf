locals {
  common_lambda_permissions = [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ]

  s3_permissions = [
    "s3:GetObject",
    "s3:PutObject",
    "s3:ListBucket"
  ]

  entity_resolution_permissions = var.enable_entity_resolution ? [
    "entityresolution:StartMatchingJob",
    "entityresolution:GetMatchingJob",
    "entityresolution:ListMatchingJobs"
  ] : []

  vpc_permissions = var.enable_vpc_access ? [
    "ec2:CreateNetworkInterface",
    "ec2:DescribeNetworkInterfaces",
    "ec2:DeleteNetworkInterface"
  ] : []
}

# Lambda execution role for each function
resource "aws_iam_role" "lambda" {
  for_each = var.lambda_functions

  name = "${var.config.iam_roles.lambda}-${each.key}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = var.config.common_tags
}

# Lambda execution policies
resource "aws_iam_role_policy" "lambda" {
  for_each = var.lambda_functions

  name = "${var.config.iam_roles.lambda}-${each.key}-policy"
  role = aws_iam_role.lambda[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = concat(
          local.common_lambda_permissions,
          local.s3_permissions,
          contains(each.value.permissions, "entity_resolution") ? local.entity_resolution_permissions : [],
          var.enable_vpc_access ? local.vpc_permissions : []
        )
        Resource = contains(each.value.permissions, "s3") ? [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ] : ["*"]
      }
    ]
  })
}

# Step Functions execution role
resource "aws_iam_role" "step_functions" {
  name = var.config.iam_roles.step_functions

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "states.amazonaws.com"
      }
    }]
  })

  tags = var.config.common_tags
}

# Step Functions execution policy
resource "aws_iam_role_policy" "step_functions" {
  name = "${var.config.iam_roles.step_functions}-policy"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          for function in aws_iam_role.lambda : function.arn
        ]
      }
    ]
  })
}

# Glue execution role
resource "aws_iam_role" "glue" {
  name = var.config.iam_roles.glue

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "glue.amazonaws.com"
      }
    }]
  })

  tags = var.config.common_tags
}

# Glue execution policy
resource "aws_iam_role_policy" "glue" {
  name = "${var.config.iam_roles.glue}-policy"
  role = aws_iam_role.glue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "glue:*",
          "s3:GetBucketLocation",
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "arn:aws:glue:*:*:*",
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = ["arn:aws:logs:*:*:*"]
      }
    ]
  })
}
