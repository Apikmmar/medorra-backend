def promptBuilder(symptomsText, medicationsText, foodText, sleepText, timeWindow):
    PROMPT = f"""You are a health pattern analysis engine. Analyze the following health diary data from the past {timeWindow} days and identify correlations between entries.

Look for time-delayed correlations between:
- Food items and symptoms
- Medications and symptoms
- Sleep patterns and symptoms
- Food items and sleep quality

For each correlation found, provide:
- trigger: the entry type and specific identifier (e.g., food name, medication name)
- correlatedSymptom: the symptom that correlates
- averageDelay: the average time delay between trigger and symptom (e.g., "2 days", "6 hours")
- confidenceScore: a float between 0.0 and 1.0 indicating confidence
- supportingEntryIds: array of 2-10 entryId values that support this correlation
- summary: a plain-language explanation at or below 8th-grade reading level

Only include correlations with confidence above 0.6.

Return your analysis as a JSON array of insight objects. Return ONLY the JSON array, no other text.

Example format:
[
  {{
    "trigger": {{"entryType": "food", "identifier": "dairy products"}},
    "correlatedSymptom": "headache",
    "averageDelay": "2 days",
    "confidenceScore": 0.82,
    "supportingEntryIds": ["id1", "id2", "id3"],
    "summary": "You tend to get headaches about 2 days after eating dairy products."
  }}
]

--- SYMPTOM ENTRIES ---
{symptomsText}

--- MEDICATION ENTRIES ---
{medicationsText}

--- FOOD ENTRIES ---
{foodText}

--- SLEEP ENTRIES ---
{sleepText}
"""

    return PROMPT
