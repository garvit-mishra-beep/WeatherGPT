"""Decisions API Router (/api/v1/decisions).

Provides direct deterministic decision-intelligence endpoints for Vayubodhak (USP Phase 1).
Produces canonical NirnayCards and verifiable EvidenceBundles without calling any LLM.
"""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.decision.engine import DeterministicDecisionEngine
from app.decision.evidence_builder import EvidenceBundleBuilder
from app.decision.models import DecisionRequest, NirnayCard
from app.dependencies.providers import (
    get_decision_engine,
    get_decision_explanation_bridge,
    get_evidence_bundle_builder,
    get_personalization_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/decisions", tags=["Vayubodhak Decision Intelligence (Nirnay)"])


@router.post(
    "",
    response_model=NirnayCard,
    status_code=status.HTTP_200_OK,
    summary="Evaluate deterministic operational decision (NirnayCard)",
    description=(
        "Transforms verified meteorological evidence into a deterministic operational decision card. "
        "Evaluates safety constraints (such as chemical spray suitability and agricultural thresholds) "
        "without LLM hallucination, emitting an audit-grade NirnayCard and EvidenceLedger."
    ),
)
async def evaluate_operational_decision(
    request: DecisionRequest,
    builder: EvidenceBundleBuilder = Depends(get_evidence_bundle_builder),
    engine: DeterministicDecisionEngine = Depends(get_decision_engine),
    bridge: Optional[Any] = Depends(get_decision_explanation_bridge),
    personalization_service: Optional[Any] = Depends(get_personalization_service),
) -> NirnayCard:
    """Evaluates an operational question against live meteorological evidence deterministically."""
    logger.info("DecisionsAPI: Evaluating query '%s' for location '%s'", request.question, request.location)
    try:
        # 1. Obtain verified EvidenceBundle (from pre-built fixture or live builder)
        if request.custom_bundle is not None:
            evidence_bundle = request.custom_bundle
        elif request.location is not None:
            evidence_bundle = await builder.build_bundle(
                location_query=request.location,
                requested_time=request.requested_time,
                domain=request.domain,
                context=request.context,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'location' or 'custom_bundle' must be provided.",
            )

        # 2. Execute deterministic decision evaluation
        nirnay_card = engine.evaluate_decision(
            evidence=evidence_bundle,
            question=request.question,
            domain=request.domain,
            context=request.context,
        )

        # 3. Optional: Evidence-grounded natural-language explanation bridge (Phase 4A)
        if request.include_explanation and bridge is not None:
            lang = "en"
            if request.context and isinstance(request.context, dict):
                lang = request.context.get("language", "en")
            nirnay_card = await bridge.explain_decision(nirnay_card, language=lang)

        # 4. Durable Decision History Recording (Phase 10)
        if personalization_service is not None and nirnay_card.ledger is not None:
            user_id = (request.context.get("user_id") if request.context and isinstance(request.context, dict) else None) or "default_user"
            plot_id = request.context.get("plot_id") if request.context and isinstance(request.context, dict) else None
            try:
                sources_data = [s if isinstance(s, dict) else s.model_dump() for s in nirnay_card.ledger.sources]
                loc_dict = evidence_bundle.location.model_dump() if hasattr(evidence_bundle.location, "model_dump") else {}
                aw_dict = nirnay_card.action_window.model_dump() if hasattr(nirnay_card.action_window, "model_dump") else nirnay_card.action_window
                await personalization_service.record_decision_history(
                    decision_id=nirnay_card.ledger.decision_id,
                    user_id=user_id,
                    plot_id=plot_id,
                    question=request.question,
                    verdict=nirnay_card.verdict,
                    severity=nirnay_card.severity,
                    recommended_action=nirnay_card.recommended_action,
                    location=loc_dict,
                    operation=request.context.get("operation") if request.context and isinstance(request.context, dict) else None,
                    evidence_snapshot=nirnay_card.evidence,
                    uncertainty=nirnay_card.uncertainty,
                    provenance={"sources": sources_data},
                    action_window=aw_dict,
                )
            except Exception as hist_err:
                logger.warning("DecisionsAPI: Failed recording decision history: %s", hist_err)

        return nirnay_card
    except Exception as exc:
        logger.exception("DecisionsAPI: Evaluation failed for query '%s': %s", request.question, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deterministic decision evaluation failed: {str(exc)}",
        )
