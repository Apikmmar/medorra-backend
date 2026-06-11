import os
import json
import boto3
from botocore.exceptions import ClientError
from registration_validator import validateRegistration
from base_entry import ValidationError
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

        validateRegistration(email, password)

        cognitoClient.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {"Name": "email", "Value": email}
            ]
        )

        return createResponse(200, "Registration successful. Please verify your email.", {"email": email,})

    except ValidationError as e:
        return createResponse(400, e.message, {"field": e.field_name})

    except cognitoClient.exceptions.UsernameExistsException:
        return createResponse(409, "Email is already in use", None)

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
