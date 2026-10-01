"""Provision the TON persona using the shared Onyx persona and tool models."""

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import Persona, StarterMessage, Tool, User
from onyx.db.persona import upsert_persona
from onyx.db.ton import dre, financial_domain
from onyx.db.ton.acl import assert_global
from onyx.db.ton.models import FinancialActualFact, ReviewRun
from onyx.prompts.ton.agent import TON_SYSTEM_PROMPT
from onyx.ton.agent.models import FinancialBaseContext, FinancialContext
from onyx.tools.tool_implementations.ton.ton_tool import TON_TOOL_CLASSES


def financial_context(
    session: Session, user: User, limit: int, offset: int
) -> FinancialContext:
    bases: list[FinancialBaseContext] = []
    for run in financial_domain.list_runs(session, user, limit, offset):
        review = session.get(ReviewRun, run.review_run_id)
        assert review is not None
        periods = list(
            session.scalars(
                sa.select(FinancialActualFact.calendar_period)
                .where(FinancialActualFact.run_id == run.id)
                .distinct()
                .order_by(FinancialActualFact.calendar_period)
                .limit(25)
            )
        )
        bases.append(
            FinancialBaseContext(
                normalization_run_id=run.id,
                source_id=review.source_id,
                review_run_id=review.id,
                periods=periods,
            )
        )
    structures = dre.list_structures(session, user, limit, offset)
    return FinancialContext(
        bases=bases,
        structure_version_ids=[
            dre.get_latest_version(session, user, item.id).id for item in structures
        ],
    )


def provision_agent(session: Session, user: User) -> Persona:
    assert_global(user, permission=Permission.FULL_ADMIN_PANEL_ACCESS)
    # Serialize configuration so two admin requests cannot create duplicate tools.
    session.execute(sa.text("SELECT pg_advisory_xact_lock(74661001)"))
    tools: list[Tool] = []
    for tool_class in TON_TOOL_CLASSES:
        tool = session.scalar(
            sa.select(Tool).where(Tool.in_code_tool_id == tool_class.__name__)
        )
        if tool is None:
            tool = Tool(
                name=tool_class.NAME,
                description=tool_class.DESCRIPTION,
                display_name=tool_class.DESCRIPTION,
                in_code_tool_id=tool_class.__name__,
                enabled=True,
            )
            session.add(tool)
        tools.append(tool)
    session.flush()
    existing = session.scalar(
        sa.select(Persona).where(
            Persona.name == "TON",
            Persona.builtin_persona.is_(True),
            Persona.deleted.is_(False),
        )
    )
    persona = upsert_persona(
        user=None,
        name="TON",
        description="Controladoria digital com análise financeira e evidências verificáveis.",
        starter_messages=[
            StarterMessage(
                name="Analisar fechamento",
                message="Analise o fechamento financeiro atual e me diga o que precisa da minha atenção.",
            ),
            StarterMessage(
                name="Consultar DRE", message="O que está impedindo a DRE de fechar?"
            ),
            StarterMessage(
                name="Consultar evidência",
                message="Me mostre a evidência da principal pendência.",
            ),
        ],
        system_prompt=TON_SYSTEM_PROMPT,
        task_prompt=None,
        datetime_aware=True,
        is_public=True,
        db_session=session,
        tool_ids=[tool.id for tool in tools],
        persona_id=existing.id if existing else None,
        builtin_persona=True,
        is_listed=True,
        is_featured=True,
        commit=False,
    )
    session.commit()
    return persona
