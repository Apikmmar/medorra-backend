import os
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from dynamo_retry import dynamoRetry
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

USERS_TABLE = dynamodb.Table(USERS_TABLE_NAME)

DEFAULT_TIME_WINDOW = 3

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        if event.get("triggerSource") != "PostConfirmation_ConfirmSignUp":
            return event

        attributes = event.get("request", {}).get("userAttributes", {})
        userId = attributes.get("sub")
        email = attributes.get("email")

        storeUserData(userId, email, attributes.get("custom:timezone"))

        return event

    except Exception as e:
        tracer.put_annotation("lambda_error", "true")
        tracer.put_annotation("lambda_name", context.function_name)
        tracer.put_metadata("event", event)
        tracer.put_metadata("message", str(e))
        logger.exception({"message": str(e)})
        return event

@tracer.capture_method
def storeUserData(userId, email, timezone_):
    if not userId:
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    item = {
        "userId": userId,
        "email": email,
        "distinctLoggingDays": 0,
        "timeWindow": DEFAULT_TIME_WINDOW,
        "timezone": timezone_ or "UTC",
        "createdAt": now,
    }

    try:
        dynamoRetry(
            USERS_TABLE.put_item,
            Item=item,
            ConditionExpression="attribute_not_exists(userId)",
        )
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise

    return item
