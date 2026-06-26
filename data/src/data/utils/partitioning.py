"""Utilities for handling partitioned datasets with lazy loading."""

from typing import Any, Callable, Dict, Iterator, Tuple, TypeVar

T = TypeVar('T')


def load_partition(value_or_loader: T | Callable[[], T]) -> T:
    """Load a partition value, handling both callables and direct values.
    
    When using PartitionedDataset, Kedro provides callables (loaders) that
    return the actual partition data when called. This utility handles both
    cases transparently:
    - If value is callable: call it to load the partition
    - If value is already loaded: return it as-is
    
    This enables compatibility with both PartitionedDataset (lazy loading)
    and direct object passing (unit tests, non-partitioned datasets).
    
    Args:
        value_or_loader: Either a callable that returns the value,
                        or the value itself
    
    Returns:
        The loaded value
    
    Examples:
        >>> # With a callable (PartitionedDataset)
        >>> loader = lambda: EnrichedDocument(...)
        >>> doc = load_partition(loader)
        
        >>> # With a direct value (unit tests)
        >>> doc_direct = EnrichedDocument(...)
        >>> doc = load_partition(doc_direct)
    """
    return value_or_loader() if callable(value_or_loader) else value_or_loader


def iter_loaded_partitions(
    partitions: Dict[str, T | Callable[[], T]]
) -> Iterator[Tuple[str, T]]:
    """Iterate over partitions, loading each one.
    
    Convenience iterator that yields (key, loaded_value) pairs,
    automatically handling callables vs direct values.
    
    Args:
        partitions: Dictionary of uid -> (value or loader)
    
    Yields:
        Tuples of (uid, loaded_value)
    
    Examples:
        >>> for uid, doc in iter_loaded_partitions(enriched_documents):
        ...     process(doc)
    """
    for uid, value_or_loader in partitions.items():
        yield uid, load_partition(value_or_loader)
