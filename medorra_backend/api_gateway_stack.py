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
        )

        # TODO: Add Cognito authorizer when protected endpoints (entries/insights) are built (tasks 5, 8)
        # self.authorizer = apigw.CognitoUserPoolsAuthorizer(
        #     self,
        #     "MedorraCognitoAuthorizer",
        #     cognito_user_pools=[cognito_stack.user_pool],
        #     authorizer_name=f"{prefix}-CognitoAuthorizer",
        #     identity_source="method.request.header.Authorization",
        # )

        # --- Public endpoints (no authorization required) ---

        # /auth resource
        auth_resource = self.api.root.add_resource("auth")

        # POST /auth/register
        register_resource = auth_resource.add_resource("register")
        register_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.register_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # POST /auth/login
        login_resource = auth_resource.add_resource("login")
        login_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.login_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # POST /auth/refresh
        refresh_resource = auth_resource.add_resource("refresh")
        refresh_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.refresh_token_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # --- Output ---
        CfnOutput(self, "ApiUrl", value=self.api.url, description="Medorra API Gateway URL")
