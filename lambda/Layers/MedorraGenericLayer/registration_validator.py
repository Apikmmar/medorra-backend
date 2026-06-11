import re
from base_entry import ValidationError

EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
)
PASSWORD_UPPERCASE = re.compile(r'[A-Z]')
PASSWORD_LOWECASE = re.compile(r'[a-z]')
PASSWORD_DIGIT = re.compile(r'[0-9]')

def ValidateRegistration(email, password):
    validateEmail(email)
    validatePassword(password)

    return {"valid": True}

def validateEmail(email):
    if not email or not email.strip():
        raise ValidationError("email", "Email is required")

    if len(email) > 254:
        raise ValidationError("email", "Email must be 254 characters or less")

    if not EMAIL_REGEX.match(email):
        raise ValidationError("email", "Invalid email format")

def validatePassword(password):
    if not password:
        raise ValidationError("password", "Password is requored")

    if len(password) < 8:
        raise ValidationError("password", "Password must be at least 8 characters")

    if len(password) > 128:
        raise ValidationError("password", "Password must be 128 characters or less")

    if not PASSWORD_UPPERCASE.search(password):
        raise ValidationError("password", "Password must contain at least one uppercase letter")

    if not PASSWORD_LOWERCASE.search(password):
        raise ValidationError("password", "Password must contain at least one lowercase letter")

    if not PASSWORD_DIGIT.search(password):
        raise ValidationError("password", "Password must contain at least one digit")


def handleDuplicateEmail(email: str, existingEmails: list) -> None:
    if email.lower() in [e.lower() for e in existingEmails]:
        raise ValidationError("email", "Email is already in use")