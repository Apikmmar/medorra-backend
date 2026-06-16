import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from medication_entry import MedicationEntry
from base_entry import BaseEntry, ValidationError
from dynamo_retry import dynamoRetry
from datetime import datetime
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

dynamodb = boto3.resource("dynamodb")

MEDICATIONS_TABLE_NAME = os.environ.get("MEDICATIONS_TABLE_NAME")
MEDICATIONS_TABLE = dynamodb.Table(MEDICATIONS_TABLE_NAME)

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

        body = json.loads(event.get("body", "{}"))

        existing = findEntry(userId, entryId)

        if not existing:
            return createResponse(404, "Entry not found", None)

        body["userId"] = userId
        body["entryId"] = existing["entryId"]
        body["createdAt"] = existing["createdAt"]
        body["timestamp"] = body.get("timestamp", existing.get("timestamp"))

        entry = MedicationEntry.fromDict(body)
        entry.validate()

        currentVersion = existing.get("version", 1)
        now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        sortKey = existing["createdAt#entryId"]

        item = entry.toDict()
        item["createdAt#entryId"] = sortKey
        item["updatedAt"] = now
        item["version"] = currentVersion + 1

        dynamoRetry(
            MEDICATIONS_TABLE.put_item,
            Item=item,
            ConditionExpression="attribute_exists(userId) AND version = :expectedVersion",
            ExpressionAttributeValues={
                ":expectedVersion": currentVersion,
            },
        )

        return createResponse(200, "Medication entry updated successfully", item)

    except ValidationError as e:
        return createResponse(400, e.message, {"field": e.field_name})

    except ClientError as e:
        errorCode = e.response.get("Error", {}).get("Code", "")
        if errorCode == "ConditionalCheckFailedException":
            return createResponse(409, "Entry was modified by another request. Please refresh and retry", None)
        
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
def findEntry(userId, entryId):
    response = dynamoRetry(
        MEDICATIONS_TABLE.query,
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
