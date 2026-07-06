import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from datetime import datetime
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

INSIGHTS_TABLE_NAME = os.environ.get("INSIGHTS_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

INSIGHTS_TABLE = dynamodb.Table(INSIGHTS_TABLE_NAME)

VALID_RESPONSES = {"dismiss", "confirm"}

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]

        pathParams = event.get("pathParameters") or {}
        insightId = pathParams.get("insightId")

        if not insightId:
            return createResponse(400, "insightId is required", {"field": "insightId"})

        body = json.loads(event.get("body", "{}"))
        userResponse = body.get("response")

        if not userResponse or userResponse not in VALID_RESPONSES:
            return createResponse(400, f"Response must be one of: {', '.join(sorted(VALID_RESPONSES))}", {"field": "response"})

        existing = findInsight(userId, insightId)

        if not existing:
            return createResponse(404, "Insight not found", None)

        newStatus = "dismissed" if userResponse == "dismiss" else "confirmed"
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        sortKey = existing["confidence#insightId"]
        confidenceStr = sortKey.split("#")[0]

        updatedItem = dict(existing)
        updatedItem["status"] = newStatus
        updatedItem["status#confidence#insightId"] = f"{newStatus}#{confidenceStr}#{insightId}"
        updatedItem["updatedAt"] = now
        updatedItem["userResponse"] = userResponse

        storeInsights(updatedItem)

        data = {
            "insightId": insightId, 
            "status": newStatus
        }

        return createResponse(200, f"Insight {newStatus} successfully", data)

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
def findInsight(userId, insightId):
    response = dynamoRetry(
        INSIGHTS_TABLE.query,
        KeyConditionExpression=Key("userId").eq(userId),
        FilterExpression="insightId = :iid",
        ExpressionAttributeValues={":iid": insightId},
    )
    items = response.get("Items", [])
    return items[0] if items else None

@tracer.capture_method
def storeInsights(updatedItem):
    dynamoRetry(
        INSIGHTS_TABLE.put_item, 
        Item=updatedItem
    )