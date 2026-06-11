from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
)
from constructs import Construct
from .lambda_layers_stack import create_layers

class LambdaStack(Construct):

    def __init__(self, scope: Construct, construct_id: str, dynamo_db_stack, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        powertools_layer, medorra_generic_layer = create_layers(self)
        tables = dynamo_db_stack.tables

        self.function_lambda = lambda_.Function(
            self, "FunctionNameLambda",
            function_name=f"{prefix}FunctionName",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/FunctionName"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer],
            environment={
                "USERS_TABLE_NAME": tables['Users'].table_name,
            },
        )

        self.function2_lambda = lambda_.Function(
            self, "FunctionName2Lambda",
            function_name=f"{prefix}FunctionName2",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/FunctionName2"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer],
            environment={
                "USERS_TABLE_NAME": tables['Users'].table_name,
            },
        )

        all_lambdas = [
            self.function_lambda,
            self.function2_lambda,
        ]

        for table in tables.values():
            for fn in all_lambdas:
                table.grant_read_write_data(fn)
