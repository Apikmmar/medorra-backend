import os
import json
import boto3
from json_encoder import DecimalEncoder
from dynamo_retry import dynamoRetry
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

VOICE_DRAFTS_TABLE_NAME = os.environ.get("VOICE_DRAFTS_TABLE_NAME")
VOICE_BUCKET = os.environ.get("VOICE_BUCKET")
VOICE_TRANSCRIPT_PREFIX = os.environ.get("VOICE_TRANSCRIPT_PREFIX")
TRANSCRIBE_JOB_PREFIX = os.environ.get("TRANSCRIBE_JOB_PREFIX")
DEFAULT_LANGUAGE = os.environ.get("TRANSCRIBE_LANGUAGE")

dynamodb = boto3.resource("dynamodb")
transcribe = boto3.client("transcribe")

VOICE_DRAFTS_TABLE = dynamodb.Table(VOICE_DRAFTS_TABLE_NAME)

logger = Logger()
tracer = Tracer()

MEDIA_FORMATS = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "mp4",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
}

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        userId = event["requestContext"]["authorizer"]["claims"]["sub"]
        draftId = event.get("pathParameters", {}).get("draftId")

        if not draftId:
            return createResponse(400, "draftId is required", {"field": "draftId"})

        body = json.loads(event.get("body", "{}") or "{}")
        timezone = body.get("timezone") or "UTC"
        language = body.get("language") or DEFAULT_LANGUAGE

        draft = getDraft(userId, draftId)

        if not draft:
            return createResponse(404, "Draft not found", None)

        if draft.get("status") not in ("UPLOADING", "FAILED"):
            return createResponse(409, f"Draft cannot be processed in status {draft.get('status')}", None)

        audioKey = draft["audioKey"]
        contentType = draft.get("contentType", "audio/webm")
        mediaFormat = MEDIA_FORMATS.get(contentType, "webm")

        jobName = f"{TRANSCRIBE_JOB_PREFIX}{userId}_{draftId}"
        outputKey = f"{VOICE_TRANSCRIPT_PREFIX}{userId}/{draftId}.json"

        transcribe.start_transcription_job(
            TranscriptionJobName=jobName,
            LanguageCode=language,
            MediaFormat=mediaFormat,
            Media={"MediaFileUri": f"s3://{VOICE_BUCKET}/{audioKey}"},
            OutputBucketName=VOICE_BUCKET,
            OutputKey=outputKey,
        )

        updateVoiceTranscription(userId, draftId, outputKey, timezone, language)

        item = {
            "draftId": draftId,
            "status": "TRANSCRIBING"
        }

        return createResponse(200, "Transcription started", item)

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

@tracer.capture_method
def getDraft(userId, draftId):
    respDraft = dynamoRetry(
        VOICE_DRAFTS_TABLE.get_item, 
        Key={
            "userId": userId, 
            "draftId": draftId
            }
        ).get("Item")
    return respDraft

@tracer.capture_method
def updateVoiceTranscription(userId, draftId, outputKey, timezone, language):
    dynamoRetry(
        VOICE_DRAFTS_TABLE.update_item,
        Key={"userId": userId, "draftId": draftId},
        UpdateExpression="SET #s = :s, transcriptKey = :tk, tz = :tz, #lang = :lang",
        ExpressionAttributeNames={
            "#s": "status",
            "#lang": "language"
            },
        ExpressionAttributeValues={
            ":s": "TRANSCRIBING",
            ":tk": outputKey,
            ":tz": timezone,
            ":lang": language
        }
    )