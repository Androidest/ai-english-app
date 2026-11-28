from app.workflow.schemas.sentence_batch import SentenceBatch
from app.workflow.schema_handlers.commons import validate_batch_uids

def validate_sentence_batch_uids(
    expected_uids: set[str],
    actual_batch: SentenceBatch,
    check_missing: bool=True,
) -> tuple[bool, str]:
    
    """Validate whether the supplied batch UIDs match the expected UIDs."""

    return validate_batch_uids(
        expected_uids=expected_uids,
        actual_uids=set(item.uid for item in actual_batch.items),
        check_missing=check_missing,
    )


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