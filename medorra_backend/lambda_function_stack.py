from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_cognito as cognito,
)
from constructs import Construct
from .lambda_layers_stack import create_layers

class LambdaStack(Construct):

    def __init__(self, scope: Construct, construct_id: str, dynamo_db_stack, cognito_stack,medorra_s3_bucket, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        powertools_layer, medorra_generic_layer, medorra_pywebpush_layer = create_layers(self)
        tables = dynamo_db_stack.tables

        self.post_confirmation_lambda = lambda_.Function(
            self, "PostConfirmationLambda",
            function_name=f"{prefix}PostConfirmation",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/PostConfirmation"),
            timeout=Duration.seconds(30),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USERS_TABLE_NAME": tables['Users'].table_name,
            },
        )

        cognito_stack.user_pool.add_trigger(
            cognito.UserPoolOperation.POST_CONFIRMATION,
            self.post_confirmation_lambda,
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

        self.create_symptom_entry_lambda = lambda_.Function(
            self, "CreateSymptomEntryLambda",
            function_name=f"{prefix}CreateSymptomEntry",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/CreateSymptomEntry"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "SYMPTOMS_TABLE_NAME": tables['Symptoms'].table_name
            },
        )

        self.create_medication_entry_lambda = lambda_.Function(
            self, "CreateMedicationEntryLambda",
            function_name=f"{prefix}CreateMedicationEntry",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/CreateMedicationEntry"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "MEDICATIONS_TABLE_NAME": tables['Medications'].table_name
            },
        )

        self.create_food_entry_lambda = lambda_.Function(
            self, "CreateFoodEntryLambda",
            function_name=f"{prefix}CreateFoodEntry",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/CreateFoodEntry"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "FOOD_TABLE_NAME": tables['Food'].table_name
            },
        )

        self.create_sleep_entry_lambda = lambda_.Function(
            self, "CreateSleepEntryLambda",
            function_name=f"{prefix}CreateSleepEntry",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/CreateSleepEntry"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "SLEEP_TABLE_NAME": tables['Sleep'].table_name
            },
        )

        self.list_entries_by_type_lambda = lambda_.Function(
            self, "ListEntriesByTypeLambda",
            function_name=f"{prefix}ListEntriesByType",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/ListEntriesByType"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "SYMPTOMS_TABLE_NAME": tables['Symptoms'].table_name,
                "MEDICATIONS_TABLE_NAME": tables['Medications'].table_name,
                "FOOD_TABLE_NAME": tables['Food'].table_name,
                "SLEEP_TABLE_NAME": tables['Sleep'].table_name,
            },
        )

        self.list_all_entries_lambda = lambda_.Function(
            self, "ListAllEntriesLambda",
            function_name=f"{prefix}ListAllEntries",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/ListAllEntries"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "SYMPTOMS_TABLE_NAME": tables['Symptoms'].table_name,
                "MEDICATIONS_TABLE_NAME": tables['Medications'].table_name,
                "FOOD_TABLE_NAME": tables['Food'].table_name,
                "SLEEP_TABLE_NAME": tables['Sleep'].table_name,
            },
        )

        self.update_medication_lambda = lambda_.Function(
            self, "UpdateMedicationEntryLambda",
            function_name=f"{prefix}UpdateMedicationEntry",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/UpdateMedicationEntry"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "MEDICATIONS_TABLE_NAME": tables['Medications'].table_name,
            },
        )

        self.update_food_lambda = lambda_.Function(
            self, "UpdateFoodEntryLambda",
            function_name=f"{prefix}UpdateFoodEntry",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/UpdateFoodEntry"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "FOOD_TABLE_NAME": tables['Food'].table_name,
            },
        )

        self.update_symptom_lambda = lambda_.Function(
            self, "UpdateSymptomEntryLambda",
            function_name=f"{prefix}UpdateSymptomEntry",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/UpdateSymptomEntry"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "SYMPTOMS_TABLE_NAME": tables['Symptoms'].table_name,
            },
        )

        self.update_sleep_lambda = lambda_.Function(
            self, "UpdateSleepEntryLambda",
            function_name=f"{prefix}UpdateSleepEntry",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/UpdateSleepEntry"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "SLEEP_TABLE_NAME": tables['Sleep'].table_name,
            },
        )

        self.delete_medication_lambda = lambda_.Function(
            self, "DeleteMedicationEntryLambda",
            function_name=f"{prefix}DeleteMedicationEntry",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/DeleteMedicationEntry"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "MEDICATIONS_TABLE_NAME": tables['Medications'].table_name,
            },
        )

        self.delete_food_lambda = lambda_.Function(
            self, "DeleteFoodEntryLambda",
            function_name=f"{prefix}DeleteFoodEntry",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/DeleteFoodEntry"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "FOOD_TABLE_NAME": tables['Food'].table_name,
            },
        )

        self.delete_symptom_lambda = lambda_.Function(
            self, "DeleteSymptomEntryLambda",
            function_name=f"{prefix}DeleteSymptomEntry",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/DeleteSymptomEntry"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "SYMPTOMS_TABLE_NAME": tables['Symptoms'].table_name,
            },
        )

        self.delete_sleep_lambda = lambda_.Function(
            self, "DeleteSleepEntryLambda",
            function_name=f"{prefix}DeleteSleepEntry",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/DeleteSleepEntry"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "SLEEP_TABLE_NAME": tables['Sleep'].table_name,
            },
        )
        
        self.check_logging_threshold_lambda = lambda_.Function(
            self, "CheckLoggingThresholdLambda",
            function_name=f"{prefix}CheckLoggingThreshold",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/CheckLoggingThreshold"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USERS_TABLE_NAME": tables['Users'].table_name,
            },
        )

        self.update_time_window_lambda = lambda_.Function(
            self, "UpdateTimeWindowLambda",
            function_name=f"{prefix}UpdateTimeWindow",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/UpdateTimeWindow"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USERS_TABLE_NAME": tables['Users'].table_name,
            },
        )

        self.pattern_analysis_lambda = lambda_.Function(
            self, "PatternAnalysisLambda",
            function_name=f"{prefix}PatternAnalysis",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/PatternAnalysis"),
            timeout=Duration.seconds(300),
            memory_size=256,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USERS_TABLE_NAME": tables['Users'].table_name,
                "SYMPTOMS_TABLE_NAME": tables['Symptoms'].table_name,
                "MEDICATIONS_TABLE_NAME": tables['Medications'].table_name,
                "SLEEP_TABLE_NAME": tables['Sleep'].table_name,
                "FOOD_TABLE_NAME": tables['Food'].table_name,
                "INSIGHTS_TABLE_NAME": tables['Insights'].table_name,
                "TOKEN_USAGE_TABLE_NAME": tables['TokenUsage'].table_name,
                "BEDROCK_MODEL_ID": 'us.anthropic.claude-sonnet-4-6',
                "BEDROCK_REGION": 'us-west-2',
                "INSIGHT_BUCKET": medorra_s3_bucket.bucket_name,
                "POLLY_VOICE_ID": "Joanna",
                "POLLY_ENGINE": "neural",
            },
        )

        self.pattern_analysis_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"]
            )
        )

        self.pattern_analysis_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["polly:SynthesizeSpeech"],
                resources=["*"]
            )
        )

        medorra_s3_bucket.grant_put(self.pattern_analysis_lambda)

        self.stream_processor_lambda = lambda_.Function(
            self, "StreamProcessorLambda",
            function_name=f"{prefix}StreamProcessor",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/StreamProcessor"),
            timeout=Duration.seconds(60),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USERS_TABLE_NAME": tables["Users"].table_name,
                "EVENT_BUS_NAME": f"{prefix}-EntryEventBus",
            },
        )

        self.list_insights_lambda = lambda_.Function(
            self, "ListInsightsLambda",
            function_name=f"{prefix}ListInsights",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/ListInsights"),
            timeout=Duration.seconds(300),
            memory_size=256,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "INSIGHTS_TABLE_NAME": tables["Insights"].table_name,
                "USERS_TABLE_NAME": tables["Users"].table_name,
                "SYMPTOMS_TABLE_NAME": tables["Symptoms"].table_name,
                "MEDICATIONS_TABLE_NAME": tables["Medications"].table_name,
                "FOOD_TABLE_NAME": tables["Food"].table_name,
                "SLEEP_TABLE_NAME": tables["Sleep"].table_name,
                "INSIGHT_BUCKET": medorra_s3_bucket.bucket_name,
            },
        )

        medorra_s3_bucket.grant_read(self.list_insights_lambda)

        self.respond_insight_lambda = lambda_.Function(
            self, "RespondInsightLambda",
            function_name=f"{prefix}RespondInsight",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/ResponseInsights"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "INSIGHTS_TABLE_NAME": tables["Insights"].table_name,
            },
        )

        self.request_account_deletion_lambda = lambda_.Function(
            self, "RequestAccountDeletionLambda",
            function_name=f"{prefix}RequestAccountDeletion",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/RequestAccountDeletion"),
            timeout=Duration.seconds(5),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USERS_TABLE_NAME": tables["Users"].table_name,
                "EVENT_BUS_NAME": f"{prefix}-EntryEventBus",
            },
        )

        self.process_account_deletion_lambda = lambda_.Function(
            self, "ProcessAccountDeletionLambda",
            function_name=f"{prefix}ProcessAccountDeletion",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/ProcessAccountDeletion"),
            timeout=Duration.seconds(300),
            memory_size=256,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USERS_TABLE_NAME": tables["Users"].table_name,
                "SYMPTOMS_TABLE_NAME": tables["Symptoms"].table_name,
                "MEDICATIONS_TABLE_NAME": tables["Medications"].table_name,
                "FOOD_TABLE_NAME": tables["Food"].table_name,
                "SLEEP_TABLE_NAME": tables["Sleep"].table_name,
                "INSIGHTS_TABLE_NAME": tables["Insights"].table_name,
                "SENDER_EMAIL": "noreply@medorra.com",
            },
        )

        self.process_account_deletion_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail"],
                resources=["*"],
            )
        )

        self.batch_get_entries_lambda  = lambda_.Function(
            self, "BatchGetEntryLambdaLambda",
            function_name=f"{prefix}BatchGetEntryLambda",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/BatchGetEntryLambda"),
            timeout=Duration.seconds(300),
            memory_size=256,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "SYMPTOMS_TABLE_NAME": tables["Symptoms"].table_name,
                "MEDICATIONS_TABLE_NAME": tables["Medications"].table_name,
                "FOOD_TABLE_NAME": tables["Food"].table_name,
                "SLEEP_TABLE_NAME": tables["Sleep"].table_name,
            },
        )

        self.update_reminder_settings_lambda = lambda_.Function(
            self, "UpdateReminderSettingsLambda",
            function_name=f"{prefix}UpdateReminderSettings",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/UpdateReminderSettings"),
            timeout=Duration.seconds(30),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USERS_TABLE_NAME": tables["Users"].table_name
            },
        )

        self.save_push_subscription_lambda = lambda_.Function(
            self, "SavePushSubscriptionLambda",
            function_name=f"{prefix}SavePushSubscription",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/SavePushSubscription"),
            timeout=Duration.seconds(30),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USERS_TABLE_NAME": tables["Users"].table_name
            },
        )

        self.send_logging_reminders_lambda = lambda_.Function(
            self, "SendLoggingRemindersLambda",
            function_name=f"{prefix}SendLoggingReminders",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/SendLoggingReminders"),
            timeout=Duration.seconds(300),
            memory_size=256,
            layers=[powertools_layer, medorra_generic_layer, medorra_pywebpush_layer],
            environment={
                "USERS_TABLE_NAME": tables["Users"].table_name,
                "VAPID_PRIVATE_KEY": "private_key.pem",
                "VAPID_SUBJECT": "mailto:noreply@medorra.com",
            },
        )

        self.trends_analytics_lambda = lambda_.Function(
            self, "TrendsAnalyticsLambda",
            function_name=f"{prefix}TrendsAnalytics",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/TrendsAnalytics"),
            timeout=Duration.seconds(300),
            memory_size=256,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USERS_TABLE_NAME": tables["Users"].table_name,
                "SYMPTOMS_TABLE_NAME": tables["Symptoms"].table_name,
                "MEDICATIONS_TABLE_NAME": tables["Medications"].table_name,
                "FOOD_TABLE_NAME": tables["Food"].table_name,
                "SLEEP_TABLE_NAME": tables["Sleep"].table_name,
            },
        )

        self.create_voice_upload_lambda = lambda_.Function(
            self, "CreateVoiceUploadLambda",
            function_name=f"{prefix}CreateVoiceUpload",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/CreateVoiceUpload"),
            timeout=Duration.seconds(30),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "VOICE_DRAFTS_TABLE_NAME": tables["VoiceDrafts"].table_name,
                "VOICE_BUCKET": medorra_s3_bucket.bucket_name,
                "VOICE_AUDIO_PREFIX": "voice/",
                "VOICE_TRANSCRIPT_PREFIX": "voice-transcripts/",
                "TRANSCRIBE_JOB_PREFIX": "medorra_voice_",
            },
        )

        self.start_voice_transcription_lambda = lambda_.Function(
            self, "StartVoiceTranscriptionLambda",
            function_name=f"{prefix}StartVoiceTranscription",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/StartVoiceTranscription"),
            timeout=Duration.seconds(30),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "VOICE_DRAFTS_TABLE_NAME": tables["VoiceDrafts"].table_name,
                "VOICE_BUCKET": medorra_s3_bucket.bucket_name,
                "VOICE_AUDIO_PREFIX": "voice/",
                "VOICE_TRANSCRIPT_PREFIX": "voice-transcripts/",
                "TRANSCRIBE_JOB_PREFIX": "medorra_voice_",
                "TRANSCRIBE_LANGUAGE": "en-US"
            },
        )

        self.extract_voice_entries_lambda = lambda_.Function(
            self, "ExtractVoiceEntriesLambda",
            function_name=f"{prefix}ExtractVoiceEntries",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/ExtractVoiceEntries"),
            timeout=Duration.seconds(120),
            memory_size=256,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "VOICE_DRAFTS_TABLE_NAME": tables["VoiceDrafts"].table_name,
                "VOICE_BUCKET": medorra_s3_bucket.bucket_name,
                "VOICE_AUDIO_PREFIX": "voice/",
                "VOICE_TRANSCRIPT_PREFIX": "voice-transcripts/",
                "TRANSCRIBE_JOB_PREFIX": "medorra_voice_",
                "TOKEN_USAGE_TABLE_NAME": tables["TokenUsage"].table_name,
                "BEDROCK_MODEL_ID": "us.anthropic.claude-sonnet-4-6",
                "BEDROCK_REGION": "us-west-2",
            },
        )

        self.get_voice_draft_lambda = lambda_.Function(
            self, "GetVoiceDraftLambda",
            function_name=f"{prefix}GetVoiceDraft",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/GetVoiceDraft"),
            timeout=Duration.seconds(30),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "VOICE_DRAFTS_TABLE_NAME": tables["VoiceDrafts"].table_name,
                "VOICE_BUCKET": medorra_s3_bucket.bucket_name,
                "VOICE_AUDIO_PREFIX": "voice/",
                "VOICE_TRANSCRIPT_PREFIX": "voice-transcripts/",
                "TRANSCRIBE_JOB_PREFIX": "medorra_voice_",
            },
        )

        self.confirm_voice_draft_lambda = lambda_.Function(
            self, "ConfirmVoiceDraftLambda",
            function_name=f"{prefix}ConfirmVoiceDraft",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/ConfirmVoiceDraft"),
            timeout=Duration.seconds(60),
            memory_size=256,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "VOICE_DRAFTS_TABLE_NAME": tables["VoiceDrafts"].table_name,
                "VOICE_BUCKET": medorra_s3_bucket.bucket_name,
                "VOICE_AUDIO_PREFIX": "voice/",
                "VOICE_TRANSCRIPT_PREFIX": "voice-transcripts/",
                "TRANSCRIBE_JOB_PREFIX": "medorra_voice_",
                "SYMPTOMS_TABLE_NAME": tables["Symptoms"].table_name,
                "MEDICATIONS_TABLE_NAME": tables["Medications"].table_name,
                "FOOD_TABLE_NAME": tables["Food"].table_name,
                "SLEEP_TABLE_NAME": tables["Sleep"].table_name,
            },
        )

        medorra_s3_bucket.grant_put(self.create_voice_upload_lambda)
        medorra_s3_bucket.grant_read_write(self.start_voice_transcription_lambda)
        medorra_s3_bucket.grant_read(self.extract_voice_entries_lambda)

        self.start_voice_transcription_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["transcribe:StartTranscriptionJob"],
                resources=["*"],
            )
        )
        self.extract_voice_entries_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["transcribe:GetTranscriptionJob"],
                resources=["*"],
            )
        )
        self.extract_voice_entries_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )

        self.search_entries_lambda = lambda_.Function(
            self, "SearchEntriesLambda",
            function_name=f"{prefix}SearchEntries",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/SearchEntries"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "SYMPTOMS_TABLE_NAME": tables['Symptoms'].table_name,
                "MEDICATIONS_TABLE_NAME": tables['Medications'].table_name,
                "FOOD_TABLE_NAME": tables['Food'].table_name,
                "SLEEP_TABLE_NAME": tables['Sleep'].table_name,
            },
        )

        self.create_feedback_lambda = lambda_.Function(
            self, "CreateFeedbackLambda",
            function_name=f"{prefix}CreateFeedback",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/CreateFeedback"),
            timeout=Duration.seconds(30),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "FEEDBACK_TABLE_NAME": tables['Feedbacks'].table_name,
            },
        )

        all_lambdas = [
            self.post_confirmation_lambda,
            self.login_lambda,
            self.refresh_token_lambda,
            self.create_symptom_entry_lambda,
            self.create_medication_entry_lambda,
            self.create_food_entry_lambda,
            self.create_sleep_entry_lambda,
            self.list_entries_by_type_lambda,
            self.list_all_entries_lambda,
            self.update_symptom_lambda,
            self.update_medication_lambda,
            self.update_food_lambda,
            self.update_sleep_lambda,
            self.delete_symptom_lambda,
            self.delete_medication_lambda,
            self.delete_food_lambda,
            self.delete_sleep_lambda,
            self.check_logging_threshold_lambda,
            self.update_time_window_lambda,
            self.pattern_analysis_lambda,
            self.stream_processor_lambda,
            self.list_insights_lambda,
            self.respond_insight_lambda,
            self.request_account_deletion_lambda,
            self.process_account_deletion_lambda,
            self.batch_get_entries_lambda,
            self.update_reminder_settings_lambda,
            self.save_push_subscription_lambda,
            self.send_logging_reminders_lambda,
            self.trends_analytics_lambda,
            self.create_voice_upload_lambda,
            self.start_voice_transcription_lambda,
            self.extract_voice_entries_lambda,
            self.get_voice_draft_lambda,
            self.confirm_voice_draft_lambda,
            self.search_entries_lambda,
            self.create_feedback_lambda,
        ]

        for table in tables.values():
            for fn in all_lambdas:
                table.grant_read_write_data(fn)
