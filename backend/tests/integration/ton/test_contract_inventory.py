from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


BACKEND_CONTRACTS = {
    "auth": ("backend/onyx/server/auth_check.py", ("/me",)),
    "chat": (
        "backend/onyx/server/query_and_chat/chat_backend.py",
        ('prefix="/chat"', '"/send-chat-message"'),
    ),
    "projects": (
        "backend/onyx/server/features/projects/api.py",
        ('prefix="/user/projects"', '"/file/upload"'),
    ),
    "personas": (
        "backend/onyx/server/features/persona/api.py",
        ("router = APIRouter",),
    ),
    "search": (
        "backend/onyx/server/features/search/api.py",
        ("router = APIRouter",),
    ),
}


def test_preserved_backend_contract_sources_exist() -> None:
    for contract_name, (relative_path, expected_fragments) in BACKEND_CONTRACTS.items():
        source_path = REPOSITORY_ROOT / relative_path
        assert source_path.is_file(), f"Missing {contract_name} source: {relative_path}"
        content = source_path.read_text(encoding="utf-8")
        for expected_fragment in expected_fragments:
            assert expected_fragment in content, (
                f"Missing {contract_name} contract {expected_fragment!r}"
            )


def test_cross_client_contract_sources_exist() -> None:
    expected_paths = (
        "mobile/src/api/chat/sessions.ts",
        "mobile/src/api/chat/stream.ts",
        "desktop/src-tauri/tauri.conf.json",
        "widget/src/services/api-service.ts",
        "extensions/chrome/src/utils/content.js",
    )

    for relative_path in expected_paths:
        assert (REPOSITORY_ROOT / relative_path).is_file(), relative_path
