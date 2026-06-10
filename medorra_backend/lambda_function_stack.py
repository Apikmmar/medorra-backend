from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_events,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct
from .lambda_layers_stack import create_layers

class LambdaStack(Construct):

    def __init__(self, scope: Construct, construct_id: str, dynamo_db_stack, bucket, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        powertools_layer, generic_layer = create_layers(self)
        tables = dynamo_db_stack.tables

        self.create_order_lambda = lambda_.Function(
            self, "CreateNewOrderLambda",
            function_name=f"{prefix}CreateNewOrder",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/CreateNewOrder"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, generic_layer],
            environment={
                "ORDER_TABLE_NAME": tables['Orders'].table_name,
            },
        )
