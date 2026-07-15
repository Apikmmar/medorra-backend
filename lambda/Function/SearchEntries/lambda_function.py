import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from concurrent.futures import ThreadPoolExecutor
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from user_isolation import enforceUserIsolation
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

VALID_TYPES = set(TABLE_NAMES.keys())

NAME_FIELDS = ("symptomName", "medicationName", "mealType")

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]
        params = event.get("queryStringParameters") or {}

        query = (params.get("q") or "").strip()
        entryType = params.get("type")
        startDate = params.get("startDate")
        endDate = params.get("endDate")
        pageSize = int(params.get("pageSize", "15"))
        page = int(params.get("page", "1"))

        if not query:
            return createResponse(400, "Search query 'q' is required.", {"field": "q"})

        if entryType and entryType not in VALID_TYPES:
            return createResponse(400, f"Invalid type. Must be one of: {', '.join(sorted(VALID_TYPES))}", {"field": "type"})

        if startDate and endDate and startDate > endDate:
            return createResponse(400, "Start date must not be after end date", {"field": "startDate"})

        targets = {entryType: TABLE_NAMES[entryType]} if entryType else TABLE_NAMES

        queryLower = query.lower()
        allEntries = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                et: executor.submit(queryTable, tableName, userId, startDate, endDate, et)
                for et, tableName in targets.items()
            }
            for et, future in futures.items():
                allEntries.extend(future.result())

        allEntries = enforceUserIsolation(userId, allEntries)

        matches = [e for e in allEntries if matchesQuery(e, queryLower)]
        matches.sort(key=lambda x: x.get("createdAt", ""), reverse=True)

        totalCount = len(matches)
        startIdx = (page - 1) * pageSize
        endIdx = startIdx + pageSize
        paginated = matches[startIdx:endIdx]

        data = {
            "entries": paginated,
            "totalCount": totalCount,
            "hasMore": endIdx < totalCount,
            "page": page,
            "pageSize": pageSize,
        }

        return createResponse(200, "Search results retrieved successfully", data)

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
def matchesQuery(entry, queryLower):
    haystack = []

    for field in NAME_FIELDS:
        value = entry.get(field)
        if isinstance(value, str):
            haystack.append(value)

    notes = entry.get("notes")
    if isinstance(notes, str):
        haystack.append(notes)

    for item in entry.get("items", []) or []:
        if isinstance(item, dict):
            desc = item.get("description")
            if isinstance(desc, str):
                haystack.append(desc)

    return queryLower in " ".join(haystack).lower()

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
        queryKwargs = {"KeyConditionExpression": keyCondition, "ScanIndexForward": False}
        if lastKey:
            queryKwargs["ExclusiveStartKey"] = lastKey

        response = dynamoRetry(table.query, **queryKwargs)

        for item in response.get("Items", []):
            item["entryType"] = entryType
            items.append(item)

        lastKey = response.get("LastEvaluatedKey")
        if not lastKey:
            break

    return items