import os
import json
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

cognitoClient = boto3.client("cognito-idp")

USER_POOL_ID = os.environ.get("USER_POOL_ID")
CLIENT_ID = os.environ.get("USER_POOL_CLIENT_ID")

AUTH_ERROR_MESSAGE = "Invalid email or password"

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    try:
        body = json.loads(event.get("body", "{}"))

        email = body.get("email")
        password = body.get("password")

        if not email or not password:
            return createResponse(401, AUTH_ERROR_MESSAGE, None)

        response = cognitoClient.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": email,
                "PASSWORD": password,
            }
        )

        authResult = response.get("AuthenticationResult", {})

        data = {
            "accessToken": authResult.get("AccessToken"),
            "idToken": authResult.get("IdToken"),
            "refreshToken": authResult.get("RefreshToken"),
            "expiresIn": authResult.get("ExpiresIn"),
            "tokenType": authResult.get("TokenType"),
        }

        return createResponse(200, "Login Successful", data)

    except cognitoClient.exceptions.NotAuthorizedException:
        return createResponse(401, AUTH_ERROR_MESSAGE, None)

    except cognitoClient.exceptions.UserNotFoundException:
        return createResponse(401, AUTH_ERROR_MESSAGE, None)

    except cognitoClient.exceptions.UserNotConfirmedException:
        return createResponse(403, "Please verify your email before logging in", None)

    except cognitoClient.exceptions.TooManyRequestsException:
        return createResponse(429, "Too many attempts. Please try again later", None)

    except ClientError as e:
        errorCode = e.response.get("Error", {}).get("Code", "")
        if errorCode == "PasswordResetRequiredException":
            return createResponse(403, "Account temporarily locked. Try again in 15 minutes", None)
        return createResponse(401, AUTH_ERROR_MESSAGE, None)

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
