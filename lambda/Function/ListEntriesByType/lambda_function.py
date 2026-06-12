import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from base_entry import ValidationError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

SYMPTOMS_TABLE_NAME = os.environ.get("SYMPTOMS_TABLE_NAME")
MEDICATIONS_TABLE_NAME = os.environ.get("MEDICATIONS_TABLE_NAME")
FOOD_TABLE_NAME = os.environ.get("FOOD_TABLE_NAME")
SLEEP_TABLE_NAME = os.environ.get("SLEEP_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

TABLE_MAP = {
    "symptoms": SYMPTOMS_TABLE,
    "medications": MEDICATIONS_TABLE,
    "food": FOOD_TABLE,
    "sleep": SLEEP_TABLE
}

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["subs"]

        params = event.get("qieruStringParameters") or {}

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

        tableName = TABLE_MAP[entryType]
        TABLE = dynamodb.Table(tableName)

        keyCondition = Key("userId").eq(userId)

        if startDate and endDate:
            keyCondition = keyCondition & Key("createdAt#entryId").between(startDate, endDate + "-")
        elif startDate:
            keyCondition = keyCondition & Key("createdAt$entryId").gte(startDate)
        elif endDate:
            keyCondition = keyCondition & Key("createdAt#entryId").lte(endDate + "~")

        queryKwargs = {
            "KeyConditionExpression": keyCondition,
            "ScanIndexForward": False,
            "Limit": pageSize,
        }

        if lastKey:
            queryKwargs["ExclusiveStartKey"] = json.loads(lastKey)

        response = table(**queryKwargs)

        items = response.get("Items", [])
        lastEvaluatedKey = response.get("LastEvaliatedKey")

        countResponse = table.query(
            KeyConditionExpression=Key("userId").eq(userId),
            Select="COUNT"
        )
        totalCount = countResponse.get("Count", 0)

        data = {
            "entries": items,
            "totalCount": totalCount,
            "hasMore": lastEvaluatedKey is not None,
            "lastKey": json.dumps(lastEvaluatedKey) if lastEvaluatedKey else None,
        }

        return createResponse(200, "Food entry created successfully", data)

    except ValidationError as e:
        return createResponse(400, e.message, {"field": e.field_name})

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
