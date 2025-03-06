{
  "Comment": "Entity Resolution Workflow",
  "StartAt": "LoadData",
  "States": {
    "LoadData": {
      "Type": "Task",
      "Resource": "${load_data_lambda_arn}",
      "Next": "WaitForProcessing",
      "Retry": [
        {
          "ErrorEquals": ["States.ALL"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "NotifyError"
        }
      ]
    },
    "WaitForProcessing": {
      "Type": "Wait",
      "Seconds": 30,
      "Next": "CheckStatus"
    },
    "CheckStatus": {
      "Type": "Task",
      "Resource": "${check_status_lambda_arn}",
      "Next": "IsComplete",
      "Retry": [
        {
          "ErrorEquals": ["States.ALL"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "NotifyError"
        }
      ]
    },
    "IsComplete": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.status",
          "StringEquals": "SUCCEEDED",
          "Next": "ProcessOutput"
        },
        {
          "Variable": "$.status",
          "StringEquals": "FAILED",
          "Next": "NotifyError"
        }
      ],
      "Default": "WaitForProcessing"
    },
    "ProcessOutput": {
      "Type": "Task",
      "Resource": "${process_data_lambda_arn}",
      "End": true,
      "Retry": [
        {
          "ErrorEquals": ["States.ALL"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "NotifyError"
        }
      ]
    },
    "NotifyError": {
      "Type": "Task",
      "Resource": "${notify_lambda_arn}",
      "End": true
    }
  }
}
