"""
Seed script: generates test data for all diary entry types (symptom, medication,
food, sleep) directly into DynamoDB, for exercising the Timeline, Entry CRUD,
Pattern Analysis, and Insights features end-to-end.

USAGE:
    1. Fill in USER_ID below with the Cognito 'sub' of your test user.
    2. Confirm/adjust the table names and region (defaults follow the CDK
       naming convention: "{TABLE_PREFIX}{TableName}", e.g. "MedorraSymptoms").
    3. Run from the medorra-backend directory (with .venv activated):
           python scripts/seed_test_data.py

NOTES:
    - The Pattern Engine requires at least 14 distinct logging days before it
      will run correlation analysis (Requirement 7.1). NUM_DAYS defaults to 14
      so seeded data is immediately eligible for insight generation. Lower it
      if you only want to test Timeline/CRUD and don't care about Insights.
    - This script ALSO writes a record to the Users table with
      distinctLoggingDays set to NUM_DAYS, because the StreamProcessor Lambda
      checks that field before triggering Pattern Analysis. Without it, entries
      will seed fine but Insights will stay empty ("No patterns detected yet")
      even with 14+ days of data.
    - A deliberate correlation is injected into the generated data: every 3rd
      day's dinner is tagged "dairy", and the following day's "Headache"
      symptom severity is elevated (8-9 instead of the usual 2-4). This gives
      the LLM-based Pattern Engine a real signal to detect.
    - By default, this script also directly invokes the PatternAnalysis Lambda
      after seeding (INVOKE_PATTERN_ANALYSIS=True) so you get Insights
      immediately, instead of waiting up to 5 minutes for the async
      DynamoDB Streams -> EventBridge -> PatternAnalysis pipeline to fire.
    - This script writes directly to DynamoDB via boto3 (bypassing the API),
      so it works even before entries/auth endpoints are wired up on the
      frontend. It reuses the same entry dataclasses from the Lambda layer so
      the data shape always matches what the Lambdas expect.
"""

import os
import sys
import uuid
import random
from decimal import Decimal
from datetime import datetime, timedelta

import boto3

# ---------------------------------------------------------------------------
# CONFIGURATION — fill these in before running
# ---------------------------------------------------------------------------
USER_ID = "e9fa351c-8001-70cc-f764-60434a24a53c"  # Cognito 'sub' claim of the test user
NUM_DAYS = 14                      # Number of days of history to generate (>=14 to unlock Pattern Analysis)
INVOKE_PATTERN_ANALYSIS = True     # If True, directly invoke the PatternAnalysis Lambda after seeding

REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
TABLE_PREFIX = os.environ.get("TABLE_PREFIX", "Medorra")

USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME", f"{TABLE_PREFIX}Users")
SYMPTOMS_TABLE_NAME = os.environ.get("SYMPTOMS_TABLE_NAME", f"{TABLE_PREFIX}Symptoms")
MEDICATIONS_TABLE_NAME = os.environ.get("MEDICATIONS_TABLE_NAME", f"{TABLE_PREFIX}Medications")
FOOD_TABLE_NAME = os.environ.get("FOOD_TABLE_NAME", f"{TABLE_PREFIX}Food")
SLEEP_TABLE_NAME = os.environ.get("SLEEP_TABLE_NAME", f"{TABLE_PREFIX}Sleep")
PATTERN_ANALYSIS_FUNCTION_NAME = os.environ.get("PATTERN_ANALYSIS_FUNCTION_NAME", f"{TABLE_PREFIX}PatternAnalysis")

# ---------------------------------------------------------------------------
# Reuse the entry dataclasses from the shared Lambda layer so generated data
# always matches the exact shape the backend expects.
# ---------------------------------------------------------------------------
LAYER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "lambda", "Layers", "MedorraGenericLayer", "python"
)
sys.path.insert(0, os.path.abspath(LAYER_PATH))

from base_entry import BaseEntry            # noqa: E402
from symptom_entry import SymptomEntry       # noqa: E402
from medication_entry import MedicationEntry  # noqa: E402
from food_entry import FoodEntry, FoodItem    # noqa: E402
from sleep_entry import SleepEntry, SleepSegment  # noqa: E402

dynamodb = boto3.resource("dynamodb", region_name=REGION)
lambdaClient = boto3.client("lambda", region_name=REGION)


def convertFloats(value):
    """Recursively convert floats to Decimal for DynamoDB compatibility."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: convertFloats(v) for k, v in value.items()}
    if isinstance(value, list):
        return [convertFloats(v) for v in value]
    return value


def isoAt(date, hour, minute=0):
    """Build an ISO 8601 timestamp string (matching BaseEntry's format) for a given date/time."""
    dt = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def putEntry(tableName, entry):
    """Write an entry to DynamoDB with the correct createdAt#entryId sort key."""
    table = dynamodb.Table(tableName)
    item = entry.toDict()
    item["createdAt#entryId"] = BaseEntry.generateSortKey(entry.createdAt, entry.entryId)
    item = convertFloats(item)
    table.put_item(Item=item)
    return item


# ---------------------------------------------------------------------------
# Entry generators — one function per entry type, called once per day
# ---------------------------------------------------------------------------

SYMPTOM_NAMES = ["Headache", "Fatigue", "Joint Pain", "Nausea"]
MEDICATIONS = [
    {"name": "Ibuprofen", "dosageAmount": 200.0, "dosageUnit": "mg", "scheduleType": "as-needed"},
    {"name": "Vitamin D", "dosageAmount": 1000.0, "dosageUnit": "IU", "scheduleType": "scheduled"},
]
BREAKFAST_OPTIONS = [
    {"description": "Oatmeal with berries", "tags": ["gluten-free"]},
    {"description": "Scrambled eggs and toast", "tags": ["gluten"]},
    {"description": "Greek yogurt with granola", "tags": ["dairy"]},
]
LUNCH_OPTIONS = [
    {"description": "Grilled chicken salad", "tags": []},
    {"description": "Turkey sandwich", "tags": ["gluten"]},
    {"description": "Rice bowl with vegetables", "tags": ["gluten-free"]},
]
DINNER_OPTIONS = [
    {"description": "Grilled salmon with vegetables", "tags": []},
    {"description": "Pasta with cream sauce", "tags": ["dairy", "gluten"]},
    {"description": "Stir-fried tofu and rice", "tags": ["gluten-free"]},
]


def generateSymptomEntries(date, dairyYesterday):
    """1-2 symptom entries per day. Headache severity spikes the day after a dairy dinner."""
    entries = []

    headacheSeverity = random.randint(8, 9) if dairyYesterday else random.randint(2, 4)
    entries.append(
        SymptomEntry(
            userId=USER_ID,
            symptomName="Headache",
            severity=headacheSeverity,
            notes="Logged via seed script" if not dairyYesterday else "Woke up with a strong headache",
            createdAt=isoAt(date, 9, random.randint(0, 59)),
            timestamp=isoAt(date, 9, random.randint(0, 59)),
        )
    )

    if random.random() < 0.5:
        otherSymptom = random.choice(SYMPTOM_NAMES[1:])
        entries.append(
            SymptomEntry(
                userId=USER_ID,
                symptomName=otherSymptom,
                severity=random.randint(2, 6),
                notes="Logged via seed script",
                createdAt=isoAt(date, 20, random.randint(0, 59)),
                timestamp=isoAt(date, 20, random.randint(0, 59)),
            )
        )

    return entries


def generateMedicationEntries(date):
    """1-2 medication entries per day (one scheduled, one as-needed ~50% of days)."""
    entries = []

    scheduled = MEDICATIONS[1]
    entries.append(
        MedicationEntry(
            userId=USER_ID,
            medicationName=scheduled["name"],
            dosageAmount=scheduled["dosageAmount"],
            dosageUnit=scheduled["dosageUnit"],
            scheduleType=scheduled["scheduleType"],
            createdAt=isoAt(date, 8, 0),
            timestamp=isoAt(date, 8, 0),
        )
    )

    if random.random() < 0.5:
        asNeeded = MEDICATIONS[0]
        entries.append(
            MedicationEntry(
                userId=USER_ID,
                medicationName=asNeeded["name"],
                dosageAmount=asNeeded["dosageAmount"],
                dosageUnit=asNeeded["dosageUnit"],
                scheduleType=asNeeded["scheduleType"],
                notes="Taken for headache",
                createdAt=isoAt(date, 9, 30),
                timestamp=isoAt(date, 9, 30),
            )
        )

    return entries


def generateFoodEntries(date, injectDairy):
    """3 food entries per day (breakfast, lunch, dinner). Dinner tagged 'dairy' every 3rd day."""
    entries = []

    breakfast = random.choice(BREAKFAST_OPTIONS)
    entries.append(
        FoodEntry(
            userId=USER_ID,
            mealType="breakfast",
            items=[FoodItem(description=breakfast["description"], tags=breakfast["tags"])],
            createdAt=isoAt(date, 7, 30),
            timestamp=isoAt(date, 7, 30),
        )
    )

    lunch = random.choice(LUNCH_OPTIONS)
    entries.append(
        FoodEntry(
            userId=USER_ID,
            mealType="lunch",
            items=[FoodItem(description=lunch["description"], tags=lunch["tags"])],
            createdAt=isoAt(date, 12, 30),
            timestamp=isoAt(date, 12, 30),
        )
    )

    if injectDairy:
        dinnerItem = FoodItem(description="Creamy pasta with parmesan", tags=["dairy", "gluten"])
    else:
        dinner = random.choice(DINNER_OPTIONS)
        dinnerItem = FoodItem(description=dinner["description"], tags=dinner["tags"])

    entries.append(
        FoodEntry(
            userId=USER_ID,
            mealType="dinner",
            items=[dinnerItem],
            createdAt=isoAt(date, 19, 0),
            timestamp=isoAt(date, 19, 0),
        )
    )

    return entries


def generateSleepEntries(date):
    """1 sleep entry per day, representing the previous night's sleep."""
    previousNight = date - timedelta(days=1)
    startHour = random.choice([22, 23])
    endHour = random.choice([6, 7])
    durationHours = (24 - startHour) + endHour

    segment = SleepSegment(
        startTime=isoAt(previousNight, startHour, 0),
        endTime=isoAt(date, endHour, 0),
    )
    segment.calculateDuration()

    qualityRating = 8 if durationHours >= 7 else random.randint(4, 6)

    entry = SleepEntry(
        userId=USER_ID,
        segments=[segment],
        qualityRating=qualityRating,
        notes="Logged via seed script",
        createdAt=isoAt(date, endHour, 15),
        timestamp=isoAt(date, endHour, 15),
    )
    entry.calculateTotalDuration()

    return [entry]


def upsertUserLoggingDays(userId, distinctLoggingDays):
    """
    Write/update the Users table record with distinctLoggingDays.

    The StreamProcessor Lambda reads this field to decide whether a user is
    eligible for Pattern Analysis (Requirement 7.1: >= 14 distinct days).
    Without this record, seeded entries alone will never produce Insights.
    """
    table = dynamodb.Table(USERS_TABLE_NAME)
    table.update_item(
        Key={"userId": userId},
        UpdateExpression="SET distinctLoggingDays = :days, timeWindow = if_not_exists(timeWindow, :defaultWindow)",
        ExpressionAttributeValues={
            ":days": distinctLoggingDays,
            ":defaultWindow": 3,
        },
    )
    print(f"Users table updated: distinctLoggingDays={distinctLoggingDays}")


def invokePatternAnalysis(userId):
    """
    Directly invoke the PatternAnalysis Lambda for the seeded user, instead of
    waiting for the async DynamoDB Streams -> EventBridge pipeline (~5 min).

    The event shape mirrors what EventBridge would deliver: a "detail" dict
    containing userId, since PatternAnalysis is normally triggered that way.
    """
    payload = {"detail": {"userId": userId}}
    try:
        response = lambdaClient.invoke(
            FunctionName=PATTERN_ANALYSIS_FUNCTION_NAME,
            InvocationType="RequestResponse",
            Payload=json_dumps_bytes(payload),
        )
        result = response["Payload"].read().decode("utf-8")
        print(f"PatternAnalysis invoked. Response: {result}")
    except Exception as e:
        print(f"WARNING: Failed to invoke PatternAnalysis Lambda directly: {e}")
        print("Entries were still seeded. Insights may appear within 5 minutes")
        print("via the async Streams -> EventBridge pipeline instead, once")
        print("StreamProcessor picks up the next entry write for this user.")


def json_dumps_bytes(obj):
    import json as _json
    return _json.dumps(obj).encode("utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if USER_ID == "REPLACE_WITH_USER_ID":
        print("ERROR: Set USER_ID at the top of this script before running.")
        sys.exit(1)

    today = datetime.now()
    counts = {"symptom": 0, "medication": 0, "food": 0, "sleep": 0}

    for dayOffset in range(NUM_DAYS - 1, -1, -1):
        date = today - timedelta(days=dayOffset)
        dayIndex = NUM_DAYS - 1 - dayOffset  # 0-based, oldest first

        injectDairyToday = (dayIndex % 3 == 0)
        dairyYesterday = ((dayIndex - 1) % 3 == 0) if dayIndex > 0 else False

        for entry in generateSymptomEntries(date, dairyYesterday):
            entry.validate()
            putEntry(SYMPTOMS_TABLE_NAME, entry)
            counts["symptom"] += 1

        for entry in generateMedicationEntries(date):
            entry.validate()
            putEntry(MEDICATIONS_TABLE_NAME, entry)
            counts["medication"] += 1

        for entry in generateFoodEntries(date, injectDairyToday):
            entry.validate()
            putEntry(FOOD_TABLE_NAME, entry)
            counts["food"] += 1

        for entry in generateSleepEntries(date):
            entry.validate()
            putEntry(SLEEP_TABLE_NAME, entry)
            counts["sleep"] += 1

        print(f"Day {dayIndex + 1}/{NUM_DAYS} ({date.strftime('%Y-%m-%d')}) seeded"
              + (" [dairy dinner]" if injectDairyToday else ""))

    print("\nDone. Entries created:")
    for entryType, count in counts.items():
        print(f"  {entryType}: {count}")
    print(f"  total: {sum(counts.values())}")

    upsertUserLoggingDays(USER_ID, NUM_DAYS)

    if NUM_DAYS >= 14 and INVOKE_PATTERN_ANALYSIS:
        print("\nInvoking PatternAnalysis Lambda...")
        invokePatternAnalysis(USER_ID)
    elif NUM_DAYS < 14:
        print(f"\nNUM_DAYS={NUM_DAYS} is below the 14-day threshold — Insights")
        print("will show 'No patterns detected yet' until you seed >= 14 days.")


if __name__ == "__main__":
    main()
