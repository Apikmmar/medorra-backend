import time
from datetime import datetime

# 15 minutes in seconds
INACTIVITY_TIMEOUT = 15 * 60

def checkSessionActivity(lastActivityTimestamp: str) -> dict:
    if not lastActivityTimestamp:
        return {"active": False, "message": "Session expired due to inactivity"}

    try:
        lastActivity = datetime.fromisoformat(lastActivityTimestamp.replace('Z', '+00:00'))
        now = datetime.now(lastActivity.tzinfo)
        elapsed = (now - lastActivity).total_seconds()

        if elapsed > INACTIVITY_TIMEOUT:
            return {
                "active": False,
                "message": "Session expired due to inactivity",
                "error": "SESSION_TIMEOUT",
            }

        return {
            "active": True,
            "remainingSeconds": int(INACTIVITY_TIMEOUT - elapsed),
        }

    except (ValueError, TypeError):
        return {"active": False, "message": "Session expired due to inactivity"}


def updateLastActivity() -> str:
    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def buildSessionTimeoutResponse() -> dict:
    return {
        "statusCode": 401,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": '{"error": "SESSION_TIMEOUT", "message": "Session expired due to inactivity"}',
    }
