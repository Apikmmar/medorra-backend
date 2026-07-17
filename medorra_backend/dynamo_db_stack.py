from aws_cdk import (
    RemovalPolicy,
    aws_dynamodb as dynamodb
)
from constructs import Construct

class DynamoDBStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        tableList = [
            'Users',
            'Symptoms',
            'Medications',
            'Food',
            'Sleep',
            'Insights',
            'TokenUsage',
            'VoiceDrafts',
            'Feedbacks'
        ]

        partition_keys = {
            'Feedbacks': 'feedbackId',
        }

        sort_keys = {
            'Symptoms': 'createdAt#entryId',
            'Medications': 'createdAt#entryId',
            'Food': 'createdAt#entryId',
            'Sleep': 'createdAt#entryId',
            'Insights': 'confidence#insightId',
            'TokenUsage': 'createdAt#usageId',
            'VoiceDrafts': 'draftId',
        }

        stream_tables = ['Symptoms', 'Medications', 'Food', 'Sleep']

        self.tables = {}

        for table in tableList:
            partition_key = partition_keys.get(table, 'userId')

            table_kwargs = {
                'table_name': f"{prefix}{table}",
                'partition_key': dynamodb.Attribute(name=partition_key, type=dynamodb.AttributeType.STRING),
                'billing_mode': dynamodb.BillingMode.PAY_PER_REQUEST,
                'encryption': dynamodb.TableEncryption.AWS_MANAGED,
                'point_in_time_recovery': True,
                'removal_policy': RemovalPolicy.DESTROY,
            }

            if table in sort_keys:
                table_kwargs['sort_key'] = dynamodb.Attribute(
                    name=sort_keys[table], type=dynamodb.AttributeType.STRING
                )

            if table in stream_tables:
                table_kwargs['stream'] = dynamodb.StreamViewType.NEW_AND_OLD_IMAGES

            ddb_table = dynamodb.Table(self, table, **table_kwargs)
            self.tables[table] = ddb_table

            if table == 'Insights':
                ddb_table.add_global_secondary_index(
                    partition_key=dynamodb.Attribute(name='userId', type=dynamodb.AttributeType.STRING),
                    sort_key=dynamodb.Attribute(name='status#confidence#insightId', type=dynamodb.AttributeType.STRING),
                    index_name='-'.join(['gsi', 'status', 'confidence']),
                    projection_type=dynamodb.ProjectionType.ALL,
                )

            if table == 'Users':
                ddb_table.add_global_secondary_index(
                    partition_key=dynamodb.Attribute(name='reminderEnabledFlag', type=dynamodb.AttributeType.STRING),
                    sort_key=dynamodb.Attribute(name='reminderHour', type=dynamodb.AttributeType.NUMBER),
                    index_name='gsi-reminders',
                    projection_type=dynamodb.ProjectionType.ALL,
                )

            if table in stream_tables:
                ddb_table.add_global_secondary_index(
                    partition_key=dynamodb.Attribute(name='userId', type=dynamodb.AttributeType.STRING),
                    sort_key=dynamodb.Attribute(name='timestamp', type=dynamodb.AttributeType.STRING),
                    index_name='gsi-timestamp',
                    projection_type=dynamodb.ProjectionType.ALL,
                )