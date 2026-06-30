from aws_cdk import (
    Duration,
    aws_cognito as cognito,
)
from constructs import Construct


class CognitoStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Cognito User Pool with email sign-in and password policy
        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"{prefix}UserPool",
            # Email as the sign-in alias (username attribute)
            sign_in_aliases=cognito.SignInAliases(email=True),
            # Self sign-up enabled
            self_sign_up_enabled=True,
            # Email verification
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            # Verification email configuration
            user_verification=cognito.UserVerificationConfig(
                email_subject="Medorra - Verify your email address",
                email_body="Welcome to Medorra! Your verification code is {####}",
                email_style=cognito.VerificationEmailStyle.CODE,
            ),
            # Password policy: min 8 chars, require uppercase, lowercase, digits
            # Note: CDK does not expose a max password length setting directly.
            # AWS Cognito enforces a max of 256 chars by default; application-level
            # validation should enforce the 128-char max per Requirement 1.1.
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_uppercase=True,
                require_lowercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            # Custom attributes
            custom_attributes={
                "timezone": cognito.StringAttribute(
                    mutable=True,
                    max_len=50,
                ),
            },
            # Standard attributes - email required with max 254 chars
            # Note: Email max length (254 chars) is enforced by RFC 5321 and
            # application-level validation per Requirement 1.1.
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
            ),
            # Enable advanced security mode for account lockout protection
            # AWS Cognito Advanced Security handles adaptive authentication including
            # account lockout after repeated failed attempts.
            # Note: The exact lockout configuration (5 failures in 15 min → 15-min lock)
            # as specified in Requirement 1.7 may need to be configured via AWS Console
            # or a custom Pre-Authentication Lambda trigger, as CDK does not expose
            # granular lockout thresholds directly.
            advanced_security_mode=cognito.AdvancedSecurityMode.ENFORCED,
        )

        # Create User Pool Client with token TTL of 24 hours
        self.user_pool_client = cognito.UserPoolClient(
            self,
            "UserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name=f"{prefix}UserPoolClient",
            # Token validity: 24 hours for both access and ID tokens
            access_token_validity=Duration.hours(24),
            id_token_validity=Duration.hours(24),
            # Refresh token validity (default 30 days)
            refresh_token_validity=Duration.days(30),
            # Auth flows
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),
            # Prevent user existence errors (opaque error messages per Requirement 1.3)
            prevent_user_existence_errors=True,
        )
