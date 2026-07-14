import os
import json
import boto3
from json_encoder import DecimalEncoder
from dynamo_retry import dynamoRetry
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

VOICE_DRAFTS_TABLE_NAME = os.environ.get("VOICE_DRAFTS_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

VOICE_DRAFTS_TABLE = dynamodb.Table(VOICE_DRAFTS_TABLE_NAME)

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]
        draftId = event.get("pathParameters", {}).get("draftId")

        if not draftId:
            return createResponse(400, "draftId is required", {"field": "draftId"})

        item = dynamoRetry(VOICE_DRAFTS_TABLE.get_item, Key={"userId": userId, "draftId": draftId}).get("Item")

        if not item:
            return createResponse(404, "Draft not found", None)

        data = {
            "draftId": item["draftId"],
            "status": item.get("status"),
            "transcript": item.get("transcript"),
            "proposedEntries": item.get("proposedEntries", []),
            "failureReason": item.get("failureReason"),
        }

        return createResponse(200, "Draft retrieved", data)

    except Exception as e:
        tracer.put_annotation("lambda_error", "true")
        tracer.put_annotation("lambda_name", context.function_name)
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
