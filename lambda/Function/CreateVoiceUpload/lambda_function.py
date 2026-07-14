import os
import json
import uuid
import time
import boto3
from datetime import datetime
from json_encoder import DecimalEncoder
from dynamo_retry import dynamoRetry
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

VOICE_DRAFTS_TABLE_NAME = os.environ.get("VOICE_DRAFTS_TABLE_NAME")
VOICE_BUCKET = os.environ.get("VOICE_BUCKET")
VOICE_AUDIO_PREFIX = os.environ.get("VOICE_AUDIO_PREFIX")
UPLOAD_URL_TTL = int(os.environ.get("UPLOAD_URL_TTL", "300"))

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

VOICE_DRAFTS_TABLE = dynamodb.Table(VOICE_DRAFTS_TABLE_NAME)

logger = Logger()
tracer = Tracer()

ALLOWED_CONTENT_TYPES = {
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
        body = json.loads(event.get("body") or "{}")
        contentType = body.get("contentType", "audio/webm")

        if contentType not in ALLOWED_CONTENT_TYPES:
            return createResponse(400, "Unsupported audio content type", {"field": "contentType"})

        ext = ALLOWED_CONTENT_TYPES[contentType]
        draftId = str(uuid.uuid4())
        audioKey = f"{VOICE_AUDIO_PREFIX}{userId}/{draftId}.{ext}"

        uploadUrl = uploadVoiceToUrl(audioKey, contentType)

        storeVoiceDraft(userId, draftId, audioKey, contentType)

        item = {
            "draftId": draftId,
            "uploadUrl": uploadUrl,
            "audioKey": audioKey,
            "contentType": contentType
        }

        return createResponse(200, "Upload URL created", item)

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
def uploadVoiceToUrl(audioKey, contentType):
    uploadUrl = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": VOICE_BUCKET,
            "Key": audioKey,
            "ContentType": contentType
        },
        ExpiresIn=UPLOAD_URL_TTL
    )

    return uploadUrl

@tracer.capture_method
def storeVoiceDraft(userId, draftId, audioKey, contentType):
    strDateTime = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    payload = {
        "userId": userId,
        "draftId": draftId,
        "status": "UPLOADING",
        "audioKey": audioKey,
        "contentType": contentType,
        "createdAt": strDateTime,
        "createdBy": "System",
        "updatedAt": strDateTime,
        "updatedBy": "System",
    }

    dynamoRetry(VOICE_DRAFTS_TABLE.put_item, Item=payload)