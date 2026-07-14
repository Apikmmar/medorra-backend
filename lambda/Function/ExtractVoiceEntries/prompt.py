def buildPrompt(transcript, timezone, nowLocal):
    return (
        "You extract structured health diary entries from a spoken transcript. "
        "Return ONLY valid JSON, no prose, no code fences.\n\n"
        f"User timezone: {timezone}. Current local time: {nowLocal}.\n\n"
        "One transcript may contain MULTIPLE entries of different types. "
        "Valid entryType values: symptom, medication, food, sleep.\n\n"
        "Schemas:\n"
        "- symptom.data: { symptomName (string), severity (int 1-10, ONLY if clearly stated), "
        "timestamp (ISO8601 with offset, ONLY if a time is stated), notes (string) }\n"
        "- medication.data: { medicationName (string), dosageAmount (number, only if stated), "
        "dosageUnit (string, e.g. mg), scheduleType ('as-needed' or 'scheduled', only if clear), "
        "timestamp (ISO8601), notes }\n"
        "- food.data: { mealType (breakfast|lunch|dinner|snack|beverage), "
        "items ([{ description (string), tags ([string]) }]), timestamp (ISO8601) }\n"
        "- sleep.data: { segments ([{ startTime (ISO8601), endTime (ISO8601) }]), "
        "qualityRating (int 1-10, only if stated), notes }\n\n"
        "STRICT RULES:\n"
        "1. NEVER invent severity, dosage, quality, medication schedule, or timestamps that were not spoken.\n"
        "2. If a required field is not stated, omit it and list its name in missingFields.\n"
        "3. Resolve relative times ('this morning', 'last night', '2pm') using the user's timezone.\n"
        "4. Put any ambiguous or uncertain interpretation into warnings.\n"
        "5. confidence is 0..1 for how sure you are about that entry.\n\n"
        "Output shape:\n"
        '{ "entries": [ { "clientEntryId": "1", "entryType": "symptom", '
        '"data": {...}, "confidence": 0.0, "missingFields": [], "warnings": [] } ] }\n\n'
        "Transcript:\n"
        f"\"\"\"{transcript}\"\"\""
    )