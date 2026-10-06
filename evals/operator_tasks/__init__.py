"""Product-oriented public operator tasks; not an intelligence or promotion benchmark."""

from .corpus import CORPUS_DIGEST, TASKS, VERSION, get_task
from .evaluator import Citation, Product, Score, decode_product, score_product
from .runner import (
    Binding,
    ExecutionRequest,
    ExecutionResult,
    History,
    Measurement,
    OperatorTaskRunner,
    Registration,
)

__all__ = [
    "Binding",
    "CORPUS_DIGEST",
    "Citation",
    "ExecutionRequest",
    "ExecutionResult",
    "History",
    "Measurement",
    "OperatorTaskRunner",
    "Product",
    "Registration",
    "Score",
    "TASKS",
    "VERSION",
    "decode_product",
    "get_task",
    "score_product",
]
