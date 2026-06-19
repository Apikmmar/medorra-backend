from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
)
from constructs import Construct
from .lambda_layers_stack import create_layers

class LambdaStack(Construct):

    def __init__(self, scope: Construct, construct_id: str, dynamo_db_stack, cognito_stack, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        powertools_layer, medorra_generic_layer = create_layers(self)
        tables = dynamo_db_stack.tables

        self.register_lambda = lambda_.Function(
            self, "RegisterLambda",
            function_name=f"{prefix}Register",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/Function/Register"),
            timeout=Duration.seconds(300),
            memory_size=128,
            layers=[powertools_layer, medorra_generic_layer],
            environment={
                "USER_POOL_ID": cognito_stack.user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": cognito_stack.user_pool_client.user_pool_client_id, 
            },
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
            function_name=f"{prefix}CreateSymptomEntryn",
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

        all_lambdas = [
            self.register_lambda,
            self.login_lambda,
            self.refresh_token_lambda,
            self.refresh_token_lambda,
            self.refresh_token_lambda,
            self.refresh_token_lambda,
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
        ]

        for table in tables.values():
            for fn in all_lambdas:
                table.grant_read_write_data(fn)
