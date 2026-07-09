import os
import json
import boto3
from datetime import datetime
from zoneinfo import ZoneInfo
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from pywebpush import webpush, WebPushException
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT")
REMINDER_FLAG_VALUE = "ENABLED"

dynamodb = boto3.resource("dynamodb")
USERS_TABLE = dynamodb.Table(USERS_TABLE_NAME)

logger = Logger()
tracer = Tracer()

GSI_REMINDERS = "gsi-reminders"

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        users = getEnabledUsers()
        sent = 0

        for user in users:
            if shouldRemind(user):
                remindUser(user)
                sent += 1

        data = {"candidates": len(users), "sent": sent}

        return createResponse(200, "Reminder run complete", data)

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
def getEnabledUsers():
    users = []
    lastKey = None
    
    while True:
        queryKwargs = {
            "IndexName": GSI_REMINDERS,
            "KeyConditionExpression": Key("reminderEnabledFlag").eq(REMINDER_FLAG_VALUE),
        }

        if lastKey:
            queryKwargs["ExclusiveStartKey"] = lastKey

        response = dynamoRetry(USERS_TABLE.query, **queryKwargs)
        users.extend(response.get("Items", []))

        lastKey = response.get("LastEvaluatedKey")
        if not lastKey:
            break

    return users

@tracer.capture_method
def shouldRemind(user):
    timezone = user.get("timezone")
    reminderHour = user.get("reminderHour")

    if timezone is None or reminderHour is None:
        return False

    nowLocal = datetime.now(ZoneInfo(timezone))
    todayLocal = nowLocal.strftime("%Y-%m-%d")

    if nowLocal.hour != int(reminderHour):
        return False

    if user.get("lastLoggedDate") == todayLocal:
        return False

    if user.get("lastReminderSentDate") == todayLocal:
        return False

    return bool(user.get("pushSubscriptions"))

@tracer.capture_method
def remindUser(user):
    userId = user["userId"]
    timezone = user["timezone"]
    todayLocal = datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d")

    payload = {
        "title": "Medorra",
        "body": "Don't forget to log your health entries today.",
        "url": "/entries/new",
    }

    subs = user.get("pushSubscriptions", [])
    liveSubs = []

    for sub in subs:
        if sendPush(sub, payload):
            liveSubs.append(sub)

    dynamoRetry(
        USERS_TABLE.update_item,
        Key={"userId": userId},
        UpdateExpression="SET pushSubscriptions = :subs, lastReminderSentDate = :d",
        ExpressionAttributeValues={":subs": liveSubs, ":d": todayLocal},
    )

@tracer.capture_method
def sendPush(subscription, payload):
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_SUBJECT},
        )
        return True
    except WebPushException as e:
        status = getattr(e.response, "status_code", None)
        if status in (404, 410):
            logger.info({"message": "Pruning expired push subscription", "status": status})
            return False
        logger.warning({"message": "Push send failed", "error": str(e)})
        return True