from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_iam as iam,
    aws_s3 as s3,
)
from constructs import Construct

from .dynamo_db_stack import DynamoDBStack
from .cognito_stack import CognitoStack
from .lambda_function_stack import LambdaStack
from .api_gateway_stack import ApiGatewayStack
from .event_bridge_stack import EventBridgeStack

class MedorraBackendStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        medorra_s3_bucket = s3.Bucket(
            self, "s3-medorra-bucket",
            bucket_name=f"{prefix.lower()}-s3-medorra-bucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(expiration=Duration.days(90)),
            ],
        )

        dynamo_db_stack = DynamoDBStack(self, "DynamoDBStack", prefix=prefix)
        cognito_stack = CognitoStack(self, "CognitoStack", prefix=prefix)
        lambda_stack = LambdaStack(self, "LambdaStack", dynamo_db_stack=dynamo_db_stack, cognito_stack=cognito_stack,medorra_s3_bucket=medorra_s3_bucket, prefix=prefix)
        api_gateway_stack = ApiGatewayStack(self, "ApiGatewayStack", lambda_stack=lambda_stack, cognito_stack=cognito_stack, prefix=prefix)
        event_bridge_stack = EventBridgeStack(self, "EventBridgeStack", dynamo_db_stack=dynamo_db_stack, lambda_stack=lambda_stack, prefix=prefix)