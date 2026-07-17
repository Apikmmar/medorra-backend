import os
import json
import boto3
from botocore.exceptions import ClientError
from feedback_entry import FeedbackEntry
from base_entry import ValidationError
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

FEEDBACK_TABLE_NAME = os.environ.get("FEEDBACK_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

FEEDBACK_TABLE = dynamodb.Table(FEEDBACK_TABLE_NAME)

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        body = json.loads(event.get("body", "{}"))

        userId = event["requestContext"]["authorizer"]["claims"]["sub"]

        body["userId"] = userId

        entry = FeedbackEntry.fromDict(body)
        entry.validate()

        item = storeFeedbackData(entry)

        return createResponse(200, "Feedback submitted successfully", item)

    except ValidationError as e:
        return createResponse(400, e.message, {"field": e.field_name})

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
def storeFeedbackData(entry):
    item = entry.toDict()

    dynamoRetry(FEEDBACK_TABLE.put_item, Item=item)

    return item
