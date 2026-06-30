import os
import json
import boto3
from dynamo_retry import dynamoRetry
from datetime import datetime, timedelta
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME")

dynamodb = boto3.resource("dynamodb")
eventbridge = boto3.client("events")

USERS_TABLE = dynamodb.Table(USERS_TABLE_NAME)

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]
        userEmail = event["requestContext"]["authorizer"]["claims"]["email"]

        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        deleteBy = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        markDeleteUser(userId, now, deleteBy, userEmail)

        eventbridge.put_events(
            Entries=[
                {
                    "Source": "medorra.account",
                    "DetailType": "AccountDeletionRequested",
                    "Detail": json.dumps({
                        "userId": userId,
                        "email": userEmail,
                        "requestedAt": now,
                        "deadline": deleteBy,
                    }),
                    "EventBusName": EVENT_BUS_NAME,
                }
            ]
        )

        return createResponse(200, "Account deletion scheduled. All data will be removed within 30 days.", {"deletionDeadline": deleteBy})

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
def markDeleteUser(userId, now, deleteBy, userEmail):
    dynamoRetry(
        USERS_TABLE.update_item,
        Key={"userId": userId},
        UpdateExpression="SET deletionRequestedAt = :now, deletionDeadline = :deadline, deletionStatus = :status, email = :email",
        ExpressionAttributeValues={
            ":now": now,
            ":deadline": deleteBy,
            ":status": "scheduled",
            ":email": userEmail,
        },
    )
