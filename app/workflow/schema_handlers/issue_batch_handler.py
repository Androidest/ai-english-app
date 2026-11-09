from app.workflow.schemas.issue_batch import IssueBatch
from app.workflow.schema_handlers.commons import validate_batch_uids


def validate_issue_batch_uids(
    expected_uids: set[str],
    actual_batch: IssueBatch,
    check_missing: bool=True,
) -> tuple[bool, str]:
    
    """Validate whether the supplied batch UIDs match the expected UIDs."""

    return validate_batch_uids(
        expected_uids=expected_uids,
        actual_uids=set(issue.uid for issue in actual_batch.issues),
        check_missing=check_missing,
    )


def validate_batch_reasons(
    batch: IssueBatch,
) -> tuple[bool, str]:
    
    """Basic deterministic checks for the issues description."""
    
    failures = []

    for issue in batch.issues:
        text = issue.reason.strip()

        if len(text) == 0:
            failures.append(f"- '{issue.uid}': Issue is empty.")
            continue

        if "\n" in text:
            failures.append(f"- '{issue.uid}': Issue contains multiple lines.")
            continue

    if len(failures) > 0:
        return (
            False,
            "Fix the issues description below:\n" + "\n".join(failures)
        )

    return True, ""
