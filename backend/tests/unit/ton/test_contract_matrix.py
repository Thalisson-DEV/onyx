from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


PRESERVED_CONTRACTS = {
    "web chat request": (
        "backend/onyx/server/query_and_chat/models.py",
        ("class SendMessageRequest", "class MessageOrigin", "additional_context"),
    ),
    "web chat client": (
        "web/src/app/app/services/lib.tsx",
        ("MessageOrigin", "additionalContext", "/api/chat/send-chat-message"),
    ),
    "mobile bearer authentication": (
        "backend/onyx/server/auth/mobile.py",
        ("/auth/mobile/login", "/auth/mobile/refresh"),
    ),
    "mobile chat": (
        "mobile/src/api/chat/stream.ts",
        ("/chat/send-chat-message",),
    ),
    "projects and files": (
        "backend/onyx/server/features/projects/api.py",
        ('prefix="/user/projects"', '"/file/upload"'),
    ),
    "widget chat": (
        "widget/src/services/api-service.ts",
        ("/chat/send-chat-message",),
    ),
}


def test_preserved_shared_contracts_remain_present() -> None:
    for relative_path, expected_fragments in PRESERVED_CONTRACTS.values():
        content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        for expected_fragment in expected_fragments:
            assert expected_fragment in content, (
                f"Missing {expected_fragment!r} from {relative_path}"
            )


def test_ton_domain_models_are_not_present() -> None:
    models = (REPOSITORY_ROOT / "backend/onyx/db/models.py").read_text(encoding="utf-8")
    for model_name in ("Finding", "Occurrence", "Rule", "RuleVersion", "AnalysisRun"):
        assert f"class {model_name}(" not in models


def test_vale_norte_report_remains_candidate_evidence() -> None:
    report = (
        REPOSITORY_ROOT
        / "plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt"
    )
    decision_log = (REPOSITORY_ROOT / "plans/ton/decision-log.md").read_text(
        encoding="utf-8"
    )

    assert report.is_file()
    assert "domain-evidence input, not an executable rule catalog" in decision_log
    assert "underlying workbook, DRE, contracts, bank extracts" in decision_log
