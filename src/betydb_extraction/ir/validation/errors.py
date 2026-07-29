"""Validation error types for whole-graph IR invariants.

Implements IR Specification Section 9.2 ("Whole-Graph (IRDataset)").
"""

from __future__ import annotations

__all__ = ["IRDatasetValidationError", "IRValidationError"]


class IRValidationError(ValueError):

    def __init__(self, invariant: str, message: str) -> None:
        self.invariant = invariant
        self.message = message
        super().__init__(f"[{invariant}] {message}")


class IRDatasetValidationError(ValueError):

    def __init__(self, errors: list[IRValidationError]) -> None:
        self.errors = errors
        joined = "\n".join(str(error) for error in errors)
        super().__init__(
            f"IRDataset failed {len(errors)} whole-graph validation "
            f"invariant(s) (IR Spec Section 9.2):\n{joined}"
        )