"""Lambda function to send pipeline notifications."""

import json
import logging
import os
from typing import Any

import boto3

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda function handler.

    Args:
        event: Lambda event data
        context: Lambda context

    Returns:
        Dictionary containing the notification status
    """
    try:
        logger.info(json.dumps({"message": "Processing notification", "event": event}))

        # Get notification details
        status = event.get("status", "unknown")
        message = event.get("message", "No message provided")
        execution_id = event.get("execution", "unknown")
        error = event.get("error", {})

        # Format notification message
        subject = f"Entity Resolution Pipeline {status.upper()}"

        notification_message = {
            "status": status,
            "message": message,
            "execution_id": execution_id,
        }

        if error:
            notification_message["error"] = error

        # Send notification
        sns_client = boto3.client("sns")
        response = sns_client.publish(
            TopicArn=os.environ["SNS_TOPIC_ARN"],
            Subject=subject,
            Message=json.dumps(notification_message, indent=2),
        )

        logger.info(
            json.dumps(
                {
                    "message": "Notification sent",
                    "message_id": response["MessageId"],
                    "status": status,
                }
            )
        )

        return {
            "statusCode": 200,
            "body": {
                "status": "success",
                "message": "Notification sent successfully",
                "message_id": response["MessageId"],
            },
        }

    except Exception as e:
        logger.error(json.dumps({"message": "Failed to send notification", "error": str(e)}))

        raise
