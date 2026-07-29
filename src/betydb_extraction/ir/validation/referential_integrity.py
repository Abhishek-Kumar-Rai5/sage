"""Whole-graph referential integrity checks.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING, TypeVar

from betydb_extraction.ir.support.enums import ProvenanceLabel
from betydb_extraction.ir.validation.errors import IRValidationError

if TYPE_CHECKING:
    from betydb_extraction.ir.dataset import IRDataset
    from betydb_extraction.ir.support.extracted_field import ExtractedField

__all__ = [
    "check_denormalized_field_consistency",
    "check_global_id_uniqueness",
    "check_management_treatment_ids_resolve",
    "check_observation_dataset_containment",
    "check_single_control_per_site",
    "check_site_name_uniqueness",
    "check_species_scientific_name_uniqueness",
    "check_treatment_uniqueness_within_citation",
    "check_aggregated_over_factors_consistency",
    "validate_referential_integrity",
]

_T = TypeVar("_T")


def _duplicate_values(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _concrete_value(field: "ExtractedField[_T] | None") -> "_T | None":
    if field is None or field.provenance_label == ProvenanceLabel.UNRESOLVED:
        return None
    return field.value


def check_global_id_uniqueness(dataset: "IRDataset") -> list[IRValidationError]:
    """Invariant 1: all id values are unique within the IRDataset, per entity type."""
    errors: list[IRValidationError] = []
    entity_lists: dict[str, list] = {
        "Citation": [dataset.primary_citation],
        "Site": dataset.sites,
        "Species": dataset.species,
        "Method": dataset.methods,
        "Treatment": dataset.treatments,
        "Management": dataset.managements,
        "Observation": dataset.observations,
    }
    for entity_name, entities in entity_lists.items():
        duplicates = _duplicate_values(entity.id for entity in entities)
        if duplicates:
            errors.append(
                IRValidationError(
                    "9.2-1", f"Duplicate {entity_name} id(s): {duplicates}."
                )
            )
    return errors


def check_site_name_uniqueness(dataset: "IRDataset") -> list[IRValidationError]:
    """Invariant 2: Site.name is unique within IRDataset."""
    names = [
        value
        for site in dataset.sites
        if (value := _concrete_value(site.name)) is not None
    ]
    duplicates = _duplicate_values(names)
    if duplicates:
        return [
            IRValidationError("9.2-2", f"Duplicate Site.name value(s): {duplicates}.")
        ]
    return []


def check_species_scientific_name_uniqueness(
    dataset: "IRDataset",
) -> list[IRValidationError]:
    """Invariant 3: Species.scientific_name is unique within IRDataset."""
    names = [
        value
        for species in dataset.species
        if (value := _concrete_value(species.scientific_name)) is not None
    ]
    duplicates = _duplicate_values(names)
    if duplicates:
        return [
            IRValidationError(
                "9.2-3",
                f"Duplicate Species.scientific_name value(s): {duplicates}.",
            )
        ]
    return []


def check_treatment_uniqueness_within_citation(
    dataset: "IRDataset",
) -> list[IRValidationError]:
    """Invariant 4: Treatment.name (and id) is unique within the same citation_id."""
    errors: list[IRValidationError] = []
    by_citation: dict[str, list] = defaultdict(list)
    for treatment in dataset.treatments:
        by_citation[treatment.citation_id.target_id].append(treatment)

    for citation_id, treatments in by_citation.items():
        duplicate_ids = _duplicate_values(treatment.id for treatment in treatments)
        if duplicate_ids:
            errors.append(
                IRValidationError(
                    "9.2-4",
                    "Duplicate Treatment.id within citation_id "
                    f"{citation_id!r}: {duplicate_ids}.",
                )
            )

        names = [
            value
            for treatment in treatments
            if (value := _concrete_value(treatment.name)) is not None
        ]
        duplicate_names = _duplicate_values(names)
        if duplicate_names:
            errors.append(
                IRValidationError(
                    "9.2-4",
                    "Duplicate Treatment.name within citation_id "
                    f"{citation_id!r}: {duplicate_names}.",
                )
            )
    return errors


def check_single_control_per_site(dataset: "IRDataset") -> list[IRValidationError]:
    """Invariant 5: at most one Treatment with control_status = True per
    (citation_id, site_id) pair."""
    errors: list[IRValidationError] = []
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for treatment in dataset.treatments:
        is_control = _concrete_value(treatment.control_status)
        if is_control:
            key = (treatment.citation_id.target_id, treatment.site_id.target_id)
            counts[key] += 1

    for (citation_id, site_id), count in counts.items():
        if count > 1:
            errors.append(
                IRValidationError(
                    "9.2-5",
                    "More than one control Treatment for "
                    f"(citation_id={citation_id!r}, site_id={site_id!r}): "
                    f"{count} found.",
                )
            )
    return errors


def check_management_treatment_ids_resolve(
    dataset: "IRDataset",
) -> list[IRValidationError]:
    """Invariant 6: Management.treatment_ids, when resolved, is non-empty and
    every id resolves to an existing Treatment."""
    errors: list[IRValidationError] = []
    treatment_ids = {treatment.id for treatment in dataset.treatments}

    for management in dataset.managements:
        field = management.treatment_ids
        if field is None or field.provenance_label == ProvenanceLabel.UNRESOLVED:
            continue

        refs = field.value or []
        if not refs:
            errors.append(
                IRValidationError(
                    "9.2-6",
                    f"Management {management.id!r}.treatment_ids must be "
                    "non-empty when provenance_label is not UNRESOLVED.",
                )
            )
            continue

        unknown = [ref.target_id for ref in refs if ref.target_id not in treatment_ids]
        if unknown:
            errors.append(
                IRValidationError(
                    "9.2-6",
                    f"Management {management.id!r}.treatment_ids references "
                    f"unknown Treatment id(s): {unknown}.",
                )
            )
    return errors


def check_denormalized_field_consistency(
    dataset: "IRDataset",
) -> list[IRValidationError]:

    errors: list[IRValidationError] = []
    treatments_by_id = {treatment.id: treatment for treatment in dataset.treatments}

    for observation in dataset.observations:
        treatment = treatments_by_id.get(observation.treatment_id.target_id)
        if treatment is None:
            errors.append(
                IRValidationError(
                    "9.2-7",
                    f"Observation {observation.id!r}.treatment_id references "
                    f"unknown Treatment {observation.treatment_id.target_id!r}.",
                )
            )
            continue

        if observation.citation_id.target_id != treatment.citation_id.target_id:
            errors.append(
                IRValidationError(
                    "9.2-7",
                    f"Observation {observation.id!r}.citation_id "
                    f"({observation.citation_id.target_id!r}) does not "
                    f"match referenced Treatment {treatment.id!r}.citation_id "
                    f"({treatment.citation_id.target_id!r}).",
                )
            )

        if observation.site_id.target_id != treatment.site_id.target_id:
            errors.append(
                IRValidationError(
                    "9.2-7",
                    f"Observation {observation.id!r}.site_id "
                    f"({observation.site_id.target_id!r}) does not match "
                    f"referenced Treatment {treatment.id!r}.site_id "
                    f"({treatment.site_id.target_id!r}).",
                )
            )

    for management in dataset.managements:
        field = management.treatment_ids
        if field is None or field.provenance_label == ProvenanceLabel.UNRESOLVED:
            continue

        for ref in field.value or []:
            treatment = treatments_by_id.get(ref.target_id)
            if treatment is None:
                # Already reported by check_management_treatment_ids_resolve.
                continue
            if management.citation_id.target_id != treatment.citation_id.target_id:
                errors.append(
                    IRValidationError(
                        "9.2-7",
                        f"Management {management.id!r}.citation_id "
                        f"({management.citation_id.target_id!r}) does not "
                        f"match Treatment {treatment.id!r}.citation_id "
                        f"({treatment.citation_id.target_id!r}).",
                    )
                )
    return errors


def check_observation_dataset_containment(
    dataset: "IRDataset",
) -> list[IRValidationError]:
    """Invariant 8: Observation.dataset_id equals the enclosing
    IRDataset.dataset_id."""
    mismatched = [
        observation.id
        for observation in dataset.observations
        if observation.dataset_id != dataset.dataset_id
    ]
    if mismatched:
        return [
            IRValidationError(
                "9.2-8",
                "Observation(s) with dataset_id not equal to "
                f"IRDataset.dataset_id ({dataset.dataset_id!r}): {mismatched}.",
            )
        ]
    return []


def check_aggregated_over_factors_consistency(
    dataset: "IRDataset",
) -> list[IRValidationError]:

    del dataset  # Unused: invariant is enforced at the Observation level.
    return []


def validate_referential_integrity(dataset: "IRDataset") -> list[IRValidationError]:

    errors: list[IRValidationError] = []
    errors.extend(check_global_id_uniqueness(dataset))
    errors.extend(check_site_name_uniqueness(dataset))
    errors.extend(check_species_scientific_name_uniqueness(dataset))
    errors.extend(check_treatment_uniqueness_within_citation(dataset))
    errors.extend(check_single_control_per_site(dataset))
    errors.extend(check_management_treatment_ids_resolve(dataset))
    errors.extend(check_denormalized_field_consistency(dataset))
    errors.extend(check_observation_dataset_containment(dataset))
    errors.extend(check_aggregated_over_factors_consistency(dataset))
    return errors