import os
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from user_isolation import enforceUserIsolation
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

SYMPTOMS_TABLE_NAME = os.environ.get("SYMPTOMS_TABLE_NAME")
MEDICATIONS_TABLE_NAME = os.environ.get("MEDICATIONS_TABLE_NAME")
FOOD_TABLE_NAME = os.environ.get("FOOD_TABLE_NAME")
SLEEP_TABLE_NAME = os.environ.get("SLEEP_TABLE_NAME")

MAX_ENTRY_IDS = 50

dynamodb = boto3.resource("dynamodb")

TABLE_MAP = {
    "symptom": dynamodb.Table(SYMPTOMS_TABLE_NAME),
    "medication": dynamodb.Table(MEDICATIONS_TABLE_NAME),
    "food": dynamodb.Table(FOOD_TABLE_NAME),
    "sleep": dynamodb.Table(SLEEP_TABLE_NAME),
}

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]
        body = json.loads(event.get("body") or "{}")
        entryIds = body.get("entryIds")

        if not isinstance(entryIds, list) or not entryIds:
            return createResponse(400, "Missing or invalid entryIds", {"field": "entryIds"})

        entryIds = list(dict.fromkeys(str(e) for e in entryIds if e))

        if not entryIds:
            return createResponse(400, "Missing or invalid entryIds", {"field": "entryIds"})

        if len(entryIds) > MAX_ENTRY_IDS:
            return createResponse(400, f"Too many entryIds (max {MAX_ENTRY_IDS})", {"field": "entryIds"})

        entries = fetchEntriesByIds(userId, set(entryIds))

        orderIndex = {eid: i for i, eid in enumerate(entryIds)}
        entries.sort(key=lambda e: orderIndex.get(e.get("entryId"), len(entryIds)))

        foundIds = {e.get("entryId") for e in entries}
        missingIds = [eid for eid in entryIds if eid not in foundIds]

        data = {
            "entries": entries,
            "totalCount": len(entries),
            "missingIds": missingIds
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
def fetchEntriesByIds(userId, wantedIds):
    remaining = set(wantedIds)
    found = []

    for entryType, table in TABLE_MAP.items():
        if not remaining:
            break
        matches = queryTableForIds(table, userId, remaining, entryType)
        for item in matches:
            item["entryType"] = entryType
            found.append(item)
            remaining.discard(item.get("entryId"))

    return enforceUserIsolation(userId, found)

@tracer.capture_method
def queryTableForIds(table, userId, wantedIds, entryType):
    matches = []
    remaining = set(wantedIds)
    lastKey = None

    while remaining:
        queryKwargs = {
            "KeyConditionExpression": Key("userId").eq(userId),
            "FilterExpression": Attr("entryId").is_in(list(wantedIds)),
            "ScanIndexForward": False,
        }
        if lastKey:
            queryKwargs["ExclusiveStartKey"] = lastKey

        response = dynamoRetry(table.query, **queryKwargs)

        for item in response.get("Items", []):
            matches.append(item)
            remaining.discard(item.get("entryId"))

        lastKey = response.get("LastEvaluatedKey")
        if not lastKey:
            break

    return matches