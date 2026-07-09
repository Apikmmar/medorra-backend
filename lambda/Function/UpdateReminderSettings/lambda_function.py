import os
import json
import boto3
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from botocore.exceptions import ClientError
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

USERS_TABLE = dynamodb.Table(USERS_TABLE_NAME)

REMINDER_FLAG_VALUE = "ENABLED"

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]
        body = json.loads(event.get("body") or "{}")

        enabled = body.get("remindersEnabled")
        reminderHour = body.get("reminderHour")
        timezone = body.get("timezone")

        if not isinstance(enabled, bool):
            return createResponse(400, "remindersEnabled must be a boolean", {"field": "remindersEnabled"})

        respUser = getUser(userId)

        if respUser is None:
            return createResponse(400, "User Not Exist", None)

        if enabled:
            if not isinstance(reminderHour, int) or reminderHour < 0 or reminderHour > 23:
                return createResponse(400, "reminderHour must be an integer between 0 and 23", {"field": "reminderHour"})

            if not isValidTimezone(timezone):
                return createResponse(400, "timezone must be a valid IANA timezone", {"field": "timezone"})

            data = enableReminders(userId, reminderHour, timezone)
        else:
            data = disableReminders(userId)

        return createResponse(200, "Reminder settings updated successfully", data)

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
def isValidTimezone(timezone):
    if not isinstance(timezone, str) or not timezone:
        return False

    try:
        ZoneInfo(timezone)
        return True
    except(ZoneInfoNotFoundError, ValueError):
        return False

@tracer.capture_method
def getUser(userId):
    respUser = dynamoRetry(
                USERS_TABLE.get_item,
                Key={"userId": userId}
            ).get("Item")

    return respUser

@tracer.capture_method
def enableReminders(userId, reminderHour, timezone):
    dynamoRetry(
        USERS_TABLE.update_item,
        Key={"userId": userId},
        UpdateExpression="SET remindersEnabled = :on, reminderHour = :h, #tz = :tz, reminderEnabledFlag = :flag",
        ExpressionAttributeNames={"#tz": "timezone"},
        ExpressionAttributeValues={
            ":on": True,
            ":h": reminderHour,
            ":tz": timezone,
            ":flag": REMINDER_FLAG_VALUE,
        },
    )

    data = {
        "remindersEnabled": True,
        "reminderHour": reminderHour,
        "timezone": timezone
    }

    return data
    
@tracer.capture_method
def disableReminders(userId):
    # Removing reminderEnabledFlag drops the user out of the sparse gsi-reminders index.
    dynamoRetry(
        USERS_TABLE.update_item,
        Key={"userId": userId},
        UpdateExpression="SET remindersEnabled = :off REMOVE reminderEnabledFlag",
        ExpressionAttributeValues={":off": False},
    )

    data = {
        "remindersEnabled": False
    }

    return data
