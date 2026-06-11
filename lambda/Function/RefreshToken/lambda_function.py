import os
import json
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

cognitoClient = boto3.client("cognito-idp")

CLIENT_ID = os.environ.get("USER_POOL_CLIENT_ID")

logger = Logger()
tracer = Tracer()


@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        body = json.loads(event.get("body", "{}"))
        refreshToken = body.get("refreshToken", "")

        if not refreshToken:
            return createResponse(400, "Refresh token is required", None)

        response = cognitoClient.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={
                "REFRESH_TOKEN": refreshToken,
            },
        )

        authResult = response.get("AuthenticationResult", {})

        result = {
            "accessToken": authResult.get("AccessToken"),
            "idToken": authResult.get("IdToken"),
            "expiresIn": authResult.get("ExpiresIn"),
            "tokenType": authResult.get("TokenType"),
        }

        return createResponse(200, "Token refreshed successfully", result)

    except cognitoClient.exceptions.NotAuthorizedException:
        return createResponse(401, "Session expired, please re-authenticate", None)

    except ClientError:
        return createResponse(401, "Session expired, please re-authenticate", None)

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
