import os
import re
import json
import uuid
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from dynamo_retry import dynamoRetry
from json_encoder import DecimalEncoder
from user_isolation import enforceUserIsolation
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from prompt import promptBuilder

USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")
SYMPTOMS_TABLE_NAME = os.environ.get("SYMPTOMS_TABLE_NAME")
MEDICATIONS_TABLE_NAME = os.environ.get("MEDICATIONS_TABLE_NAME")
FOOD_TABLE_NAME = os.environ.get("FOOD_TABLE_NAME")
SLEEP_TABLE_NAME = os.environ.get("SLEEP_TABLE_NAME")
INSIGHTS_TABLE_NAME = os.environ.get("INSIGHTS_TABLE_NAME")
TOKEN_USAGE_TABLE_NAME = os.environ.get("TOKEN_USAGE_TABLE_NAME")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION")
INSIGHT_BUCKET = os.environ.get("INSIGHT_BUCKET")
POLLY_VOICE_ID = os.environ.get("POLLY_VOICE_ID")
POLLY_ENGINE = os.environ.get("POLLY_ENGINE")

dynamodb = boto3.resource("dynamodb")
bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
polly = boto3.client("polly", region_name=BEDROCK_REGION)
s3 = boto3.client("s3")

USERS_TABLE = dynamodb.Table(USERS_TABLE_NAME)
SYMPTOMS_TABLE = dynamodb.Table(SYMPTOMS_TABLE_NAME)
MEDICATIONS_TABLE = dynamodb.Table(MEDICATIONS_TABLE_NAME)
FOOD_TABLE = dynamodb.Table(FOOD_TABLE_NAME)
SLEEP_TABLE = dynamodb.Table(SLEEP_TABLE_NAME)
INSIGHTS_TABLE = dynamodb.Table(INSIGHTS_TABLE_NAME)
TOKEN_USAGE_TABLE = dynamodb.Table(TOKEN_USAGE_TABLE_NAME) if TOKEN_USAGE_TABLE_NAME else None

TABLE_MAP = {
    "symptom": SYMPTOMS_TABLE,
    "medication": MEDICATIONS_TABLE,
    "food": FOOD_TABLE,
    "sleep": SLEEP_TABLE,
}

MINIMUM_LOGGING_DAYS = 14
DEFAULT_TIME_WINDOW = 3
MIN_CONFIDENCE = 0.6
MAX_INSIGHTS = 20
GSI_TIMESTAMP = "gsi-timestamp"

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        detail = event.get("detail", {})
        userId = detail.get("userId") or event.get("userId")

        if not userId:
            return createResponse(400, "Missing userId in event.", None)

        userConfig = getUserConfig(userId)

        if not userConfig:
            return createResponse(404, "User not found", None)

        distinctLoggingDays = userConfig.get("distinctLoggingDays", 0)

        if distinctLoggingDays < MINIMUM_LOGGING_DAYS:
            remainingDays = MINIMUM_LOGGING_DAYS - distinctLoggingDays
            return createResponse(200, f"Threshold not met. {remainingDays} more days needed.", {"remainingDays": remainingDays})

        timeWindow = getTimeWindow(userConfig)
        entries = fetchAllEntries(userId, timeWindow)

        if not entries:
            return createResponse(200, "No entries in time window", None)

        insights = analyzeWithBedrock(userId, entries, timeWindow)

        validInsights = [i for i in insights if i.get("confidenceScore", 0) > MIN_CONFIDENCE]

        validInsights.sort(key=lambda x: x.get("confidenceScore", 0), reverse=True)
        validInsights = validInsights[:MAX_INSIGHTS]

        storeInsights(userId, validInsights)

        return createResponse(200, "Analysis complete", {"insightsCount": len(validInsights)})

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
def getUserConfig(userId):
    response = dynamoRetry(
        USERS_TABLE.get_item,
        Key={"userId": userId},
    )
    return response.get("Item")

@tracer.capture_method
def getTimeWindow(userConfig):
    return userConfig.get("timeWindow", DEFAULT_TIME_WINDOW)

@tracer.capture_method
def fetchAllEntries(userId, lookbackDays):
    cutoffDate = (datetime.utcnow() - timedelta(days=int(lookbackDays))).strftime('%Y-%m-%dT%H:%M:%S')

    allEntries = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for entryType, table in TABLE_MAP.items():
            futures[entryType] = executor.submit(
                queryTableSinceDate, table, userId, cutoffDate, entryType
            )

        for entryType, future in futures.items():
            allEntries[entryType] = enforceUserIsolation(userId, future.result())

    return allEntries

@tracer.capture_method
def queryTableSinceDate(table, userId, cutoffDate, entryType):
    items = []
    lastKey = None

    while True:
        queryKwargs = {
            "IndexName": GSI_TIMESTAMP,
            "KeyConditionExpression": Key("userId").eq(userId) & Key("timestamp").gte(cutoffDate),
            "ScanIndexForward": False,
        }
        if lastKey:
            queryKwargs["ExclusiveStartKey"] = lastKey

        response = dynamoRetry(table.query, **queryKwargs)

        for item in response.get("Items", []):
            item["entryType"] = entryType
            items.append(item)

        lastKey = response.get("LastEvaluatedKey")
        if not lastKey:
            break

    return items

@tracer.capture_method
def analyzeWithBedrock(userId, entries, timeWindow):
    symptomsText = formatEntries(entries.get("symptom", []), "symptom")
    medicationsText = formatEntries(entries.get("medication", []), "medication")
    foodText = formatEntries(entries.get("food", []), "food")
    sleepText = formatEntries(entries.get("sleep", []), "sleep")

    prompt = promptBuilder(symptomsText, medicationsText, foodText, sleepText, timeWindow)

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.2,
    })

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body,
    )

    responseBody = json.loads(response["body"].read())
    responseText = responseBody.get("content", [{}])[0].get("text", "")

    usage = responseBody.get("usage", {}) or {}
    storeTokenUsage(
        userId,
        inputTokens=int(usage.get("input_tokens", 0)),
        outputTokens=int(usage.get("output_tokens", 0)),
    )

    insights = parseBedrockResponse(responseText)

    return insights

@tracer.capture_method
def formatEntries(entries, entryType):
    if not entries:
        return "No entries"

    lines = []

    for entry in entries:
        if entryType == "symptom":
            lines.append(f"[{entry.get('timestamp', '')}] entryId={entry.get('entryId', '')} symptom={entry.get('symptomName', '')} severity={entry.get('severity', '')}")
        elif entryType == "medication":
            lines.append(f"[{entry.get('timestamp', '')}] entryId={entry.get('entryId', '')} medication={entry.get('medicationName', '')} dosage={entry.get('dosageAmount', 'unspecified')}{entry.get('dosageUnit', '')}")
        elif entryType == "food":
            items = entry.get("items", [])
            descriptions = [item.get("description", "") for item in items if isinstance(item, dict)]
            lines.append(f"[{entry.get('timestamp', '')}] entryId={entry.get('entryId', '')} meal={entry.get('mealType', '')} items={', '.join(descriptions)}")
        elif entryType == "sleep":
            lines.append(f"[{entry.get('timestamp', '')}] entryId={entry.get('entryId', '')} duration={entry.get('totalDuration', 0)}min quality={entry.get('qualityRating', '')}")

    return "\n".join(lines)

@tracer.capture_method
def parseBedrockResponse(responseText):
    text = (responseText or "").strip()

    if text.startswith("```"):
        fence = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()

    def loadList(candidate):
        parsed = json.loads(candidate)
        if not isinstance(parsed, list):
            raise ValueError("Bedrock response is not a JSON array")
        return parsed

    try:
        return loadList(text)
    except (json.JSONDecodeError, ValueError):

        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return loadList(match.group(0))
            except (json.JSONDecodeError, ValueError):
                pass

    logger.warning({
        "message": "Failed to parse Bedrock response",
        "rawResponse": text[:1000],
        "rawLength": len(text),
    })
    return []

@tracer.capture_method
def storeInsights(userId, insights):
    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    existingInsights = getExistingInsights(userId)

    for existing in existingInsights:
        if existing.get("status") == "active":
            deleteInsights(userId, existing)

    for insight in insights:
        insightId = str(uuid.uuid4())
        confidenceScore = insight.get("confidenceScore", 0)

        confidenceStr = f"{confidenceScore:.2f}"
        sortKey = f"{confidenceStr}#{insightId}"

        summary = insight.get("summary", "")
        audioKey = synthesizeInsightAudio(userId, insightId, summary)

        payload = {
            "userId": userId,
            "confidence#insightId": sortKey,
            "insightId": insightId,
            "trigger": insight.get("trigger", {}),
            "correlatedSymptom": insight.get("correlatedSymptom", ""),
            "averageDelay": insight.get("averageDelay", ""),
            "confidenceScore": confidenceScore,
            "summary": summary,
            "supportingEntryIds": insight.get("supportingEntryIds", []),
            "status": "active",
            "status#confidence#insightId": f"active#{confidenceStr}#{insightId}",
            "disclaimer": "These insights are observational patterns and not medical diagnoses.",
            "createdAt": now,
            "updatedAt": now,
        }

        if audioKey:
            payload["audioKey"] = audioKey

        dynamoRetry(
            INSIGHTS_TABLE.put_item, 
            Item=payload
        )

@tracer.capture_method
def deleteInsights(userId, existing):
    dynamoRetry(
        INSIGHTS_TABLE.delete_item,
        Key={
            "userId": userId,
            "confidence#insightId": existing["confidence#insightId"],
        },
    )

@tracer.capture_method
def getExistingInsights(userId):
    items = []
    lastKey = None

    while True:
        queryKwargs = {
            "KeyConditionExpression": Key("userId").eq(userId),
        }

        if lastKey:
            queryKwargs["ExclusiveStartKey"] = lastKey

        response = dynamoRetry(INSIGHTS_TABLE.query, **queryKwargs)
        items.extend(response.get("Items", []))

        lastKey = response.get("LastEvaluatedKey")
        if not lastKey:
            break

    return items

@tracer.capture_method
def storeTokenUsage(userId, inputTokens, outputTokens):

    if TOKEN_USAGE_TABLE is None:
        logger.warning({"message": "TOKEN_USAGE_TABLE_NAME not configured; skipping usage record"})
        return

    try:
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        usageId = str(uuid.uuid4())
        totalTokens = inputTokens + outputTokens

        payload = {
            "userId": userId,
            "usageId": usageId,
            "createdAt#usageId": f"{now}#{usageId}",
            "operation": "pattern_analysis",
            "model": BEDROCK_MODEL_ID,
            "inputTokens": inputTokens,
            "outputTokens": outputTokens,
            "totalTokens": totalTokens,
            "createdAt": now,
        }

        dynamoRetry(TOKEN_USAGE_TABLE.put_item, Item=payload)

    except Exception as e:
        logger.warning({"message": "Failed to record token usage", "error": str(e)})

@tracer.capture_method
def synthesizeInsightAudio(userId, insightId, text):
    if not INSIGHT_BUCKET or not text:
        return None

    try:
        response = polly.synthesize_speech(
            Text=text,
            VoiceId=POLLY_VOICE_ID,
            Engine=POLLY_ENGINE,
            OutputFormat="mp3",
        )

        audioStream = response.get("AudioStream")
        if audioStream is None:
            return None

        audioBytes = audioStream.read()
        key = f"polly-voice/{userId}/{insightId}.mp3"

        s3.put_object(
            Bucket=INSIGHT_BUCKET,
            Key=key,
            Body=audioBytes,
            ContentType="audio/mpeg",
        )

        return key

    except ClientError as e:
        logger.warning({"message": "Failed to synthesize insight audio", "error": str(e)})
        return None
