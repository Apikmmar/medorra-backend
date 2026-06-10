from aws_cdk import (
    Stack,)
from constructs import Construct

from .dynamo_db_stack import DynamoDBStack
from .lambda_function_stack import LambdaStack
from .api_gateway_stack import ApiGatewayStack

class MedorraBackendStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        dynamo_db_stack = DynamoDBStack(self, "DynamoDBStack", prefix=prefix)
        lambda_stack = LambdaStack(self, "LambdaStack", dynamo_db_stack=dynamo_db_stack, prefix=prefix)
        api_gateway_stack = ApiGatewayStack(self, "ApiGatewayStack", lambda_stack=lambda_stack, prefix=prefix)