from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
)
from constructs import Construct
from .lambda_layers_stack import create_layers

class LambdaStack(Construct):

    def __init__(self, scope: Construct, construct_id: str, dynamo_db_stack, cognito_stack, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        powertools_layer, medorra_generic_layer = create_layers(self)
        tables = dynamo_db_stack.tables

        self.register_lambda = lambda_.Function(
            self, "RegisterLambda",
            function_name=f"{prefix}Register",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/Register"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USER_POOL_ID": cognito_stack.user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": cognito_stack.user_pool_client.user_pool_client_id, 
            },
        )

        self.login_lambda = lambda_.Function(
            self, "LoginLambda",
            function_name=f"{prefix}Login",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/Login"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USER_POOL_ID": cognito_stack.user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": cognito_stack.user_pool_client.user_pool_client_id, 
            },
        )

        self.refresh_token_lambda = lambda_.Function(
            self, "RefreshTokenLambda",
            function_name=f"{prefix}RefreshToken",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/RefreshToken"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USER_POOL_CLIENT_ID": cognito_stack.user_pool_client.user_pool_client_id, 
            },
        )

        all_lambdas = [
            self.register_lambda,
            self.login_lambda,
            self.refresh_token_lambda,
        ]

        for table in tables.values():
            for fn in all_lambdas:
                table.grant_read_write_data(fn)
