import re

def validate_batch_uids(
    expected_uids: set[str],
    actual_uids: set[str],
    check_missing: bool=True,
) -> tuple[bool, str]:
    
    """Validate whether the supplied actual UIDs match with the expected ones."""

    if actual_uids != expected_uids:
        # error msg
        error = []

        # ---- counting duplicates -----
        id_count = {}
        for id in actual_uids:
            id_count[id] = id_count.get(id, 0) + 1
    
        duplicates = [
            f"- '{id}': has {count-1} duplicates." 
            for id, count in id_count.items() 
            if count > 1
        ]
            
        if duplicates:
            error.append(f"Duplicate UIDs:")
            error.extend(duplicates)
            error.append("\n")
        
        # ---- extra ids ----
        extra = sorted(actual_uids - expected_uids)
        if extra:
            error.append(f"Unexpected extra UIDs:")
            error.extend([ f'- "{id}"' for id in extra ])
            error.append("\n")

        # ---- missing ids ----
        missing = sorted(expected_uids - actual_uids)
        if missing and check_missing:
            error.append(f"Missing UIDs:")
            error.extend([ f'- "{id}"' for id in missing ])
            error.append("\n")

        if error:
            return False, "[UID mismatch] Structured-output alignment failure!" + '\n'.join(error)

    return True, ""

def normalize_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text