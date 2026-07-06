import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

SYMPTOMS_TABLE_NAME = os.environ.get("SYMPTOMS_TABLE_NAME")
MEDICATIONS_TABLE_NAME = os.environ.get("MEDICATIONS_TABLE_NAME")
FOOD_TABLE_NAME = os.environ.get("FOOD_TABLE_NAME")
SLEEP_TABLE_NAME = os.environ.get("SLEEP_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

TABLE_MAP = {
    "symptom": SYMPTOMS_TABLE_NAME,
    "medication": MEDICATIONS_TABLE_NAME,
    "food": FOOD_TABLE_NAME,
    "sleep": SLEEP_TABLE_NAME,
}

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]
        params = event.get("queryStringParameters") or {}

        entryType = params.get("type")
        startDate = params.get("startDate")
        endDate = params.get("endDate")
        pageSize = int(params.get("pageSize", "20"))
        lastKey = params.get("lastKey")

        if not entryType:
            return createResponse(400, "Missing required parameter: type", None)

        if entryType not in TABLE_MAP:
            return createResponse(400, f"Invalid type. Must be one of: {', '.join(sorted(TABLE_MAP.keys()))}", {"field": "type"})

        if startDate and endDate and startDate > endDate:
            return createResponse(400, "Start date must not be after end date", {"field": "startDate"})

        table = dynamodb.Table(TABLE_MAP[entryType])

        items, lastEvaluatedKey = queryEntries(table, userId, startDate, endDate, pageSize, lastKey)
        totalCount = countEntries(table, userId)

        data = {
            "entries": items,
            "totalCount": totalCount,
            "hasMore": lastEvaluatedKey is not None,
            "lastKey": json.dumps(lastEvaluatedKey) if lastEvaluatedKey else None,
        }

        return createResponse(200, "Entries retrieved successfully", data)

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
def buildKeyCondition(userId, startDate, endDate):
    keyCondition = Key("userId").eq(userId)

    if startDate and endDate:
        keyCondition = keyCondition & Key("createdAt#entryId").between(startDate, endDate + "~")
    elif startDate:
        keyCondition = keyCondition & Key("createdAt#entryId").gte(startDate)
    elif endDate:
        keyCondition = keyCondition & Key("createdAt#entryId").lte(endDate + "~")

    return keyCondition

@tracer.capture_method
def queryEntries(table, userId, startDate, endDate, pageSize, lastKey):
    keyCondition = buildKeyCondition(userId, startDate, endDate)

    queryKwargs = {
        "KeyConditionExpression": keyCondition,
        "ScanIndexForward": False,
        "Limit": pageSize,
    }

    if lastKey:
        queryKwargs["ExclusiveStartKey"] = json.loads(lastKey)

    response = dynamoRetry(table.query, **queryKwargs)

    items = response.get("Items", [])
    lastEvaluatedKey = response.get("LastEvaluatedKey")

    return items, lastEvaluatedKey

@tracer.capture_method
def countEntries(table, userId):
    countResponse = dynamoRetry(
        table.query,
        KeyConditionExpression=Key("userId").eq(userId),
        Select="COUNT",
    )
    return countResponse.get("Count", 0)
