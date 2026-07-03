import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

USERS_TABLE = dynamodb.Table(USERS_TABLE_NAME)

MINIMUM_LOGGING_DAYS = 14

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]

        user = getUser(userId)

        if not user:
            return createResponse(404, "User not found", None)

        distinctLoggingDays = user.get("distinctLoggingDays", 0)
        remainingDays = max(0, MINIMUM_LOGGING_DAYS - distinctLoggingDays)

        if remainingDays > 0:
            data = {
                "eligible": False,
                "distinctLoggingDays": distinctLoggingDays,
                "remainingDays": remainingDays,
                "message": f"{remainingDays} more days of logging needed before pattern analysis can begin",
            }

            return createResponse(200, "Threshold not met", data)
        
        data = {
            "eligible": True,
            "distinctLoggingDays": distinctLoggingDays,
            "remainingDays": 0,
        }

        return createResponse(200, "Threshold met", data)

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
def getUser(userId):
    response = dynamoRetry(
            USERS_TABLE.get_item,
            Key={"userId": userId}
        ).get("Item")

    return response