"""AI reading of a note or boleto the deterministic readers could not read:
an NFS-e PDF in a city hall's own layout, a scanned PDF or a photo.

The model only transcribes what is printed. Every value is validated here
(CNPJ and access-key check digits, the boleto line verifiers, dates and
amounts) and anything that fails is dropped. The result is marked as read
by AI, so the screen asks the person to confirm it and a mismatch with the
title never blocks the release on its own. A boleto line that passes its
check digits is the one exception: the amount and due date then come from
the verified code, not from the model.
"""

import base64
import datetime
import io
import json
import re
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from onyx.llm.interfaces import LLM
from onyx.llm.models import (
    ContentPart,
    ImageContentPart,
    ImageUrlDetail,
    SystemMessage,
    TextContentPart,
    UserMessage,
)
from onyx.llm.utils import llm_response_to_string
from onyx.ton.payables.documents import (
    DocumentReading,
    Installment,
    brl_amount,
    read_bank_line,
    reading_from_key,
)
from onyx.ton.payables.identifiers import access_key, digits, tax_id
from onyx.utils.logger import setup_logger

logger = setup_logger()

LLM_TIMEOUT_SECONDS = 60
# Enough text for a two-page NFS-e; the rest is usually legal boilerplate.
MAX_TEXT_CHARS = 12000
# Long side of a photo sent to the model: legible digits, small payload.
MAX_IMAGE_SIDE = 2000
MAX_IMAGES = 2

_DOCUMENT_TYPES = {"NFE": "NF", "NFSE": "NFSE", "FATURA": "FATURA", "RECIBO": "RECIBO"}
_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

SYSTEM_PROMPT = """Você transcreve documentos fiscais brasileiros para o contas a pagar.
Leia o documento (nota fiscal, NFS-e, DANFE, fatura, recibo ou boleto) e responda SOMENTE um objeto JSON, sem texto antes ou depois:
{
  "tipo": "NOTA" | "BOLETO" | "OUTRO",
  "modelo": "NFE" | "NFSE" | "FATURA" | "RECIBO" | null,
  "cnpj_emitente": "CNPJ ou CPF de quem emitiu a nota ou de quem recebe o boleto (beneficiário)" | null,
  "nome_emitente": string | null,
  "numero": "número da nota" | null,
  "data_emissao": "AAAA-MM-DD" | null,
  "valor_total": "valor total da nota ou valor do boleto, ex.: 1234.56" | null,
  "chave_acesso": "os 44 dígitos da chave de acesso" | null,
  "linha_digitavel": "os 47 ou 48 dígitos da linha digitável do boleto" | null,
  "vencimento": "AAAA-MM-DD" | null,
  "parcelas": [{"numero": 1, "vencimento": "AAAA-MM-DD", "valor": "1234.56"}]
}
Regras:
- Copie exatamente o que está impresso. Nunca calcule, complete ou adivinhe.
- Campo ilegível, cortado ou ausente: null (ou [] em parcelas).
- O emitente é quem presta o serviço ou vende, nunca o tomador ou destinatário (a Vale Norte).
- Valores com ponto decimal e sem separador de milhar."""


def _image_url(data: bytes) -> str | None:
    """The photo upright, at most MAX_IMAGE_SIDE, as a JPEG data URL."""
    from PIL import Image, ImageOps

    try:
        with Image.open(io.BytesIO(data)) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
    except Exception:  # noqa: BLE001 — an unreadable photo is left for a person
        logger.info("TON payables: image could not be prepared for reading")
        return None
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _date(value: Any) -> datetime.date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None
    return parsed if 2000 <= parsed.year <= 2100 else None


def _amount(value: Any) -> Decimal | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = f"{value:.2f}"
    return brl_amount(value) if isinstance(value, str) else None


def _text(value: Any, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())[:limit]
    return cleaned or None


def _number(value: Any) -> str | None:
    if isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    text = _text(value, 40)
    if not text or not any(char.isdigit() for char in text):
        return None
    return text


def _bank_line(value: Any) -> DocumentReading:
    """The boleto line typed the way ``read_bank_line`` validates it."""
    number = digits(value) if isinstance(value, str) else ""
    if len(number) == 47:
        line = (
            f"{number[0:5]}.{number[5:10]} {number[10:15]}.{number[15:21]} "
            f"{number[21:26]}.{number[26:32]} {number[32]} {number[33:]}"
        )
    elif len(number) == 48 and number[0] == "8":
        line = " ".join(number[i : i + 12] for i in range(0, 48, 12))
        line = " ".join(f"{block[:11]}-{block[11]}" for block in line.split())
    else:
        return DocumentReading()
    return read_bank_line(line)


def _installments(value: Any) -> tuple[Installment, ...]:
    if not isinstance(value, list):
        return ()
    found: list[Installment] = []
    for index, item in enumerate(value[:120], start=1):
        if not isinstance(item, dict):
            continue
        due = _date(item.get("vencimento"))
        amount = _amount(item.get("valor"))
        if due is None or amount is None:
            continue
        raw = item.get("numero")
        number = raw if isinstance(raw, int) and 0 < raw <= 120 else index
        found.append(Installment(number=number, due_date=due, amount=amount))
    return tuple(sorted(found, key=lambda item: item.due_date))


def parse_answer(answer: str) -> DocumentReading:
    """The model's JSON as a validated reading; empty when nothing holds."""
    match = _JSON_OBJECT.search(answer or "")
    if not match:
        return DocumentReading()
    try:
        data = json.loads(match.group())
    except ValueError:
        return DocumentReading()
    if not isinstance(data, dict):
        return DocumentReading()
    issuer = (
        tax_id(data["cnpj_emitente"])
        if isinstance(data.get("cnpj_emitente"), str)
        else None
    )
    name = _text(data.get("nome_emitente"), 300)

    boleto = _bank_line(data.get("linha_digitavel"))
    if boleto.is_read:
        return DocumentReading(
            kind="BOLETO",
            amount=boleto.amount,
            due_date=boleto.due_date,
            tax_id=issuer,
            issuer_name=name,
            source="FILE",
        )
    if data.get("tipo") == "BOLETO":
        amount = _amount(data.get("valor_total"))
        due = _date(data.get("vencimento"))
        if amount is None and due is None:
            return DocumentReading()
        return DocumentReading(
            kind="BOLETO",
            amount=amount,
            due_date=due,
            tax_id=issuer,
            issuer_name=name,
            source="AI",
        )

    key = (
        access_key(data["chave_acesso"])
        if isinstance(data.get("chave_acesso"), str)
        else None
    )
    from_key = reading_from_key(key) if key else DocumentReading()
    reading = DocumentReading(
        kind="NOTA",
        amount=_amount(data.get("valor_total")),
        # The verified key wins over the transcribed CNPJ and number.
        tax_id=from_key.tax_id or issuer,
        document_number=from_key.document_number or _number(data.get("numero")),
        document_type=from_key.document_type
        or _DOCUMENT_TYPES.get(str(data.get("modelo") or "").upper()),
        issue_date=_date(data.get("data_emissao")),
        issuer_name=name,
        installments=_installments(data.get("parcelas")),
        due_date=_date(data.get("vencimento")),
        source="AI",
    )
    if (
        reading.amount is None
        and reading.tax_id is None
        and reading.document_number is None
    ):
        return DocumentReading()
    return reading


def _default_text_llm() -> LLM | None:
    from onyx.llm.factory import get_default_llm

    return get_default_llm(timeout=LLM_TIMEOUT_SECONDS, temperature=0)


def _default_vision_llm() -> LLM | None:
    from onyx.llm.factory import get_default_llm_with_vision

    return get_default_llm_with_vision(timeout=LLM_TIMEOUT_SECONDS, temperature=0)


class AiDocumentReader:
    """``AttachmentReader`` backed by the configured models. Any failure
    (no model, timeout, unreadable answer) is an empty reading."""

    def __init__(
        self,
        text_llm: Callable[[], LLM | None] = _default_text_llm,
        vision_llm: Callable[[], LLM | None] = _default_vision_llm,
    ) -> None:
        self._text_llm = text_llm
        self._vision_llm = vision_llm

    def _ask(
        self, llm: LLM | None, content: str | list[ContentPart]
    ) -> DocumentReading:
        if llm is None:
            return DocumentReading()
        try:
            response = llm.invoke(
                [SystemMessage(content=SYSTEM_PROMPT), UserMessage(content=content)],
                timeout_override=LLM_TIMEOUT_SECONDS,
            )
            return parse_answer(llm_response_to_string(response))
        except Exception:
            logger.exception("TON payables: AI reading of an attachment failed")
            return DocumentReading()

    def read_text(self, text: str) -> DocumentReading:
        if not text.strip():
            return DocumentReading()
        prompt = "Texto extraído do PDF:\n\n" + text[:MAX_TEXT_CHARS]
        try:
            llm = self._text_llm()
        except Exception:
            logger.exception("TON payables: no model for reading attachments")
            return DocumentReading()
        return self._ask(llm, prompt)

    def read_images(self, images: list[bytes]) -> DocumentReading:
        urls = [url for url in map(_image_url, images[:MAX_IMAGES]) if url]
        if not urls:
            return DocumentReading()
        try:
            llm = self._vision_llm()
        except Exception:
            logger.exception("TON payables: no vision model for reading attachments")
            return DocumentReading()
        if llm is None:
            logger.info(
                "TON payables: no vision model configured; photo left for a person"
            )
            return DocumentReading()
        content: list[ContentPart] = [
            TextContentPart(text="Leia o documento da imagem."),
            *(
                ImageContentPart(image_url=ImageUrlDetail(url=url, detail="high"))
                for url in urls
            ),
        ]
        return self._ask(llm, content)
