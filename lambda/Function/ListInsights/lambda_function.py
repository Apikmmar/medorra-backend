import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

INSIGHTS_TABLE_NAME = os.environ.get("INSIGHTS_TABLE_NAME")
USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

INSIGHTS_TABLE = dynamodb.Table(INSIGHTS_TABLE_NAME)
USERS_TABLE = dynamodb.Table(USERS_TABLE_NAME)

MINIMUM_LOGGING_DAYS = 14

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]

        totalDistinctDays = getDistinctLoggingDays(userId)
        thresholdMet = totalDistinctDays >= MINIMUM_LOGGING_DAYS
        daysRemaining = max(0, MINIMUM_LOGGING_DAYS - totalDistinctDays)

        if not thresholdMet:
            data = {
                "insights": [],
                "totalCount": 0,
                "thresholdMet": False,
                "daysRemaining": daysRemaining,
                "totalDistinctDays": totalDistinctDays,
            }
            return createResponse(200, f"{daysRemaining} more days needed", data)

        allInsights = getInsights(userId)

        activeInsights = [i for i in allInsights if i.get("status") != "dismissed"]

        data = {
            "insights": activeInsights,
            "totalCount": len(activeInsights),
            "thresholdMet": True,
            "daysRemaining": 0,
            "totalDistinctDays": totalDistinctDays,
        }

        if not activeInsights:
            return createResponse(200, "No patterns detected yet", data)

        return createResponse(200, "Insights retrieved successfully", data)

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
def getInsights(userId):
    response = dynamoRetry(
        INSIGHTS_TABLE.query,
        KeyConditionExpression=Key("userId").eq(userId),
        ScanIndexForward=False,
    )
    return response.get("Items", [])

@tracer.capture_method
def getDistinctLoggingDays(userId):
    user = dynamoRetry(
        USERS_TABLE.get_item,
        Key={"userId": userId},
    ).get("Item")

    if not user:
        return 0

    return int(user.get("distinctLoggingDays", 0))