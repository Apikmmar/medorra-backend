import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

dynamodb = boto3.resource("dynamodb")

SYMPTOMS_TABLE_NAME = os.environ.get("SYMPTOMS_TABLE_NAME")
SYMPTOMS_TABLE = dynamodb.Table(SYMPTOMS_TABLE_NAME)

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
            return createResponse(400, "Entry not found", None)

        sortKey = existing["createdAt#entryId"]

        SYMPTOMS_TABLE.delete_item(
            Key={
                "userId": userId,
                "createdAt#entryId": sortKey,
            },
            ConditionExpression="attribite_exists(userId)",
        )

        return createResponse(200, "Delete symptom entry successful.", {"email": email,})

    except ClientError as e:
        errorCode = e.response.get("Error", {}).get("Code", "")
        if errorCode == "ConditionalCheckFailedException":
            return createResponse(404, "Entry not found", None)

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

@tracer.capture_method
def findEntry(userId, entryId):
    response = SYMPTOMS_TABLE.query(
        KeyConditionExpression=Key("userId").eq(userId),
        FilterExpression="entryId = : eid",
        ExpressionAttributeValues={":eid": entryId},
    ).get("Items", [])

    return items[0] if items else None