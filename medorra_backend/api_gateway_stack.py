from aws_cdk import (
    CfnOutput,
    aws_apigateway as apigw,
)
from constructs import Construct

CORS_OPTIONS = apigw.CorsOptions(
    allow_origins=[
        "http://localhost:3005",
        "https://medorra-frontend.vercel.app",
        "https://medorra-frontend-aafiqs-projects.vercel.app",
    ],
    allow_methods=apigw.Cors.ALL_METHODS,
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Amz-Date",
        "X-Api-Key",
        "X-Amz-Security-Token",
    ],
)


class ApiGatewayStack(Construct):

    def __init__(self, scope: Construct, construct_id: str, lambda_stack, cognito_stack, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.api = apigw.RestApi(
            self,
            "MedorraAPI",
            description="API for Medorra Web-App",
            rest_api_name=f"{prefix}-API",
            default_cors_preflight_options=CORS_OPTIONS,
            endpoint_configuration=apigw.EndpointConfiguration(
                types=[apigw.EndpointType.EDGE],
            ),
            deploy_options=apigw.StageOptions(
                throttling_rate_limit=25,
                throttling_burst_limit=50,
                method_options={
                    "/voice-entries/upload/POST": apigw.MethodDeploymentOptions(
                        throttling_rate_limit=2,
                        throttling_burst_limit=5,
                    ),
                    "/voice-entries/{draftId}/process/POST": apigw.MethodDeploymentOptions(
                        throttling_rate_limit=2,
                        throttling_burst_limit=5,
                    ),
                }
            )
        )

        self.authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "MedorraCognitoAuthorizer",
            cognito_user_pools=[cognito_stack.user_pool],
            authorizer_name=f"{prefix}-CognitoAuthorizer",
            identity_source="method.request.header.Authorization",
        )

        # --- Public endpoints (no authorization required) ---
        auth_resource = self.api.root.add_resource("auth")

        register_resource = auth_resource.add_resource("register")
        register_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.register_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        login_resource = auth_resource.add_resource("login")
        login_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.login_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        refresh_resource = auth_resource.add_resource("refresh")
        refresh_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.refresh_token_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # --- Protected endpoints (Cognito authorization required) ---
        entries_resource = self.api.root.add_resource("entries")

        symptom_resource = entries_resource.add_resource("symptom")
        symptom_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.create_symptom_entry_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        medication_resource = entries_resource.add_resource("medication")
        medication_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.create_medication_entry_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        food_resource = entries_resource.add_resource("food")
        food_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.create_food_entry_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        sleep_resource = entries_resource.add_resource("sleep")
        sleep_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.create_sleep_entry_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        entries_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.list_entries_by_type_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        timeline_resource = entries_resource.add_resource("timeline")
        timeline_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.list_all_entries_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        symptom_entry_resource = symptom_resource.add_resource("{entryId}")
        symptom_entry_resource.add_method(
            "PUT",
            apigw.LambdaIntegration(lambda_stack.update_symptom_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        medication_entry_resource = medication_resource.add_resource("{entryId}")
        medication_entry_resource.add_method(
            "PUT",
            apigw.LambdaIntegration(lambda_stack.update_medication_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        food_entry_resource = food_resource.add_resource("{entryId}")
        food_entry_resource.add_method(
            "PUT",
            apigw.LambdaIntegration(lambda_stack.update_food_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        sleep_entry_resource = sleep_resource.add_resource("{entryId}")
        sleep_entry_resource.add_method(
            "PUT",
            apigw.LambdaIntegration(lambda_stack.update_sleep_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        symptom_entry_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(lambda_stack.delete_symptom_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        medication_entry_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(lambda_stack.delete_medication_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        food_entry_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(lambda_stack.delete_food_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        sleep_entry_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(lambda_stack.delete_sleep_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        analysis_resource = self.api.root.add_resource("analysis")

        threshold_resource = analysis_resource.add_resource("threshold")
        threshold_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.check_logging_threshold_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        settings_resource = self.api.root.add_resource("settings")

        time_window_resource = settings_resource.add_resource("time-window")
        time_window_resource.add_method(
            "PUT",
            apigw.LambdaIntegration(lambda_stack.update_time_window_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        insights_resource = self.api.root.add_resource("insights")

        insights_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.list_insights_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        insight_id_resource = insights_resource.add_resource("{insightId}")
        respond_resource = insight_id_resource.add_resource("respond")
        respond_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.respond_insight_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        account_resource = auth_resource.add_resource("account")
        account_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(lambda_stack.request_account_deletion_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        batch_resource = entries_resource.add_resource("batch")
        batch_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.batch_get_entries_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        reminders_resource = settings_resource.add_resource("reminders")
        reminders_resource.add_method(
            "PUT",
            apigw.LambdaIntegration(lambda_stack.update_reminder_settings_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        push_resource = settings_resource.add_resource("push-subscription")
        push_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.save_push_subscription_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )
        push_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(lambda_stack.save_push_subscription_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        trends_resource = analysis_resource.add_resource("trends")
        trends_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.trends_analytics_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        voice_resource = self.api.root.add_resource("voice-entries")

        voice_upload_resource = voice_resource.add_resource("upload")
        voice_upload_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.create_voice_upload_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        voice_draft_resource = voice_resource.add_resource("{draftId}")
        voice_draft_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.get_voice_draft_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        voice_process_resource = voice_draft_resource.add_resource("process")
        voice_process_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.start_voice_transcription_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        voice_confirm_resource = voice_draft_resource.add_resource("confirm")
        voice_confirm_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.confirm_voice_draft_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        search_resource = entries_resource.add_resource("search")
        search_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.search_entries_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )


        # --- Output ---
        CfnOutput(self, "ApiUrl", value=self.api.url, description="Medorra API Gateway URL")
