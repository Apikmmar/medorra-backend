import os
import json
import uuid
import hashlib
import boto3
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError
from base_entry import BaseEntry, ValidationError
from symptom_entry import SymptomEntry
from medication_entry import MedicationEntry
from food_entry import FoodEntry
from sleep_entry import SleepEntry
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

VOICE_DRAFTS_TABLE_NAME = os.environ.get("VOICE_DRAFTS_TABLE_NAME")
SYMPTOMS_TABLE_NAME = os.environ.get("SYMPTOMS_TABLE_NAME")
MEDICATIONS_TABLE_NAME = os.environ.get("MEDICATIONS_TABLE_NAME")
FOOD_TABLE_NAME = os.environ.get("FOOD_TABLE_NAME")
SLEEP_TABLE_NAME = os.environ.get("SLEEP_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

VOICE_DRAFTS_TABLE = dynamodb.Table(VOICE_DRAFTS_TABLE_NAME)
FUTURE_TOLERANCE_MINUTES = 5

logger = Logger()
tracer = Tracer()

TABLE_MAP = {
    "symptom": dynamodb.Table(SYMPTOMS_TABLE_NAME),
    "medication": dynamodb.Table(MEDICATIONS_TABLE_NAME),
    "food": dynamodb.Table(FOOD_TABLE_NAME),
    "sleep": dynamodb.Table(SLEEP_TABLE_NAME),
}

MODEL_MAP = {
    "symptom": SymptomEntry,
    "medication": MedicationEntry,
    "food": FoodEntry,
    "sleep": SleepEntry,
}

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]
        draftId = event.get("pathParameters", {}).get("draftId")

        if not draftId:
            return createResponse(400, "draftId is required", {"field": "draftId"})

        draft = getDraft(userId, draftId)

        if not draft:
            return createResponse(404, "Draft not found", None)

        if draft.get("status") == "CONFIRMED":
            return createResponse(200, "Already confirmed", {"created": draft.get("createdEntryIds", [])})

        body = json.loads(event.get("body", "{}") or "{}")
        entries = body.get("entries", [])

        if not isinstance(entries, list) or len(entries) == 0:
            return createResponse(400, "At least one entry is required", {"field": "entries"})

        if len(entries) > 20:
            return createResponse(400, "Too many entries in one confirmation", {"field": "entries"})

        prepared = []
        for idx, e in enumerate(entries):
            entryType = e.get("entryType")
            model = MODEL_MAP.get(entryType)
            if model is None:
                return createResponse(400, f"Invalid entryType at index {idx}", {"field": "entryType"})

            clientEntryId = e.get("clientEntryId") or str(uuid.uuid4())

            data = dict(e.get("data", {}))
            data["userId"] = userId
            data["entryType"] = entryType
            data["entryId"] = deterministicUuidV4(f"{draftId}:{clientEntryId}")

            entry = model.fromDict(data)
            entry.validate()
            alignEventTime(entry)

            if isFutureTime(entry.timestamp):
                return createResponse(400, "Entries cannot have a future date/time", {"field": "timestamp"})

            prepared.append(entry)

        createdIds = []

        for entry in prepared:
            sortKey = BaseEntry.generateSortKey(entry.createdAt, entry.entryId)
            item = entry.toDict()
            item["createdAt#entryId"] = sortKey
            writeEntry(entry.entryType, item)
            createdIds.append(entry.entryId)

        markConfirmed(userId, draftId, createdIds)

        return createResponse(200, "Entries created from voice", {"created": createdIds})

    except ValidationError as e:
        return createResponse(400, e.message, {"field": e.field_name})

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

def isFutureTime(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return False

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    return dt > now + timedelta(minutes=FUTURE_TOLERANCE_MINUTES)

@tracer.capture_method
def alignEventTime(entry):
    eventTime = None

    if entry.entryType == "sleep":
        endTimes = [seg.endTime for seg in getattr(entry, "segments", []) if getattr(seg, "endTime", None)]
        if endTimes:
            eventTime = max(endTimes)
    else:
        eventTime = getattr(entry, "timestamp", None)

    if eventTime:
        entry.createdAt = eventTime
        entry.timestamp = eventTime

@tracer.capture_method
def deterministicUuidV4(seed):
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    b = bytearray(digest[:16])
    b[6] = (b[6] & 0x0F) | 0x40
    b[8] = (b[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(b)))

@tracer.capture_method
def getDraft(userId, draftId):
    respDraft = dynamoRetry(
        VOICE_DRAFTS_TABLE.get_item, 
        Key={"userId": userId, 
        "draftId": draftId}).get("Item")

    return respDraft
    
@tracer.capture_method
def writeEntry(entryType, item):
    table = TABLE_MAP[entryType]

    try:
        dynamoRetry(
            table.put_item,
            Item=item,
            ConditionExpression="attribute_not_exists(userId) AND attribute_not_exists(#sk)",
            ExpressionAttributeNames={"#sk": "createdAt#entryId"},
        )
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return
        raise

@tracer.capture_method
def markConfirmed(userId, draftId, createdIds):
    dynamoRetry(
        VOICE_DRAFTS_TABLE.update_item,
        Key={"userId": userId, "draftId": draftId},
        UpdateExpression="SET #s = :s, createdEntryIds = :ids",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "CONFIRMED", ":ids": createdIds},
    )