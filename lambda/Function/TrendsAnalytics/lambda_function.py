import os
import json
import boto3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")
SYMPTOMS_TABLE_NAME = os.environ.get("SYMPTOMS_TABLE_NAME")
MEDICATIONS_TABLE_NAME = os.environ.get("MEDICATIONS_TABLE_NAME")
FOOD_TABLE_NAME = os.environ.get("FOOD_TABLE_NAME")
SLEEP_TABLE_NAME = os.environ.get("SLEEP_TABLE_NAME")

dynamodb = boto3.resource("dynamodb")

USERS_TABLE = dynamodb.Table(USERS_TABLE_NAME)
SYMPTOMS_TABLE = dynamodb.Table(SYMPTOMS_TABLE_NAME)
MEDICATIONS_TABLE = dynamodb.Table(MEDICATIONS_TABLE_NAME)
FOOD_TABLE = dynamodb.Table(FOOD_TABLE_NAME)
SLEEP_TABLE = dynamodb.Table(SLEEP_TABLE_NAME)

VALID_RANGES = {7, 30, 90}
DEFAULT_RANGE = 30

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]
        params = event.get("queryStringParameters") or {}

        rangeDays, error = parseRange(params.get("range"))

        if error:
            return createResponse(400, error, {"field": "range"})

        userTimezone = getUserTimezone(userId)
        tz = ZoneInfo(userTimezone)

        dateLabels, cutoffUtc = buildDateWindow(rangeDays, tz)

        symptomEntries = fetchEntriesSince(SYMPTOMS_TABLE, userId, cutoffUtc)
        medicationEntries = fetchEntriesSince(MEDICATIONS_TABLE, userId, cutoffUtc)
        foodEntries = fetchEntriesSince(FOOD_TABLE, userId, cutoffUtc)
        sleepEntries = fetchEntriesSince(SLEEP_TABLE, userId, cutoffUtc)

        data = {
            "range": rangeDays,
            "timezone": userTimezone,
            "dates": dateLabels,
            "symptom": aggregateSymptoms(symptomEntries, dateLabels, tz),
            "sleep": aggregateSleep(sleepEntries, dateLabels, tz),
            "medication": aggregateCounts(medicationEntries, dateLabels, tz),
            "food": aggregateCounts(foodEntries, dateLabels, tz),
        }

        return createResponse(200, "Trends retrieved successfully", data)

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
def parseRange(rawRange):
    if rawRange is None:
        return DEFAULT_RANGE, None

    try:
        rangeDays = int(rawRange)
    except (TypeError, ValueError):
        return None, f"range must be one of: {', '.join(str(r) for r in sorted(VALID_RANGES))}"

    if rangeDays not in VALID_RANGES:
        return None, f"range must be one of: {', '.join(str(r) for r in sorted(VALID_RANGES))}"

    return rangeDays, None

@tracer.capture_method
def getUserTimezone(userId):
    user = dynamoRetry(
        USERS_TABLE.get_item,
        Key={"userId": userId},
    ).get("Item")

    if not user:
        return "UTC"

    return user.get("timezone") or "UTC"

@tracer.capture_method
def buildDateWindow(rangeDays, tz):
    nowLocal = datetime.now(tz)
    todayLocal = nowLocal.date()
    startLocalDate = todayLocal - timedelta(days=rangeDays - 1)

    dateLabels = [
        (startLocalDate + timedelta(days=i)).isoformat()
        for i in range(rangeDays)
    ]

    startLocalMidnight = datetime.combine(startLocalDate, time.min, tzinfo=tz)
    cutoffUtc = startLocalMidnight.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    return dateLabels, cutoffUtc

@tracer.capture_method
def fetchEntriesSince(table, userId, cutoffUtc):
    items = []
    lastKey = None

    while True:
        queryKwargs = {
            "KeyConditionExpression": Key("userId").eq(userId) & Key("createdAt#entryId").gte(cutoffUtc),
            "ScanIndexForward": False,
        }
        if lastKey:
            queryKwargs["ExclusiveStartKey"] = lastKey

        response = dynamoRetry(table.query, **queryKwargs)
        items.extend(response.get("Items", []))

        lastKey = response.get("LastEvaluatedKey")
        if not lastKey:
            break

    return items

@tracer.capture_method
def toLocalDateLabel(createdAt, tz):
    dt = datetime.strptime(createdAt[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).date().isoformat()

@tracer.capture_method
def aggregateSymptoms(entries, dateLabels, tz):
    severityByDay = defaultdict(list)
    nameCountByDay = defaultdict(Counter)

    for entry in entries:
        createdAt = entry.get("createdAt")
        if not createdAt:
            continue

        dayLabel = toLocalDateLabel(createdAt, tz)
        if dayLabel not in dateLabels:
            continue

        severity = entry.get("severity")
        if severity is not None:
            severityByDay[dayLabel].append(float(severity))

        symptomName = entry.get("symptomName")
        if symptomName:
            nameCountByDay[dayLabel][symptomName] += 1

    avgSeverity = []
    maxSeverity = []
    topSymptom = []

    for day in dateLabels:
        severities = severityByDay.get(day, [])
        avgSeverity.append(round(sum(severities) / len(severities), 2) if severities else None)
        maxSeverity.append(max(severities) if severities else None)

        counts = nameCountByDay.get(day)
        topSymptom.append(counts.most_common(1)[0][0] if counts else None)

    return {
        "avgSeverity": avgSeverity,
        "maxSeverity": maxSeverity,
        "topSymptom": topSymptom,
    }

@tracer.capture_method
def aggregateSleep(entries, dateLabels, tz):
    durationByDay = defaultdict(list)
    qualityByDay = defaultdict(list)

    for entry in entries:
        createdAt = entry.get("createdAt")
        if not createdAt:
            continue

        dayLabel = toLocalDateLabel(createdAt, tz)
        if dayLabel not in dateLabels:
            continue

        duration = entry.get("totalDuration")
        if duration is not None:
            durationByDay[dayLabel].append(float(duration))

        quality = entry.get("qualityRating")
        if quality is not None:
            qualityByDay[dayLabel].append(float(quality))

    avgDuration = []
    avgQuality = []

    for day in dateLabels:
        durations = durationByDay.get(day, [])
        qualities = qualityByDay.get(day, [])
        avgDuration.append(round(sum(durations) / len(durations), 1) if durations else None)
        avgQuality.append(round(sum(qualities) / len(qualities), 2) if qualities else None)

    return {
        "avgDuration": avgDuration,
        "avgQuality": avgQuality,
    }

@tracer.capture_method
def aggregateCounts(entries, dateLabels, tz):
    countByDay = defaultdict(int)

    for entry in entries:
        createdAt = entry.get("createdAt")
        if not createdAt:
            continue

        dayLabel = toLocalDateLabel(createdAt, tz)
        if dayLabel not in dateLabels:
            continue

        countByDay[dayLabel] += 1

    return {
        "count": [countByDay.get(day, 0) for day in dateLabels],
    }