import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from dynamo_retry import dynamoRetry
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

dynamodb = boto3.resource("dynamodb")

SLEEP_TABLE_NAME = os.environ.get("SLEEP_TABLE_NAME")
SLEEP_TABLE = dynamodb.Table(SLEEP_TABLE_NAME)

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]

        pathParams = event.get("pathParameters") or {}
        entryId = pathParams.get("entryId")

        if not entryId:
            return createResponse(400, "entryId is required", {"field": "entryId"})

        existing = findEntry(userId, entryId)

        if not existing:
            return createResponse(404, "Entry not found", None)

        deleteSleepData(existing, userId)

        return createResponse(200, "Sleep entry deleted successfully", None)

    except Exception as e:
        tracer.put_annotation("lambda_error", "true")
        tracer.put_annotation("lambda_name", context.function_name)
        tracer.put_metadata("event", event)
        tracer.put_metadata("message", str(e))
        logger.exception({"message": str(e)})
        return createResponse(500, "The server encountered an unexpected condition that prevented it from fulfilling your request.", None)

@tracer.capture_method
def findEntry(userId, entryId):
    response = dynamoRetry(
        SLEEP_TABLE.query,
        KeyConditionExpression=Key("userId").eq(userId),
        FilterExpression="entryId = :eid",
        ExpressionAttributeValues={":eid": entryId},
    )
    items = response.get("Items", [])
    return items[0] if items else None

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

@tracer.capture_method
def deleteSleepData(existing, userId):
    sortKey = existing["createdAt#entryId"]

    dynamoRetry(
        SLEEP_TABLE.delete_item,
        Key={
            "userId": userId,
            "createdAt#entryId": sortKey,
        },
    )