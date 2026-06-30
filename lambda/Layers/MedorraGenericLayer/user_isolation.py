def enforceUserIsolation(userId, entries):
    filtered = [entry for entry in entries if entry.get("userId") == userId]

    if len(filtered) != len(entries):
        raise Exception(f"Data isolation violation detected: {len(entries) - len(filtered)} entries did not belong to user {userId}")

    return filtered
