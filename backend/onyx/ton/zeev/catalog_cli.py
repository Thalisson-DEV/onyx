"""Print a safe Zeev source catalog summary: python -m onyx.ton.zeev.catalog_cli."""

from collections import Counter

from onyx.ton.zeev.catalog import ZeevCatalogService
from onyx.ton.zeev.client import ZeevClient, ZeevConfig, ZeevError
from onyx.ton.zeev.models import ZeevSchemaState


def main() -> int:
    config = ZeevConfig.from_env()
    if not config.enabled or not (
        config.token or (config.username and config.password)
    ):
        print("Zeev catalog: DISABLED_OR_UNCONFIGURED")
        return 2
    calls: Counter[tuple[str, str]] = Counter()
    statuses: Counter[int] = Counter()
    with ZeevClient(
        config,
        audit_call=lambda method, path: calls.update([(method, path)]),
        audit_status=lambda _method, _path, status: statuses.update([status]),
    ) as client:
        try:
            catalog = ZeevCatalogService(client).discover()
        except ZeevError as exc:
            print(f"Zeev catalog: {type(exc).__name__}")
            return 1

    print("Zeev Source Catalog")
    print(f"Flows discovered: {len(catalog.flows)}")
    print(f"Startable flows: {sum(flow.startable for flow in catalog.flows)}")
    print(f"Editable flows: {sum(flow.editable for flow in catalog.flows)}")
    print(
        "Schemas readable: "
        + str(
            sum(
                flow.schema_state is ZeevSchemaState.AVAILABLE for flow in catalog.flows
            )
        )
    )
    print(f"Fields cataloged: {catalog.field_count}")
    print(
        "Task designs readable: "
        + str(
            sum(
                flow.design_state is ZeevSchemaState.AVAILABLE for flow in catalog.flows
            )
        )
    )
    print(f"Design elements cataloged: {catalog.design_element_count}")
    print(f"Instances structurally sampled: {catalog.instance_sample_count}")
    print(f"Tasks structurally sampled: {catalog.task_sample_count}")
    print(f"Attachments: {catalog.attachment_read.value}")
    print("Candidate areas:")
    for area, count in sorted(
        Counter(item.area for item in catalog.candidates).items()
    ):
        print(f"  {area}: {count}")
    print("Warnings:")
    for warning in catalog.warnings:
        print(f"  {warning.resource} {warning.external_id or '-'}: {warning.state}")
    if not catalog.warnings:
        print("  none")
    print("Network audit:")
    for (method, path), count in sorted(calls.items()):
        print(f"  {method} {path}: {count}")
    print(f"Rate-limit responses: {statuses[429]}")
    mutation_calls = sum(
        count
        for (method, path), count in calls.items()
        if method in {"PUT", "PATCH", "DELETE"}
        or (
            method == "POST"
            and path not in {"/api/2/tokens", "/api/2/instances/report"}
        )
    )
    print(f"Mutation calls: {mutation_calls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
