output "lambda_roles" {
  description = "Map of Lambda IAM role ARNs"
  value = {
    for k, v in aws_iam_role.lambda : k => {
      arn  = v.arn
      name = v.name
    }
  }
}

output "step_functions_role" {
  description = "Step Functions IAM role"
  value = {
    arn  = aws_iam_role.step_functions.arn
    name = aws_iam_role.step_functions.name
  }
}

output "glue_role" {
  description = "Glue IAM role"
  value = {
    arn  = aws_iam_role.glue.arn
    name = aws_iam_role.glue.name
  }
}
