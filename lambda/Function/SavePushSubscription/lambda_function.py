import os
import json
import boto3
from botocore.exceptions import ClientError
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

USERS_TABLE = dynamodb.Table(USERS_TABLE_NAME)

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]
        method = event.get("httpMethod", "POST")
        body = json.loads(event.get("body", "{}"))
        subscription = body.get("subscription")

        if not isValidSubscription(subscription):
            return createResponse(400, "Invalid push subscription", {"field": "subscription"})
        
        if method =="DELETE":
            data = removeSubscription(userId, subscription["endpoint"])

            return createResponse(200, "Push subscription removed", data)

        data = saveSubscription(userId, subscription)

        return createResponse(200, "Push subscription saved", data)

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
def isValidSubscription(sub):
    if not isinstance(sub, dict):
        return False

    keys = sub.get("keys", {})

    return bool(sub.get("endpoint")) and bool(keys.get("p256dh")) and bool(keys.get("auth"))

@tracer.capture_method
def removeSubscription(userId, subsEndpoint):
    subs = [s for s in getSubscriptions(userId) if s.get("endpoint") != subsEndpoint]

    dynamoRetry(
        USERS_TABLE.update_item,
        Key={"userId": userId},
        UpdateExpression="SET pushSubscriptions = :subs",
        ExpressionAttributeValues={":subs": subs},
    )

    data = {"subscriptionCount": len(subs)}

    return data

@tracer.capture_method
def saveSubscription(userId, subscription):
    subs = getSubscriptions(userId)

    subs = [s for s in subs if s.get("endpoint") != subscription["endpoint"]]
    subs.append(subscription)

    dynamoRetry(
        USERS_TABLE.update_item,
        Key={"userId": userId},
        UpdateExpression="SET pushSubscriptions = :subs",
        ExpressionAttributeValues={":subs": subs},
    )
    data = {"subscriptionCount": len(subs)}
    
    return data

@tracer.capture_method
def getSubscriptions(userId):
    user = dynamoRetry(
        USERS_TABLE.get_item,
        Key={"userId": userId}
    ).get("Item") or {}

    userPushSubs = user.get("pushSubscriptions", [])

    return userPushSubs