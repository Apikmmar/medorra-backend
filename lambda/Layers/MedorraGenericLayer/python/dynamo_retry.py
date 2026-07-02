import time
import random
from decimal import Decimal
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

logger = Logger()

RETRYABLE_ERROR_CODES = {
    "ProvisionedThroughputExceededException",
    "ThrottlingException",
    "RequestLimitExceeded",
    "InternalServerError",
    "ServiceUnavailable",
}

MAX_RETRIES = 3
BASE_DELAY = 0.1

# Kwargs whose values may contain application data (and therefore floats)
# that DynamoDB's boto3 resource API requires as Decimal.
_FLOAT_CONVERT_KWARGS = {"Item", "ExpressionAttributeValues"}


def _convertFloatsToDecimal(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _convertFloatsToDecimal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_convertFloatsToDecimal(v) for v in value]
    return value


def dynamoRetry(operation, **kwargs):
    lastException = None

    kwargs = {
        key: (_convertFloatsToDecimal(value) if key in _FLOAT_CONVERT_KWARGS else value)
        for key, value in kwargs.items()
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = operation(**kwargs)
            return response

        except ClientError as e:
            errorCode = e.response.get("Error", {}).get("Code", "")
            lastException = e

            if errorCode not in RETRYABLE_ERROR_CODES:
                raise

            if attempt >= MAX_RETRIES:
                logger.error({
                    "message": "All retries exhausted",
                    "errorCode": errorCode,
                    "attempts": attempt + 1,
                })
                raise

            delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.05)
            logger.warning({
                "message": f"Retrying DynamoDB operation",
                "errorCode": errorCode,
                "attempt": attempt + 1,
                "delay": delay,
            })
            time.sleep(delay)

    raise lastException