import os
import json
import uuid
import boto3
from prompt import buildPrompt
from datetime import datetime
from dynamo_retry import dynamoRetry
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

VOICE_DRAFTS_TABLE_NAME = os.environ.get("VOICE_DRAFTS_TABLE_NAME")
TOKEN_USAGE_TABLE_NAME = os.environ.get("TOKEN_USAGE_TABLE_NAME")
VOICE_BUCKET = os.environ.get("VOICE_BUCKET")
TRANSCRIBE_JOB_PREFIX = os.environ.get("TRANSCRIBE_JOB_PREFIX")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION")

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
transcribe = boto3.client("transcribe")

VOICE_DRAFTS_TABLE = dynamodb.Table(VOICE_DRAFTS_TABLE_NAME)
TOKEN_USAGE_TABLE = dynamodb.Table(TOKEN_USAGE_TABLE_NAME) if TOKEN_USAGE_TABLE_NAME else None

logger = Logger()
tracer = Tracer()

VALID_TYPES = {"symptom", "medication", "food", "sleep"}

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        detail = event.get("detail", {})
        jobName = detail.get("TranscriptionJobName")
        jobStatus = detail.get("TranscriptionJobStatus")

        if not jobName.startswith(TRANSCRIBE_JOB_PREFIX):
            return {"ignored": True}

        rest = jobName[len(TRANSCRIBE_JOB_PREFIX):]
        userId, _, draftId = rest.partition("_")

        if not userId or not draftId:
            return {"ignored": True}

        if jobStatus == "FAILED":
            setDraftFailed(userId, draftId, "Transcription Failed")
            return {"status": "FAILED"}

        draft = getDraft(userId, draftId)
        if not draft:
            return {"ignored": True}

        transcript = readTranscript(draft["transcriptKey"])
        if not transcript.strip():
            setDraftFailed(userId, draftId, "Empty Transcript")
            return {"status": "FAILED"}

        timezone = draft.get("tz", "UTC")
        proposed = extractEntries(transcript, timezone, userId)

        updateVoiceDraftReady(userId, draftId, transcript, proposed)

        return {"status": "READY", "count": len(proposed)}

    except Exception as e:
        tracer.put_annotation("lambda_error", "true")
        tracer.put_metadata("message", str(e))
        logger.exception({"message": str(e)})
        try:
            detail = event.get("detail", {})
            jobName = detail.get("TranscriptionJobName", "")
            rest = jobName[len(TRANSCRIBE_JOB_PREFIX):]
            userId, _, draftId = rest.partition("_")
            if userId and draftId:
                setDraftFailed(userId, draftId, "Extraction error")
        except Exception:
            pass
        return {"status": "ERROR"}

@tracer.capture_method
def getDraft(userId, draftId):
    resp = dynamoRetry(
        VOICE_DRAFTS_TABLE.get_item, 
        Key={"userId": userId, "draftId": draftId}).get("Item")

    return resp

@tracer.capture_method
def setDraftFailed(userId, draftId, transcriptionMessage):
    dynamoRetry(
        VOICE_DRAFTS_TABLE.update_item,
        Key={"userId": userId, "draftId": draftId},
        UpdateExpression="SET #s = :s, failureReason = :r",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "FAILED", ":r": transcriptionMessage},
    )

@tracer.capture_method
def readTranscript(transcriptKey):
    obj = s3.get_object(Bucket=VOICE_BUCKET, Key=transcriptKey)
    data = json.loads(obj["Body"].read())
    transcripts = data.get("results", {}).get("transcripts", [])
    if transcripts:
        return transcripts[0].get("transcript", "")

    return ""

@tracer.capture_method
def extractEntries(transcript, timezone, userId):
    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    prompt = buildPrompt(transcript, timezone, now)

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "temperature": 0.1,
        "messages": [
            {
                "role": "user", 
                "content": prompt
            }
        ],
    })

    resp = bedrock.invoke_model(
        modelId = BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body
    )

    responseBody = json.loads(resp["body"].read())
    text = responseBody.get("content", [{}])[0].get("text", "")
    parsed = parseModelJson(text)

    usage = responseBody.get("usage", {}) or {}
    storeTokenUsage(
        userId,
        inputTokens=int(usage.get("input_tokens", 0)),
        outputTokens=int(usage.get("output_tokens", 0)),
    )

    entries = parsed.get("entries", []) if isinstance(parsed, dict) else []
    cleaned = []
    for e in entries:
        entryType = e.get("entryType")
        if entryType not in VALID_TYPES:
            continue

        cleaned.append({
            "clientEntryId": e.get("clientEntryId") or str(uuid.uuid4()),
            "entryType": entryType,
            "data": e.get("data", {}),
            "confidence": e.get("confidence", 0),
            "missingFields": e.get("missingFields", []),
            "warnings": e.get("warnings", []),
        })
    return cleaned

@tracer.capture_method
def parseModelJson(text):
    try:
        t = text.strip()
        if t.startswith("```"):
            lines = t.split("\n")
            t = "\n".join(lines[1:-1])
        return json.loads(t)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning({"message": "Failed to parse model JSON", "error": str(e)})
        return {"entries": []}

@tracer.capture_method
def updateVoiceDraftReady(userId, draftId, transcript, proposed):
    dynamoRetry(
            VOICE_DRAFTS_TABLE.update_item,
            Key={"userId": userId, "draftId": draftId},
            UpdateExpression="SET #s = :s, transcript = :t, proposedEntries = :p",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "READY",
                ":t": transcript,
                ":p": proposed,
            },
        )

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
            "operation": "voice_recognition",
            "model": BEDROCK_MODEL_ID,
            "inputTokens": inputTokens,
            "outputTokens": outputTokens,
            "totalTokens": totalTokens,
            "createdAt": now,
        }

        dynamoRetry(TOKEN_USAGE_TABLE.put_item, Item=payload)

    except Exception as e:
        logger.warning({"message": "Failed to record token usage", "error": str(e)})