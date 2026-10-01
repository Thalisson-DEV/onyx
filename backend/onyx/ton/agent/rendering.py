"""Render persisted report content without recalculation."""

from onyx.ton.agent.closing_models import PublishedClosing
from onyx.ton.agent.registry import SPECIALISTS


def render_markdown(publication: PublishedClosing) -> str:
    output = publication.output
    names = {item.key: item.name for item in SPECIALISTS}
    lines = [
        "# Pendências do fechamento",
        "",
        output.data_context,
        "",
        f"Período: {output.period:%m/%Y}. Escopo: {output.scope}.",
        f"Gerado em: {output.generated_at.isoformat()}",
        f"Resultado: {publication.status}.",
        "",
        "## Resumo executivo",
        "",
    ]
    for label in ("RESULTADO", "PROBLEMA", "IMPACTO", "CAUSA / HIPÓTESE", "AÇÃO"):
        value = output.executive_brief[label]
        lines.extend([f"**{label}**: {value}", ""])
    lines.extend(["## Fontes", ""])
    for source in output.sources:
        lines.extend(
            [
                f"- {source['name']}: {source['status']}. Última importação concluída: {source.get('last_success_at') or 'Sem registro'}. Aquisição: {source['acquisition']}. Integração direta: {source['direct_integration']}."
            ]
        )
    lines.extend(["", "## Especialistas", ""])
    for specialist in output.specialists:
        lines.extend(
            [
                f"### {names[specialist.key]} — {specialist.status}",
                "",
                specialist.reason,
                "",
            ]
        )
        lines.extend(
            f"- {value}" for value in specialist.actions + specialist.limitations
        )
        lines.append("")
    lines.extend(["## Bloqueios da DRE", ""])
    lines.extend(f"- {label}: {count}" for label, count in output.blockers.items())
    if not output.blockers:
        lines.append(
            f"DRE: {output.dre_status}. Consulte o resultado persistido antes de apresentar valores."
        )
    lines.extend(["", "## Achados e evidências", "", output.findings_scope, ""])
    for finding in output.findings:
        lines.extend(
            [
                f"- {finding['title']} ({finding['id']})",
                f"  - Estado: {finding['status']}",
            ]
        )
        lines.extend(
            f"  - Evidência: fonte {evidence.get('source_snapshot_id')}; planilha {evidence.get('sheet_name')}; linha {evidence.get('row_number')}; confiança {evidence['confidence_level']}."
            for evidence in finding["evidence"]
        )
        lines.extend(
            f"  - Recomendação: {action}" for action in finding["recommendations"]
        )
    if not output.findings:
        lines.append(
            "Nenhum achado retornado nesta consulta. Isso não constitui aprovação da base."
        )
    if output.findings_may_have_more:
        lines.append(
            "Há possivelmente mais achados. Consulte a próxima página no espaço de revisão financeira."
        )
    lines.extend(["", "## Execução", ""])
    lines.extend(
        f"- {item['specialist']} / {item['code']}: {item['status']}. {item.get('reason') or ''}"
        for item in publication.steps
    )
    lines.extend(
        [
            "",
            f"Execução: {publication.run_id}",
            f"Revisão imutável: {publication.revision_id}",
            "",
        ]
    )
    return "\n".join(lines)
