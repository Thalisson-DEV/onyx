"""Explicit deployment label; never creates or infers synthetic records."""

import os


def uses_synthetic_demo_data() -> bool:
    return os.environ.get("TON_DEMO_SYNTHETIC_DATA", "false").lower() == "true"


SYNTHETIC_DATA_NOTICE = (
    "Dados sintéticos de demonstração. Não representam resultados reais do cliente."
)
