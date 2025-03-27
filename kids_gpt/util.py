import re

def characteristics_reducer(a: list, b: list) -> list:
    return list(set(a + b))

def validate_email(email: str) -> bool:
    # Regular expression to validate email format
    email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    # Match the email with the regex
    return bool(re.match(email_regex, email))