from aws_cdk import (
    CfnOutput,
    aws_apigateway as apigw,
)
from constructs import Construct

CORS_OPTIONS = apigw.CorsOptions(
    allow_origins=apigw.Cors.ALL_ORIGINS,
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

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        lambda_stack,
        cognito_stack,
        prefix: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create REST API with TLS 1.2+ enforcement.
        # The default execute-api endpoint enforces TLS 1.2+ automatically.
        # For custom domains, SecurityPolicy.TLS_1_2 must be set on the DomainName resource.
        self.api = apigw.RestApi(
            self,
            "MedorraAPI",
            description="API for Medorra Web-App",
            rest_api_name=f"{prefix}-API",
            default_cors_preflight_options=CORS_OPTIONS,
            endpoint_configuration=apigw.EndpointConfiguration(
                types=[apigw.EndpointType.EDGE],
            ),
        )

        # Create Cognito authorizer for protected endpoints
        self.authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "MedorraCognitoAuthorizer",
            cognito_user_pools=[cognito_stack.user_pool],
            authorizer_name=f"{prefix}-CognitoAuthorizer",
            identity_source="method.request.header.Authorization",
        )

        # --- Protected endpoints (require Cognito authorization) ---

        # /entries resource
        entries_resource = self.api.root.add_resource("entries")

        # POST /entries - Create new entry
        entries_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.function_lambda),
            authorizer=self.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # GET /entries - List entries (paginated, filterable)
        entries_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.function_lambda),
            authorizer=self.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # /entries/{entryId} resource
        entry_resource = entries_resource.add_resource("{entryId}")

        # PUT /entries/{entryId} - Update existing entry
        entry_resource.add_method(
            "PUT",
            apigw.LambdaIntegration(lambda_stack.function_lambda),
            authorizer=self.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # DELETE /entries/{entryId} - Delete entry
        entry_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(lambda_stack.function_lambda),
            authorizer=self.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # /insights resource
        insights_resource = self.api.root.add_resource("insights")

        # GET /insights - List user's insights (sorted by confidence)
        insights_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.function2_lambda),
            authorizer=self.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # /insights/{id}/respond resource
        insight_id_resource = insights_resource.add_resource("{id}")
        insight_respond_resource = insight_id_resource.add_resource("respond")

        # POST /insights/{id}/respond - Dismiss or confirm an insight
        insight_respond_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.function2_lambda),
            authorizer=self.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # --- Public endpoints (no authorization required) ---

        # /auth resource
        auth_resource = self.api.root.add_resource("auth")

        # POST /auth/register - Register new account
        register_resource = auth_resource.add_resource("register")
        register_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.function2_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # POST /auth/login - Authenticate
        login_resource = auth_resource.add_resource("login")
        login_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.function2_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # POST /auth/refresh - Refresh token
        refresh_resource = auth_resource.add_resource("refresh")
        refresh_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.function2_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # --- Output ---
        CfnOutput(
            self,
            "ApiUrl",
            value=self.api.url,
            description="Medorra API Gateway URL",
        )
