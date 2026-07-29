"""Whole-graph validation for the Intermediate Representation.

Implements IR Specification Section 9.2 ("Whole-Graph (IRDataset)"). These
validators operate on a fully-constructed IRDataset and its contained
entities. They do not require access to the source Document object (Section
11, Remaining Mentor Decision 7): "Validate without Document access; pass
Document only when a specific rule needs it." None of the invariants below
need it.
"""