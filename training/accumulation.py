from __future__ import annotations


def accumulation_window_size(batch_index: int, total_batches: int, accum: int) -> int:
    """Return the number of microbatches in the current accumulation window."""
    if accum < 1:
        raise ValueError("accum must be >= 1")
    if total_batches < 1:
        raise ValueError("total_batches must be >= 1")
    if batch_index < 0 or batch_index >= total_batches:
        raise ValueError("batch_index out of range")
    window_start = (batch_index // accum) * accum
    return min(accum, total_batches - window_start)


def is_optimizer_boundary(batch_index: int, total_batches: int, accum: int) -> bool:
    """True when gradients must be committed, including a short final window."""
    accumulation_window_size(batch_index, total_batches, accum)
    return ((batch_index + 1) % accum == 0) or (batch_index + 1 == total_batches)
