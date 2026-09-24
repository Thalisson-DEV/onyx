"""Small, redacted live discovery for the Zeev source adapter."""

from datetime import datetime, timedelta, timezone

from onyx.ton.zeev.client import ZeevClient, ZeevConfig, ZeevError
from onyx.ton.zeev.models import ZeevInstanceQuery


def main() -> int:
    config = ZeevConfig.from_env()
    if not config.enabled:
        print("Zeev integration: DISABLED")
        return 2
    if not (config.token or (config.username and config.password)):
        print("Zeev integration: UNCONFIGURED")
        return 2

    print("Zeev read-only policy: ACTIVE")

    def audit_call(method: str, path: str) -> None:
        print(f"Call: {method} {path}")

    rate_headers: set[str] = set()

    def audit_rate_headers(names: tuple[str, ...]) -> None:
        rate_headers.update(names)

    with ZeevClient(
        config, audit_call=audit_call, audit_rate_headers=audit_rate_headers
    ) as client:
        try:
            client.authenticate()
            health = client.health_check()
            print(f"Health: {health.state.value}")
            if health.state.value != "AVAILABLE":
                return 1
            flows = client.list_flows()
            print(f"Startable flows: {len(flows)}")
            for flow in flows[:3]:
                print(f"Flow sample: {flow.name}")
            try:
                editable_flows = client.list_editable_flows()
                print(f"Editable flows: {len(editable_flows)}")
            except ZeevError as exc:
                print(f"Editable flows: {type(exc).__name__}")
            services = client.list_services()
            print(f"Startable services: {len(services)}")
            for flow in flows[:2]:
                try:
                    fields = client.get_flow_form_fields(flow.external_id)
                    print(f"Form flow {flow.external_id}: {len(fields)} fields")
                except ZeevError as exc:
                    print(f"Form flow {flow.external_id}: {type(exc).__name__}")
            now = datetime.now(timezone.utc)
            instances = client.query_instances(
                ZeevInstanceQuery(
                    start=now - timedelta(days=1),
                    end=now,
                    page_size=5,
                    max_pages=2,
                    max_records=10,
                )
            )
            print(f"Recent instance sample: {len(instances)}")
            post_instances = client.query_instances(
                ZeevInstanceQuery(
                    start=now - timedelta(days=1),
                    end=now,
                    page_size=2,
                    max_pages=1,
                    max_records=2,
                ),
                use_post=True,
            )
            print(f"Read-only POST instance sample: {len(post_instances)}")
            if instances:
                instance = client.get_instance(instances[0].external_id)
                print(f"Sample instance tasks: {len(instance.tasks)}")
                if instance.tasks:
                    print(
                        "Task fields: "
                        + ", ".join(sorted(instance.tasks[0].source_metadata))
                    )
            assignments = client.list_my_assignments(page_size=5)
            print(f"Pending assignment sample: {len(assignments)}")
        except ZeevError as exc:
            print(f"Zeev discovery: {type(exc).__name__}")
            return 1
    print("Mutation calls: 0")
    print("Rate-limit header names: " + (", ".join(sorted(rate_headers)) or "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
