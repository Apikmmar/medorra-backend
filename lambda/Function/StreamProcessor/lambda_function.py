import os
import json
import boto3
from botocore.exceptions import ClientError
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME")

dynamodb = boto3.resource("dynamodb")
eventbridge = boto3.client("events")

USERS_TABLE = dynamodb.Table(USERS_TABLE_NAME)
MINIMUM_LOGGING_DAYS = 14

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        records = event.get("Records", [])
        processedUsers = set()

        for record in records:
            eventName = record.get("eventName")

            if eventName not in ("INSERT", "MODIFY"):
                continue
            
            newImage = record.get("dynamodb", {}).get("NewImage", {})
            userId = record.get("userId", {}).get("S")

            if not userId or userId in processedUsers:
                continue

            processedUsers.add(userId)

            if not isEligible(userId):
                continue

            eventbridge.put_events(
                Entries=[
                    {
                        "Source": "medorra.entries",
                        "DetailType": "EntryCreated",
                        "Detail": json.dumps({"userId": userId}),
                        "EventBusName": EVENT_BUS_NAME,
                    }
                ]
            )

        return createResponse(200, "Login Successful", data)

    except ClientError as e:
        logger.exception({"message": str(e)})
        return createResponse(503, "Service temporarily unavailable", None)

    except Exception as e:
        tracer.put_annotation("lambda_error", "true")
        tracer.put_annotation("lambda_name", context.function_name)
        tracer.put_metadata("event", event)
        tracer.put_metadata("message", str(e))
        logger.exception({"message": str(e)})
        return createResponse(500, "The server encountered an unexpected condition that prevented it from fulfilling your request.", None)

@tracer.capture_method
def createResponse(statusCode, message, data):
    return {
        'statusCode': statusCode,
        'body': json.dumps({
            'status': True if statusCode == 200 else False,
            'message': message,
            'data': data
        }, cls=DecimalEncoder),
        'headers': {"Access-Control-Allow-Origin": "*"}
    }

@tracer.capture_method
def isEligible(userId):
    response = dynamoRetry(
        USERS_TABLE.get_item,
        Key={"userId": userId}
    ).get("Item")

    if not response:
        return False

    distinctLoggingDays = user.get("distinctLoggingDays")

    return distinctLoggingDays >= MINIMUM_LOGGING_DAYS