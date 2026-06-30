import aws_cdk as core
import aws_cdk.assertions as assertions

from medorra_backend.medorra_backend_stack import MedorraBackendStack

# Smoke test: ensure the stack synthesizes without errors
def test_stack_synthesizes():
    app = core.App()
    stack = MedorraBackendStack(app, "medorra-backend", prefix="Medorra")
    template = assertions.Template.from_stack(stack)

    # Verify DynamoDB tables are created (6 tables expected)
    template.resource_count_is("AWS::DynamoDB::Table", 6)
