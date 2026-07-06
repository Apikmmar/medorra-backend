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

dynamodb = boto3.resource("dynamodb")

INSIGHTS_TABLE = dynamodb.Table(INSIGHTS_TABLE_NAME)

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]

        allInsights = getInsights(userId)

        activeInsights = [i for i in allInsights if i.get("status") != "dismissed"]

        if not activeInsights:
            return createResponse(200, "No patterns detected yet", {"insights": [], "totalCount": 0})

        data = {
            "insights": activeInsights,
            "totalCount": len(activeInsights),
        }

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