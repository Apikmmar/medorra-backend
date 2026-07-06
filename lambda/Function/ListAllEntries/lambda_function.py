import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

SYMPTOMS_TABLE_NAME = os.environ.get("SYMPTOMS_TABLE_NAME")
MEDICATIONS_TABLE_NAME = os.environ.get("MEDICATIONS_TABLE_NAME")
FOOD_TABLE_NAME = os.environ.get("FOOD_TABLE_NAME")
SLEEP_TABLE_NAME = os.environ.get("SLEEP_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

TABLE_NAMES = {
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

        startDate = params.get("startDate")
        endDate = params.get("endDate")
        pageSize = int(params.get("pageSize", "20"))
        page = int(params.get("page", "1"))

        if startDate and endDate and startDate > endDate:
            return createResponse(400, "Start date must not be after end date", {"field": "startDate"})

        allEntries = []
        totalCount = 0

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            for entryType, tableName in TABLE_NAMES.items():
                futures[entryType] = executor.submit(
                    queryTable, tableName, userId, startDate, endDate, entryType
                )

            for entryType, future in futures.items():
                result = future.result()
                allEntries.extend(result["items"])
                totalCount += result["count"]

        allEntries.sort(key=lambda x: x.get("createdAt", ""), reverse=True)

        startIdx = (page - 1) * pageSize
        endIdx = startIdx + pageSize
        paginatedEntries = allEntries[startIdx:endIdx]

        data = {
            "entries": paginatedEntries,
            "totalCount": totalCount,
            "hasMore": endIdx < len(allEntries),
            "page": page,
            "pageSize": pageSize,
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
def queryTable(tableName, userId, startDate, endDate, entryType):
    table = dynamodb.Table(tableName)

    keyCondition = Key("userId").eq(userId)

    if startDate and endDate:
        keyCondition = keyCondition & Key("createdAt#entryId").between(startDate, endDate + "~")
    elif startDate:
        keyCondition = keyCondition & Key("createdAt#entryId").gte(startDate)
    elif endDate:
        keyCondition = keyCondition & Key("createdAt#entryId").lte(endDate + "~")

    items = []
    lastKey = None

    while True:
        queryKwargs = {
            "KeyConditionExpression": keyCondition,
            "ScanIndexForward": False,
        }
        if lastKey:
            queryKwargs["ExclusiveStartKey"] = lastKey

        response = dynamoRetry(table.query, **queryKwargs)

        for item in response.get("Items", []):
            item["entryType"] = entryType
            items.append(item)

        lastKey = response.get("LastEvaluatedKey")
        if not lastKey:
            break

    return {"items": items, "count": len(items)}
