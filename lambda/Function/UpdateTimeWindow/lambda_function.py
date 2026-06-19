import os
import json
import boto3
from botocore.exceptions import ClientError
from dynamo_retry import dynamoRetry
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

USERS_TABLE = dynamodb.Table(USERS_TABLE_NAME)

MIN_TIME_WINDOW = 1
MAX_TIME_WINDOW = 7
DEFAULT_TIME_WINDOW = 3

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]

        body = json.loads(event.get("body", "{}"))

        timeWindow = body.get("timeWimdow", DEFAULT_TIME_WINDOW)

        if not isinstance(timeWindow, int) or timeWindow < MIN_TIME_WINDOW or timeWindow > MAX_TIME_WINDOW:
            return createResponse(400, f"timeWindow must be an integer between {MIN_TIME_WINDOW} and {MAX_TIME_WINDOW}", {"field": "timeWindow"})
    
        dynamoRetry(
            USERS_TABLE.update_item,
            Key={"userId": userId},
            UpdateExpression="SET timeWindow = :tw",
            ExpressionAttributeValues={":tw": timeWindow},
        )

        data = {
            "timeWindow": timeWindow
        }
        
        return createResponse(200, "Time window updated successfully", data)

    except ClientError as e:
        logger.exception({"message": str(e)})
        return createResponse(503, "Service temporarily unavailable, please retry", None)

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
        }),
        'headers': {"Access-Control-Allow-Origin": "*"}
    }
