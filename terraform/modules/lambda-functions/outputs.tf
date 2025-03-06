output "lambda_functions" {
  description = "Map of Lambda function details"
  value = {
    load = {
      arn           = aws_lambda_function.load.arn
      function_name = aws_lambda_function.load.function_name
      role_arn      = aws_iam_role.load_lambda.arn
    }
    process = {
      arn           = aws_lambda_function.process.arn
      function_name = aws_lambda_function.process.function_name
      role_arn      = aws_iam_role.process_lambda.arn
    }
    check_status = {
      arn           = aws_lambda_function.check_status.arn
      function_name = aws_lambda_function.check_status.function_name
      role_arn      = aws_iam_role.check_status_lambda.arn
    }
    notify = {
      arn           = aws_lambda_function.notify.arn
      function_name = aws_lambda_function.notify.function_name
      role_arn      = aws_iam_role.notify_lambda.arn
    }
  }
}

output "cloudwatch_log_groups" {
  description = "Map of CloudWatch Log Group ARNs"
  value = {
    load         = aws_cloudwatch_log_group.load_lambda.arn
    process      = aws_cloudwatch_log_group.process_lambda.arn
    check_status = aws_cloudwatch_log_group.check_status_lambda.arn
    notify       = aws_cloudwatch_log_group.notify_lambda.arn
  }
}

output "check_status" {
  description = "Check status Lambda function details"
  value = {
    function_name = aws_lambda_function.check_status.function_name
    arn           = aws_lambda_function.check_status.arn
    invoke_arn    = aws_lambda_function.check_status.invoke_arn
  }
}

output "load_data" {
  description = "Load data Lambda function details"
  value = {
    function_name = aws_lambda_function.load_data.function_name
    arn           = aws_lambda_function.load_data.arn
    invoke_arn    = aws_lambda_function.load_data.invoke_arn
  }
}

output "process_data" {
  description = "Process data Lambda function details"
  value = {
    function_name = aws_lambda_function.process_data.function_name
    arn           = aws_lambda_function.process_data.arn
    invoke_arn    = aws_lambda_function.process_data.invoke_arn
  }
}

output "notify" {
  description = "Notification Lambda function details"
  value = {
    function_name = aws_lambda_function.notify.function_name
    arn           = aws_lambda_function.notify.arn
    invoke_arn    = aws_lambda_function.notify.invoke_arn
  }
}

output "function_names" {
  description = "List of Lambda function names"
  value = [
    aws_lambda_function.load_data.function_name,
    aws_lambda_function.process_data.function_name,
    aws_lambda_function.check_status.function_name,
    aws_lambda_function.notify.function_name
  ]
}

# Add a new output to provide a structured map of all Lambda functions
output "functions" {
  description = "Map of all Lambda functions with their details"
  value = {
    load_data = {
      function_name = aws_lambda_function.load_data.function_name
      arn           = aws_lambda_function.load_data.arn
      invoke_arn    = aws_lambda_function.load_data.invoke_arn
    }
    check_status = {
      function_name = aws_lambda_function.check_status.function_name
      arn           = aws_lambda_function.check_status.arn
      invoke_arn    = aws_lambda_function.check_status.invoke_arn
    }
    process_data = {
      function_name = aws_lambda_function.process_data.function_name
      arn           = aws_lambda_function.process_data.arn
      invoke_arn    = aws_lambda_function.process_data.invoke_arn
    }
    notify = {
      function_name = aws_lambda_function.notify.function_name
      arn           = aws_lambda_function.notify.arn
      invoke_arn    = aws_lambda_function.notify.invoke_arn
    }
  }
}
