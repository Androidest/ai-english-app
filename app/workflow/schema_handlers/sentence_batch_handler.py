from app.workflow.schemas.sentence_batch import SentenceBatch


def validate_batch_ids(
    expected_batch_ids: set[str],
    actual_batch: SentenceBatch,
    check_missing: bool=True,
) -> tuple[bool, str]:
    
    """Validate that the LLM returned exactly the requested unique IDs."""

    actual_ids = set([item.uid for item in actual_batch.items])

    if actual_ids != expected_batch_ids:
        # error msg
        error = ["# Structured-output alignment failure"]

        # ---- counting duplicates -----
        id_count = {}
        for id in actual_ids:
            id_count[id] = id_count.get(id, 0) + 1
    
        duplicates = [
            f"- '{id}': has {count-1} duplicates." 
            for id, count in id_count.items() 
            if count > 1
        ]
            
        if duplicates != "":
            error.append(f"[Duplicate UID]")
            error.extend(duplicates)
            error.append("\n")

        error.append(f"[UID mismatch]")

        # ---- check extra ids ----
        extra = sorted(actual_ids - expected_batch_ids)
        error.append(f"- Unexpected extra ids: {extra}")

        # ---- check missing ids ----
        if check_missing:
            missing = sorted(expected_batch_ids - actual_ids)
            error.append(f"- Missing ids: {missing}")

        return False, '\n'.join(error)

    return True, ""


def validate_batch_sentence(
    batch: SentenceBatch,
    max_len: int,
    prompt_max_len: int,
) -> tuple[bool, str]:
    
    """Basic deterministic checks for the generated sentences."""
    
    failures = []

    for item in batch.items:
        text = item.val.strip()

        if len(text) == 0:
            failures.append(f"- '{item.uid}': Sentence is empty.")
            continue

        if len(text) > max_len:
            failures.append(f"- '{item.uid}': Sentence exceeds maximun length with ({len(text)}). Expected maximun length is ({prompt_max_len}). Try make it shorter.")
            continue

        if "\n" in text:
            failures.append(f"- '{item.uid}': Sentence contains multiple lines.")
            continue

    if len(failures) > 0:
        return (
            False,
            "Fix the problematic sentences below with the following UIDs according to their problem description:\n" + "\n".join(failures)
        )

    return True, ""


def merge_batch(
    base: SentenceBatch, 
    updates: SentenceBatch
) -> SentenceBatch:

    """
    Merge `updates` into `base` by uid, with `updates` taking precedence.
    Returns a new SentenceBatch; neither input is mutated.
    """
    
    merged = base.model_copy()

    if not updates.items:
        return merged

    update_dict = {item.uid: item.val for item in updates.items}

    for item in merged.items:
        if item.uid in update_dict:
            # print(f"Merge: {item.val} -> {update_dict[item.uid]}")
            item.val = update_dict[item.uid]

    return merged


def extract_uid_sentence_map(batches: list[SentenceBatch]) -> dict[str, str]:

    """
    Build uid -> sentence text mapping from multiple SentenceBatch instances.

    Args:
        batches: List of SentenceBatch to flatten and index.
    Returns:
        Dictionary mapping item.uid to item.val (sentence text).
    Note: Duplicate uids are overwritten by later batches.
    """

    sentence_dict = {}
    for batch in batches:
        for item in batch.items:
            sentence_dict[item.uid] = item.val
    return sentence_dict