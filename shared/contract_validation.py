"""Small sovereign validation helpers for canonical runtime contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass

from shared.schemas import CanonicalSchema


@dataclass(frozen=True)
class ContractValidationResult:
    """Validation status for a dataclass backed canonical contract."""

    schema_name: str
    contract_name: str
    status: str
    errors: list[str]
    retry_applied: bool = False


@dataclass(frozen=True)
class OutputValidationResult:
    """Validation status for synthesized runtime output."""

    status: str
    errors: list[str]
    retry_applied: bool = False


def validate_contract_instance(
    contract: object,
    *,
    schema: CanonicalSchema,
) -> ContractValidationResult:
    """Validate required canonical fields on a dataclass instance."""

    if not is_dataclass(contract):
        raise TypeError("canonical contract validation requires a dataclass instance")

    payload = asdict(contract)
    errors = [
        f"missing_required_field:{field_name}"
        for field_name in schema.required_fields
        if _is_missing(payload.get(field_name))
    ]
    return ContractValidationResult(
        schema_name=schema.name,
        contract_name=schema.contract_name,
        status="invalid" if errors else "coherent",
        errors=errors,
    )


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False
