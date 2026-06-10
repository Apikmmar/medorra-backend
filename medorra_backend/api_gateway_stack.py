from aws_cdk import (
    CfnOutput,
    aws_apigateway as apigw,
)
from constructs import Construct

CORS_OPTIONS = apigw.CorsOptions(
    allow_origins=apigw.Cors.ALL_ORIGINS,
    allow_methods=apigw.Cors.ALL_METHODS,
    allow_headers=apigw.Cors.DEFAULT_HEADERS,
)

class ApiGatewayStack(Construct):

    def __init__(self, scope: Construct, construct_id: str, lambda_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        api = apigw.RestApi(
            self, "MedorraAPI",
            description="API for Medorra Web-App",
            rest_api_name=f"Medorra-API",
            default_cors_preflight_options=CORS_OPTIONS,
        )

        def add_resource(path: str, fn, methods: list[str]):
            resource = api.root.add_resource(path)
            for method in methods:
                resource.add_method(method, apigw.LambdaIntegration(fn))
            return resource