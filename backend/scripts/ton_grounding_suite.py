"""Ask the TON assistant the reference questions and check latency and numbers.

Each answer must finish within the latency budget, use at most the allowed
tool calls, and cite only money amounts that the tools returned or that the
persisted DRE statement (the DRE screen) shows. The closing overview lines
must also equal that statement. Exits non-zero naming each failure.

Usage (a personal access token of a TON user, created in Configurações):
    TON_PAT=onyx_pat_... python backend/scripts/ton_grounding_suite.py
    python backend/scripts/ton_grounding_suite.py --from-json answers.json

`--from-json` scores answers collected elsewhere (for example in the
browser): a list of {question, seconds, tools, answer, tool_data, statements},
where `statements` maps a DRE run id to its statement JSON.
"""

import argparse
import json
import os
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from onyx.ton.agent.grounding import numbers_in, ungrounded  # noqa: E402

QUESTIONS = (
    "Como está o fechamento de junho?",
    "Quais pendências impedem a DRE?",
    "O que mudou depois das decisões?",
    "Qual foi o resultado de abril em Mossoró-RN?",
)
LATENCY_BUDGET_SECONDS = 45.0
MAX_TOOL_CALLS = 8


def _ask(base: str, headers: dict[str, str], persona_id: int, question: str) -> dict:
    start = time.monotonic()
    tools: list[str] = []
    tool_data: list[Any] = []
    text: list[str] = []
    body = {
        "message": question,
        "chat_session_info": {"persona_id": persona_id},
        "stream": True,
    }
    with requests.post(
        f"{base}/api/chat/send-chat-message",
        json=body,
        headers=headers,
        stream=True,
        timeout=600,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            try:
                obj = json.loads(line).get("obj") or {}
            except json.JSONDecodeError:
                continue
            if obj.get("type") == "custom_tool_start":
                tools.append(obj.get("tool_name", ""))
            elif obj.get("type") == "custom_tool_delta":
                tool_data.append(obj.get("data"))
            elif obj.get("type") == "message_delta":
                text.append(obj.get("content", ""))
    return dict(
        question=question,
        seconds=round(time.monotonic() - start, 1),
        tools=tools,
        answer="".join(text),
        tool_data=tool_data,
    )


def _run_ids(tool_data: list[Any]) -> set[str]:
    ids: set[str] = set()
    for item in tool_data:
        if isinstance(item, dict) and item.get("run_id") and "linhas_dre" in item:
            ids.add(item["run_id"])
    return ids


def _statement_values(statement: dict) -> tuple[set[Decimal], dict[str, Decimal]]:
    values: set[Decimal] = set()
    by_label: dict[str, Decimal] = {}
    for line in statement.get("lines", []):
        for key in ("realizado", "realizado_ytd", "orcado", "orcado_ytd"):
            values.add(Decimal(str(line[key])))
        by_label[line["label"]] = Decimal(str(line["realizado"]))
    return values, by_label


def score(result: dict) -> list[str]:
    failures: list[str] = []
    question = result["question"]
    if result["seconds"] > LATENCY_BUDGET_SECONDS:
        failures.append(
            f"{question}: {result['seconds']} s acima de {LATENCY_BUDGET_SECONDS} s"
        )
    if len(result["tools"]) > MAX_TOOL_CALLS:
        failures.append(
            f"{question}: {len(result['tools'])} chamadas (máximo {MAX_TOOL_CALLS})"
        )
    expected = numbers_in(result["tool_data"])
    for run_id, statement in result.get("statements", {}).items():
        values, by_label = _statement_values(statement)
        expected |= values
        for item in result["tool_data"]:
            if not (isinstance(item, dict) and item.get("run_id") == run_id):
                continue
            for line in item.get("linhas_dre", []):
                screen = by_label.get(line["linha"])
                if screen is None or Decimal(line["realizado"]) != screen.quantize(
                    Decimal("0.01")
                ):
                    failures.append(
                        f"{question}: linha '{line['linha']}' {line['realizado']} difere da tela DRE ({screen})"
                    )
    failures.extend(
        f"{question}: valor sem origem nos dados persistidos: {amount}"
        for amount in ungrounded(result["answer"], expected)
    )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url", default=os.environ.get("TON_BASE_URL", "http://localhost:3000")
    )
    parser.add_argument("--persona-id", type=int, default=None)
    parser.add_argument("--from-json", type=Path)
    parser.add_argument("questions", nargs="*")
    args = parser.parse_args()

    if args.from_json:
        results = json.loads(args.from_json.read_text(encoding="utf-8"))
    else:
        token = os.environ.get("TON_PAT")
        if not token:
            print("Defina TON_PAT com um token pessoal de um usuário TON.")
            return 2
        headers = {"Authorization": f"Bearer {token}"}
        persona_id = (
            args.persona_id
            or requests.get(
                f"{args.base_url}/api/ton/agent/configuration",
                headers=headers,
                timeout=30,
            ).json()["persona_id"]
        )
        results = []
        for question in args.questions or QUESTIONS:
            result = _ask(args.base_url, headers, persona_id, question)
            result["statements"] = {
                run_id: requests.get(
                    f"{args.base_url}/api/ton/dre/calculations/{run_id}/statement",
                    headers=headers,
                    timeout=60,
                ).json()
                for run_id in _run_ids(result["tool_data"])
            }
            results.append(result)

    failures: list[str] = []
    for result in results:
        problems = score(result)
        failures.extend(problems)
        print(
            f"{'FALHOU' if problems else 'ok    '} {result['seconds']:6.1f} s "
            f"{len(result['tools'])} chamadas  {result['question']}"
        )
    for failure in failures:
        print("  -", failure)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
