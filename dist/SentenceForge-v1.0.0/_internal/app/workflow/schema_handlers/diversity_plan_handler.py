from app.workflow.schemas.diversity_plan import DiversityPlan, DiversityBucket


def validate_plan(
    plan: DiversityPlan,
    target_count: int,
) -> tuple[bool, str]:

    """
    Validate whether the plan contains dupicate categories, 
    or whether the actual planned sentence count differs from the expected target count.
    """
    
    errors = []

    # counting
    total = 0
    cat_count = {}
    for bucket in plan.buckets:
        total += bucket.count
        cat_count[bucket.category] = cat_count.get(bucket.category, 0) + 1

    if total != target_count:
        errors.append("Diversity planner returned an invalid count allocation:")
        errors.append(f"- Requested total sentence counts: {target_count}")
        errors.append(f"- Actual total sentence counts (sum of all bucket sentence counts): {total}\n")

    duplicates = [
        f"- Category '{cat}' has {count-1} duplicates." 
        for cat, count in cat_count.items() 
        if count > 1
    ]

    if duplicates:
        errors.append("Diversity planner returned duplicate categories:")
        errors.extend(duplicates)

    return len(errors) == 0, errors


def batchify_plan(
    diversity_plan: DiversityPlan, 
    batch_size:int,
) -> list[DiversityPlan]:

    """
    Turn the plan into a list of batches.
    One batch is one small plan with the same class as the original large plan. 

    The total number of sentences across all buckets in one batch must be equal to or less than the batch size.
    If a bucket spans two or more batches, it will be split.
    """

    cur_idx = 0
    cur_bucket:DiversityBucket = None # bucket in progress
    cur_batch = [] # batch in progress
    cur_batch_size = 0 # in progress batch size (sum of all bucket.count inside the batch)
    batches = []

    while cur_idx < len(diversity_plan.buckets) or cur_bucket != None:

        # get the next bucket if the current one has finished processing
        if cur_bucket == None:
            cur_bucket = diversity_plan.buckets[cur_idx].model_copy()
            cur_idx += 1

        # in_bucket is the current bucket that is going to be put in the batch
        in_bucket = None

        # Slice the current bucket if it's too big to fit into a batch.
        if cur_batch_size + cur_bucket.count > batch_size:
            # Cut a slice from the bucket to fill in the current batch
            in_bucket = cur_bucket.model_copy()
            in_bucket.count = batch_size - cur_batch_size
            # update the remaining counts of the current bucket
            cur_bucket.count -= in_bucket.count

        # No cutting needed
        else:
            in_bucket = cur_bucket
            cur_bucket = None

        # adding buckets to the current batch
        cur_batch.append(in_bucket)
        cur_batch_size += in_bucket.count

        # Save the batch when it's full or when nothing left to be process
        if (
            cur_batch_size == batch_size # the batch is full
            or 
            (cur_idx >= len(diversity_plan.buckets) and cur_bucket == None) # nothing left to be process
        ):
            batches.append(DiversityPlan(buckets=cur_batch))
            cur_batch = []
            cur_batch_size = 0

    return batches
