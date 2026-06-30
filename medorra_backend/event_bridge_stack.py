from aws_cdk import (
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_iam as iam,
)
from constructs import Construct

class EventBridgeStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, dynamo_db_stack, lambda_stack, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.event_bus = events.EventBus(
            self, "MedorraEventBus",
            event_bus_name=f"{prefix}-EntryEventBus",
        )

        stream_tables = ["Symptoms", "Medications", "Food", "Sleep"]

        for table_name in stream_tables:
            table = dynamo_db_stack.tables[table_name]
            lambda_stack.stream_processor_lambda.add_event_source(
                lambda_event_sources.DynamoEventSource(
                    table,
                    starting_position=lambda_.StartingPosition.LATEST,
                    batch_size=10,
                    retry_attempts=3,
                )
            )

        self.event_bus.grant_put_events_to(lambda_stack.stream_processor_lambda)

        self.analytics_rule = events.Rule(
            self,
            "PatternAnalysisTriggerRule",
            rule_name=f"{prefix}-PatternAnalysisTrigger",
            event_bus=self.event_bus,
            event_pattern=events.EventPattern(
                source=["medorra.entries"],
                detail_type=["EntryCreated"],
            ),
            targets=[targets.LambdaFunction(lambda_stack.pattern_analysis_lambda)],
        )

        self.delete_rule = events.Rule(
            self,
            "AccountDeletionRule",
            rule_name=f"{prefix}-AccountDeletionTrigger",
            event_bus=self.event_bus,
            event_pattern=events.EventPattern(
                source=["medorra.account"],
                detail_type=["AccountDeletionRequested"],
            ),
            targets=[
                targets.LambdaFunction(lambda_stack.process_account_deletion_lambda)
            ],
        )

        self.event_bus.grant_put_events_to(lambda_stack.request_account_deletion_lambda)
