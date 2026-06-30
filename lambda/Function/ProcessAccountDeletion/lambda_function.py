import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from dynamo_retry import dynamoRetry
from datetime import datetime
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")
SYMPTOMS_TABLE_NAME = os.environ.get("SYMPTOMS_TABLE_NAME")
MEDICATIONS_TABLE_NAME = os.environ.get("MEDICATIONS_TABLE_NAME")
FOOD_TABLE_NAME = os.environ.get("FOOD_TABLE_NAME")
SLEEP_TABLE_NAME = os.environ.get("SLEEP_TABLE_NAME")
INSIGHTS_TABLE_NAME = os.environ.get("INSIGHTS_TABLE_NAME")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")

dynamodb = boto3.resource("dynamodb")
ses = boto3.client("ses")

USERS_TABLE = dynamodb.Table(USERS_TABLE_NAME)
SYMPTOMS_TABLE = dynamodb.Table(SYMPTOMS_TABLE_NAME)
MEDICATIONS_TABLE = dynamodb.Table(MEDICATIONS_TABLE_NAME)
FOOD_TABLE = dynamodb.Table(FOOD_TABLE_NAME)
SLEEP_TABLE = dynamodb.Table(SLEEP_TABLE_NAME)
INSIGHTS_TABLE = dynamodb.Table(INSIGHTS_TABLE_NAME)

ENTRY_TABLES = {
    "Symptoms": {"table": SYMPTOMS_TABLE, "sk": "createdAt#entryId"},
    "Medications": {"table": MEDICATIONS_TABLE, "sk": "createdAt#entryId"},
    "Food": {"table": FOOD_TABLE, "sk": "createdAt#entryId"},
    "Sleep": {"table": SLEEP_TABLE, "sk": "createdAt#entryId"},
    "Insights": {"table": INSIGHTS_TABLE, "sk": "confidence#insightId"},
}

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        detail = event.get("detail")
        userId = detail.get("userId")
        userEmail = detail.get("email")

        if not userId:
            return createResponse(400, "Missing userId", None)

        failedTables = []

        for tableName, config in ENTRY_TABLES.items():
            success = deleteAllUserEntries(userId, config["table"], config["sk"])

            if not success:
                failedTables.append(tableName)

        if failedTables:
            updateDeletionStatusFailed(userId, failedTables)

            if userEmail:
                notifyUser(userEmail)
        else:
            deleteUser(userId)

        return createResponse(200, "Account deleted successfully", None)

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
def deleteAllUserEntries(userId, table, skName):
    try:
        lastKey = None

        while True:
            queryKwargs = {
                "KeyConditionExpression": Key("userId").eq(userId),
                "ProjectionExpression": f"userId, #sk",
                "ExpressionAttributeNames": {"#sk": skName},
            }

            if lastKey:
                queryKwargs["ExclusiveStartKey"] = lastKey

            response = dynamoRetry(table.query, **queryKwargs)
            items = response.get("Items", [])

            for item in items:
                dynamoRetry(
                    table.delete_item,
                    Key={
                        "userId": userId,
                        skName: item[skName],
                    }
                )

            lastKey = response.get("LastEvaluatedKey")

            if not lastKey:
                break

        return True
    except Exception as e:
        return False

@tracer.capture_method
def notifyUser(email):
    try:
        ses.send_email(
            Source=SENDER_EMAIL,
            Destination={
                "ToAddresses": [email],
            },
            Message={
                "Subject": {"Data": "Medorra - Account Deletion In Progress"},
                "Body": {
                    "Text": {
                        "Data": "Your account deletion request is still being processed. We will complete it within 30 days of your original request. No action is needed from you."
                    }
                },
            },
        )
    except Exception as e:
        logger.warning({"message": "Failed to send notification email", "error": str(e)})

@tracer.capture_method
def deleteUser(userId):
    dynamoRetry(
        USERS_TABLE.delete_item
        , Key={"userId": userId}
    )

@tracer.capture_method
def updateDeletionStatusFailed(userId, failedTables):
    dynamoRetry(
        USERS_TABLE.update_item,
        Key={"userId": userId},
        UpdateExpression="SET deletionStatus = :status, failedTables = :failed, lastRetryAt = :now",
        ExpressionAttributeValues={
            ":status": "failed",
            ":failed": failedTables,
            ":now": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        },
    )