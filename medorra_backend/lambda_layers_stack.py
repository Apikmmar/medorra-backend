from aws_cdk import BundlingOptions, aws_lambda as lambda_
from constructs import Construct

def create_layers(scope: Construct):
    powertools_layer = lambda_.LayerVersion(
        scope, "PowertoolsLayer",
        code=lambda_.Code.from_asset(
            "lambda/Layers/PowertoolsLayer",
            bundling=BundlingOptions(
                image=lambda_.Runtime.PYTHON_3_14.bundling_image,
                command=["bash", "-c", "pip install -r requirements.txt -t /asset-output/python"]
            )
        ),
        compatible_runtimes=[lambda_.Runtime.PYTHON_3_14],
        description="powertools layer"
    )

    generic_layer = lambda_.LayerVersion(
        scope, "GenericLayer",
        code=lambda_.Code.from_asset("lambda/Layers/GenericLayer"),
        compatible_runtimes=[lambda_.Runtime.PYTHON_3_14],
        description="generic shared utilities layer"
    )

    return powertools_layer, generic_layer
