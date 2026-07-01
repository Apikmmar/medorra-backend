import os
import json
import boto3
from botocore.exceptions import ClientError
from food_entry import FoodEntry
from base_entry import BaseEntry, ValidationError
from dynamo_retry import dynamoRetry
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

FOOD_TABLE_NAME = os.environ.get("FOOD_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

FOOD_TABLE = dynamodb.Table(FOOD_TABLE_NAME)

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        body = json.loads(event.get("body", "{}"))

        userId = event["requestContext"]["authorizer"]["claims"]["sub"]

        body["userId"] = userId

        entry = FoodEntry.fromDict(body)
        entry.validate()

        sortKey = BaseEntry.generateSortKey(entry.createdAt, entry.entryId)

        item = storeFoodData(sortKey, entry)

        return createResponse(200, "Food entry created successfully", item)

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
        }),
        'headers': {"Access-Control-Allow-Origin": "*"}
    }

@tracer.capture_method
def storeFoodData(sortKey, entry):
    item = entry.toDict()
    item["createdAt#entryId"] = sortKey

    dynamoRetry(FOOD_TABLE.put_item, Item=item)

    return item