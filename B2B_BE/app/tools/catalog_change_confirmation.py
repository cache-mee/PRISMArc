from pydantic import BaseModel

from app.domain.services import (
    ProposedService,
    ProposedServiceDeletion,
    ProposedServiceEdit,
)


class ConfirmCatalogChangeArgs(BaseModel):
    """LLM-callable tool arguments for the FR-18 catalog-change confirmation checkpoint.

    Mirrors ``VerifyConflictCheckArgs``'s "nothing to correct, only to confirm"
    shape: a restated catalog change (add/edit/delete) is Ramesh's own proposal
    read back to him, not deterministic data he might correct, so there is
    nothing here beyond his explicit yes/no.
    """

    confirmed: bool


def confirm_catalog_change(
    pending: ProposedService | ProposedServiceEdit | ProposedServiceDeletion,
    args: ConfirmCatalogChangeArgs,
) -> ProposedService | ProposedServiceEdit | ProposedServiceDeletion:
    """Record Ramesh's explicit yes/no on a pending catalog-change proposal (FR-18).

    This is the in-process tool seam a future Manager Agent loop registers for
    Ramesh to act on ``present_proposed_service_change_for_confirmation``'s output
    (``app.agent.manager_agent``), immediately before any call to
    ``confirm_and_create_service`` / ``confirm_and_update_service`` /
    ``confirm_and_delete_service`` (``app.domain.services``). A single generic
    implementation is reused across all three ``Proposed*`` types — setting
    ``confirmed`` is identical for all three, so no per-type duplication is
    needed. Returns a new object via ``pending.model_copy(update=...)``; ``pending``
    itself is left unchanged, so a decline (``args.confirmed=False``) is recorded
    via the returned copy, not silently dropped.
    """
    return pending.model_copy(update={"confirmed": args.confirmed})
