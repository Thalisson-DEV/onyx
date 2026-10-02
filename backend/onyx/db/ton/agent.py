"""Provision the TON persona using the shared Onyx persona and tool models."""

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import Persona, StarterMessage, Tool, User
from onyx.db.persona import upsert_persona
from onyx.db.ton import dre, financial_domain, sources
from onyx.db.ton.acl import (
    assert_global,
    business_unit_visible_clause,
    is_ton_administrator,
)
from onyx.db.ton.models import (
    BusinessUnit,
    DreCalculationRun,
    FinancialActualFact,
    ReviewRun,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.prompts.ton.agent import TON_SYSTEM_PROMPT
from onyx.ton.agent.models import (
    FinancialBaseContext,
    FinancialContext,
    StoredDreContext,
    ToolQuery,
)
from onyx.ton.agent.policy import SYNTHETIC_DATA_NOTICE, uses_synthetic_demo_data
from onyx.tools.tool_implementations.python.python_tool import PythonTool
from onyx.tools.tool_implementations.ton.ton_tool import (
    TON_TOOL_CLASSES,
    TON_TOOL_DISPLAY_NAMES,
)


def finance_summary(
    session: Session, user: User, query: ToolQuery
) -> financial_domain.ReadinessView:
    if query.normalization_run_id is None or query.period is None:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Informe normalization_run_id e period"
        )
    if query.unit_id is None and not is_ton_administrator(user):
        raise OnyxError(OnyxErrorCode.ADMIN_ONLY, "Selecione uma unidade autorizada")
    if (
        query.unit_id is not None
        and session.scalar(
            sa.select(BusinessUnit.id).where(
                BusinessUnit.id == query.unit_id, business_unit_visible_clause(user)
            )
        )
        is None
    ):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Unidade indisponível")
    return financial_domain.readiness(
        session, user, query.normalization_run_id, query.period, query.unit_id
    )


def financial_context(
    session: Session, user: User, limit: int, offset: int
) -> FinancialContext:
    bases: list[FinancialBaseContext] = []
    for run in financial_domain.list_runs(session, user, limit, offset):
        review = session.get(ReviewRun, run.review_run_id)
        assert review is not None
        source = sources.get_source(session, user, review.source_id)
        stored_results: list[StoredDreContext] = []
        calculations = session.scalars(
            sa.select(DreCalculationRun)
            .where(DreCalculationRun.normalization_run_id == run.id)
            .order_by(DreCalculationRun.finished_at.desc(), DreCalculationRun.id)
            .limit(10)
        )
        for calculation in calculations:
            try:
                view = dre.get_calculation(session, user, calculation.id)
            except OnyxError as error:
                if error.error_code in (
                    OnyxErrorCode.ADMIN_ONLY,
                    OnyxErrorCode.NOT_FOUND,
                    OnyxErrorCode.INSUFFICIENT_PERMISSIONS,
                ):
                    continue
                raise
            stored_results.append(
                StoredDreContext(
                    run_id=view.id,
                    period=view.scope.period,
                    unit_id=view.scope.unit_id,
                    structure_version_id=view.scope.structure_version_id,
                    status=view.status,
                )
            )
        periods = list(
            session.scalars(
                sa.select(FinancialActualFact.calendar_period)
                .where(FinancialActualFact.run_id == run.id)
                .distinct()
                .order_by(FinancialActualFact.calendar_period.desc())
                .limit(25)
            )
        )
        bases.append(
            FinancialBaseContext(
                normalization_run_id=run.id,
                source_id=review.source_id,
                review_run_id=review.id,
                periods=periods,
                source_name=source.display_name,
                stored_dre_results=stored_results,
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
                display_name=TON_TOOL_DISPLAY_NAMES[tool_class.NAME],
                in_code_tool_id=tool_class.__name__,
                enabled=True,
            )
            session.add(tool)
        else:
            tool.display_name = TON_TOOL_DISPLAY_NAMES[tool_class.NAME]
        tools.append(tool)
    # Code Interpreter for exploratory analysis, only when this deployment can
    # run it; the prompt bounds what its results may claim.
    python = session.scalar(
        sa.select(Tool).where(
            Tool.in_code_tool_id == PythonTool.__name__, Tool.enabled.is_(True)
        )
    )
    if python is not None and PythonTool.is_available(session):
        tools.append(python)
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
        system_prompt=(
            TON_SYSTEM_PROMPT
            + "\n"
            + SYNTHETIC_DATA_NOTICE
            + "\nInforme esse aviso no início de toda análise financeira. Chame resultados de 'resultados persistidos de demonstração'."
        )
        if uses_synthetic_demo_data()
        else TON_SYSTEM_PROMPT,
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


def configured_agent_id(session: Session, user: User) -> int | None:
    assert_global(user, permission=Permission.READ_TON_SOURCES)
    return session.scalar(
        sa.select(Persona.id)
        .where(
            Persona.name == "TON",
            Persona.builtin_persona.is_(True),
            Persona.deleted.is_(False),
            Persona.is_public.is_(True),
        )
        .limit(1)
    )
