from aws_cdk import (
    Duration,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_sqs as sqs,
    aws_iam as iam,
)
from constructs import Construct

class EventBridgeStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, dynamo_db_stack, lambda_stack, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        def make_dlq(name: str) -> sqs.Queue:
            return sqs.Queue(
                self,
                name,
                queue_name=f"{prefix}-{name}",
                retention_period=Duration.days(14),
                encryption=sqs.QueueEncryption.SQS_MANAGED,
                enforce_ssl=True
            )

        self.stream_dlq = make_dlq("StreamProcessorDLQ")
        self.pattern_analysis_dlq = make_dlq("PatternAnalysisDLQ")
        self.account_deletion_dlq = make_dlq("AccountDeletionDLQ")
        self.reminders_dlq = make_dlq("LoggingRemindersDLQ")
        self.voice_extract_dlq = make_dlq("VoiceExtractDLQ")

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
                    bisect_batch_on_error=True,
                    max_record_age=Duration.hours(24),
                    on_failure=lambda_event_sources.SqsDlq(self.stream_dlq),
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
            targets=[
                targets.LambdaFunction(
                    lambda_stack.pattern_analysis_lambda,
                    dead_letter_queue=self.pattern_analysis_dlq,
                    retry_attempts=2,
                    max_event_age=Duration.hours(2),
                )
            ],
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
                targets.LambdaFunction(
                    lambda_stack.process_account_deletion_lambda,
                    dead_letter_queue=self.account_deletion_dlq,
                    retry_attempts=2,
                    max_event_age=Duration.hours(2),
                )
            ],
        )

        self.event_bus.grant_put_events_to(lambda_stack.request_account_deletion_lambda)

        self.reminder_schedule_rule = events.Rule(
            self,
            "LoggingReminderSchedule",
            rule_name=f"{prefix}-LoggingReminderSchedule",
            schedule=events.Schedule.rate(Duration.hours(1)),
            targets=[
                targets.LambdaFunction(
                    lambda_stack.send_logging_reminders_lambda,
                    dead_letter_queue=self.reminders_dlq,
                    retry_attempts=2,
                    max_event_age=Duration.hours(2),
                )
            ],
        )

        self.transcribe_completion_rule = events.Rule(
            self,
            "VoiceTranscribeCompletionRule",
            rule_name=f"{prefix}-VoiceTranscribeCompletion",
            event_pattern=events.EventPattern(
                source=["aws.transcribe"],
                detail_type=["Transcribe Job State Change"],
                detail={
                    "TranscriptionJobStatus": ["COMPLETED", "FAILED"],
                },
            ),
            targets=[
                targets.LambdaFunction(
                    lambda_stack.extract_voice_entries_lambda,
                    dead_letter_queue=self.voice_extract_dlq,
                    retry_attempts=2,
                    max_event_age=Duration.hours(2),
                )
            ],
        )
