"""Assistant service: retrieval-augmented answering with verified citations."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.providers.base import ProviderError
from app.providers.registry import get_provider
from app.retrieval.context import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    SYSTEM_PROMPT,
    build_sources,
    build_user_prompt,
    validate_answer,
)
from app.schemas.assistant import AssistantRequest, AssistantResponse, SourceReference
from app.schemas.search import SearchRequest
from app.services.search_service import SearchService


class AssistantService:
    def __init__(self, db: Session):
        self.db = db

    async def ask(self, request: AssistantRequest) -> AssistantResponse:
        notes: list[str] = []

        if not settings.ENABLE_AI_ASSISTANT:
            notes.append(
                "AI assistant is disabled in settings. Search still works without AI."
            )

        # 1. Retrieve evidence
        search_response = await SearchService(self.db).search(
            SearchRequest(
                query=request.question,
                mode=request.mode,
                limit=request.limit,
            )
        )
        results = search_response.results

        if not results:
            return AssistantResponse(
                answer=INSUFFICIENT_EVIDENCE_MESSAGE,
                sources=[],
                provider="none",
                model="none",
                grounded=True,
                insufficient_evidence=True,
                retrieval_mode=request.mode,
                notes=notes + ["No documents matched the question."],
            )

        sources = build_sources(results)

        # 2. Resolve provider and enforce consent for non-local providers
        try:
            provider = get_provider(request.provider)
        except ProviderError as exc:
            return self._unavailable(
                sources, request, str(exc), notes
            )

        if not provider.is_configured():
            return self._unavailable(
                sources,
                request,
                f"AI provider '{provider.name}' is not configured.",
                notes,
            )

        is_local = provider.name == "ollama"
        if not is_local and not request.consent_to_external_provider:
            return self._unavailable(
                sources,
                request,
                "This provider sends document text off-device. "
                "Explicit consent is required before using it.",
                notes,
            )

        # 3. Ask the model
        prompt = build_user_prompt(request.question, sources)
        try:
            answer = await provider.complete(SYSTEM_PROMPT, prompt)
        except ProviderError as exc:
            return self._unavailable(sources, request, str(exc), notes)

        if not answer or INSUFFICIENT_EVIDENCE_MESSAGE in answer:
            return AssistantResponse(
                answer=INSUFFICIENT_EVIDENCE_MESSAGE,
                sources=[],
                provider=provider.name,
                model=getattr(provider, "model", settings.AI_MODEL),
                grounded=True,
                insufficient_evidence=True,
                retrieval_mode=request.mode,
                notes=notes,
            )

        # 4. Validate citations
        validation = validate_answer(answer, sources)

        references = [
            SourceReference(
                index=source.index,
                chunk_id=source.chunk_id,
                document_id=source.document_id,
                document_name=source.document_name,
                page_number=source.page_number,
                heading=source.heading,
                excerpt=source.content[:400],
                score=source.score,
            )
            for source in validation["sources"]
        ]

        result_notes = list(notes)
        if validation["invalid_citations"]:
            result_notes.append(
                "Removed citations that did not match any retrieved source: "
                + ", ".join(str(n) for n in validation["invalid_citations"])
            )
        if validation["warning"]:
            result_notes.append(validation["warning"])

        return AssistantResponse(
            answer=validation["answer"],
            sources=references,
            provider=provider.name,
            model=getattr(provider, "model", settings.AI_MODEL),
            grounded=bool(references),
            insufficient_evidence=not references,
            invalid_citations=validation["invalid_citations"],
            warning=validation["warning"],
            retrieval_mode=request.mode,
            notes=result_notes,
        )

    def _unavailable(
        self,
        sources,
        request: AssistantRequest,
        reason: str,
        notes: list[str],
    ) -> AssistantResponse:
        """Return retrieval results when no AI answer can be produced."""
        references = [
            SourceReference(
                index=source.index,
                chunk_id=source.chunk_id,
                document_id=source.document_id,
                document_name=source.document_name,
                page_number=source.page_number,
                heading=source.heading,
                excerpt=source.content[:400],
                score=source.score,
            )
            for source in sources
        ]
        return AssistantResponse(
            answer=(
                "AI answering is unavailable, so here are the retrieved sources instead. "
                f"Reason: {reason}"
            ),
            sources=references,
            provider="none",
            model="none",
            grounded=False,
            insufficient_evidence=True,
            retrieval_mode=request.mode,
            notes=notes + ["Search-only fallback used."],
        )
