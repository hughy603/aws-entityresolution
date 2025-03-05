# Step Functions State Machine
resource "aws_sfn_state_machine" "entity_resolution_pipeline" {
  name     = "${var.project_name}-pipeline"
  role_arn = aws_iam_role.step_functions.arn

  definition = jsonencode({
    Comment = "Entity Resolution Pipeline Orchestration"
    StartAt = "ExtractFromSnowflake"
    States = {
      ExtractFromSnowflake = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.lambda_handlers["extract"].function_name
          Payload = {
            "source_table.$" = "$$.Execution.Input.source_table"
          }
        }
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        Next       = "StartEntityResolutionJob"
        ResultPath = "$.extraction_result"
        ResultSelector = {
          "s3_key.$"            = "$.Payload.body.s3_key"
          "s3_bucket.$"         = "$.Payload.body.s3_bucket"
          "records_extracted.$" = "$.Payload.body.records_extracted"
        }
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "FailureState"
            ResultPath  = "$.error"
          }
        ]
      },
      StartEntityResolutionJob = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.lambda_handlers["process"].function_name
          Payload = {
            "body.$" = "$.extraction_result"
          }
        }
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        Next       = "CheckJobStatus"
        ResultPath = "$.process_result"
        ResultSelector = {
          "job_id.$"        = "$.Payload.body.job_id"
          "output_prefix.$" = "$.Payload.body.output_prefix"
        }
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "FailureState"
            ResultPath  = "$.error"
          }
        ]
      },
      CheckJobStatus = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.lambda_handlers["check_status"].function_name
          Payload = {
            "body" : {
              "job_id.$" = "$.process_result.job_id"
            },
            "TaskToken.$" = "$$.Task.Token"
          }
        }
        Next       = "IsJobSuccessful"
        ResultPath = "$.job_status"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "FailureState"
            ResultPath  = "$.error"
          }
        ]
      },
      IsJobSuccessful = {
        Type = "Choice",
        Choices = [
          {
            Variable     = "$.job_status.Payload.body.status",
            StringEquals = "completed",
            Next         = "LoadToSnowflake"
          }
        ],
        Default = "FailureState"
      },
      LoadToSnowflake = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.lambda_handlers["load"].function_name
          Payload = {
            "body" : {
              "output_location.$" = "$.job_status.Payload.body.output_location"
            }
          }
        }
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        Next       = "SuccessState"
        ResultPath = "$.load_result"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "FailureState"
            ResultPath  = "$.error"
          }
        ]
      },
      SuccessState = {
        Type       = "Succeed",
        OutputPath = "$.load_result.Payload.body"
      },
      FailureState = {
        Type  = "Fail",
        Error = "EntityResolutionPipelineFailed",
        Cause = "See the details in the error object"
      }
    }
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = var.default_tags
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/stepfunctions/${var.project_name}-pipeline"
  retention_in_days = 30
  tags              = var.default_tags
}

# IAM Role for Step Functions
resource "aws_iam_role" "step_functions" {
  name = "${var.project_name}-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = var.default_tags
}

# IAM Policy for Step Functions
resource "aws_iam_role_policy" "step_functions" {
  name = "${var.project_name}-step-functions-policy"
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
          for k, v in aws_lambda_function.lambda_handlers : v.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = ["*"]
      }
    ]
  })
}

# EventBridge Rule for Scheduled Execution
resource "aws_cloudwatch_event_rule" "pipeline_schedule" {
  name                = "${var.project_name}-pipeline-schedule"
  description         = "Schedule for entity resolution pipeline"
  schedule_expression = var.pipeline_schedule
  tags                = var.default_tags
}

resource "aws_cloudwatch_event_target" "pipeline_schedule" {
  rule      = aws_cloudwatch_event_rule.pipeline_schedule.name
  target_id = "StartPipeline"
  arn       = aws_sfn_state_machine.entity_resolution_pipeline.arn
  role_arn  = aws_iam_role.eventbridge.arn
}

# IAM Role for EventBridge
resource "aws_iam_role" "eventbridge" {
  name = "${var.project_name}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = var.default_tags
}

# IAM Policy for EventBridge
resource "aws_iam_role_policy" "eventbridge" {
  name = "${var.project_name}-eventbridge-policy"
  role = aws_iam_role.eventbridge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = [
          aws_sfn_state_machine.entity_resolution_pipeline.arn
        ]
      }
    ]
  })
}
