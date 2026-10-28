"""Reading a note that is not an XML: the DANFE key, and the AI fallback for
NFS-e PDFs, scans and photos. The model is faked; the validation is real."""

import datetime
import io
import json
import uuid
from decimal import Decimal
from typing import Any

import pytest
from PIL import Image

from onyx.ton.payables import ai_reading, documents
from onyx.ton.payables import checks as rules
from onyx.ton.payables.ai_reading import AiDocumentReader, parse_answer
from onyx.ton.payables.documents import (
    DocumentReading,
    brl_amount,
    find_access_key,
    read_attachment,
    read_danfe_text,
)
from onyx.ton.payables.identifiers import access_key
from tests.unit.ton.test_payables import SUPPLIER, TODAY, _bank_line, _facts

# Santo André Pneus, NF-e 26358 série 1, October 2026, with its real check digit.
KEY = "41261001651656000137550010000263581000263582"
SPACED_KEY = " ".join(KEY[i : i + 4] for i in range(0, 44, 4))


class FakeReader:
    def __init__(self, reading: DocumentReading | None = None) -> None:
        self.reading = reading or DocumentReading()
        self.texts: list[str] = []
        self.images: list[list[bytes]] = []

    def read_text(self, text: str) -> DocumentReading:
        self.texts.append(text)
        return self.reading

    def read_images(self, images: list[bytes]) -> DocumentReading:
        self.images.append(images)
        return self.reading


class FakeLLM:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.messages: list[Any] = []

    def invoke(self, messages: list[Any], **_: Any) -> str:
        self.messages = messages
        return self.answer


@pytest.fixture(autouse=True)
def _plain_llm_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai_reading, "llm_response_to_string", lambda response: response)


def _photo() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (3000, 1500), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


# ------------------------------------------------------------ access key


def test_access_key_needs_its_check_digit_and_model() -> None:
    assert access_key(SPACED_KEY) == KEY
    assert access_key(KEY[:-1] + "0") is None
    # Model 57 (CT-e) is not a note the units send.
    assert access_key(KEY[:20] + "57" + KEY[22:]) is None


def test_danfe_text_reads_key_total_and_issue_date() -> None:
    text = (
        "DANFE\nCHAVE DE ACESSO\n" + SPACED_KEY + "\n"
        "DATA DA EMISSÃO 06/10/2026\n"
        "VALOR TOTAL DA NOTA 7.479,00\n"
    )
    reading = read_danfe_text(text)
    assert reading.kind == "NOTA"
    assert reading.source == "FILE"
    assert reading.tax_id == SUPPLIER
    assert reading.document_number == "26358"
    assert reading.document_type == "NF"
    assert reading.amount == Decimal("7479.00")
    assert reading.issue_date == datetime.date(2026, 10, 6)


def test_danfe_total_on_another_line_is_not_trusted() -> None:
    text = (
        SPACED_KEY
        + "\nVALOR TOTAL DA NOTA\n1.234,56 7.479,00\nDATA DA EMISSÃO 06/09/2026"
    )
    reading = read_danfe_text(text)
    assert reading.amount is None
    # September is not the key's month (October).
    assert reading.issue_date is None


def test_boleto_line_is_not_mistaken_for_a_key() -> None:
    assert find_access_key(_bank_line(79140, datetime.date(2026, 11, 10))) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("7.479,00", "7479.00"),
        ("7479,5", "7479.50"),
        ("7479.00", "7479.00"),
        ("0,00", None),
        ("abc", None),
    ],
)
def test_brl_amount(raw: str, expected: str | None) -> None:
    assert brl_amount(raw) == (Decimal(expected) if expected else None)


# ------------------------------------------------------------ orchestration


def test_danfe_without_total_asks_the_reader_and_becomes_ai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        documents, "_pdf_text", lambda _: "DANFE " + SPACED_KEY + " " * 100
    )
    reader = FakeReader(
        DocumentReading(
            kind="NOTA", amount=Decimal("7479.00"), tax_id="11222333000181", source="AI"
        )
    )
    reading = read_attachment(b"%PDF", "application/pdf", "danfe.pdf", None, reader)
    # The key wins: the reader only fills the missing total.
    assert reading.tax_id == SUPPLIER
    assert reading.amount == Decimal("7479.00")
    assert reading.source == "AI"


def test_pdf_with_text_and_no_key_goes_to_the_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "PREFEITURA DE MOSSORÓ - NOTA FISCAL DE SERVIÇO ELETRÔNICA " * 3
    monkeypatch.setattr(documents, "_pdf_text", lambda _: text)
    reader = FakeReader(
        DocumentReading(kind="NOTA", amount=Decimal("2600.00"), source="AI")
    )
    reading = read_attachment(b"%PDF", "application/pdf", "nfse.pdf", None, reader)
    assert reader.texts == [text]
    assert reading.amount == Decimal("2600.00")


def test_scanned_pdf_sends_its_pictures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(documents, "_pdf_text", lambda _: "")
    monkeypatch.setattr(documents, "_pdf_images", lambda _: [b"page1"])
    reader = FakeReader()
    read_attachment(b"%PDF", "application/pdf", "scan.pdf", None, reader)
    assert reader.images == [[b"page1"]]


def test_boleto_pdf_never_calls_the_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    line = _bank_line(79140, datetime.date(2026, 11, 10))
    monkeypatch.setattr(documents, "_pdf_text", lambda _: "Linha digitável " + line)
    reader = FakeReader()
    reading = read_attachment(b"%PDF", "application/pdf", "boleto.pdf", None, reader)
    assert reading.kind == "BOLETO" and reading.source == "FILE"
    assert reader.texts == [] and reader.images == []


def test_photo_without_reader_is_left_for_a_person() -> None:
    assert not read_attachment(b"jpg", "image/jpeg", "nota.jpg", None).is_read


# ------------------------------------------------------------ model answer


def test_answer_with_valid_fields_is_an_ai_note() -> None:
    reading = parse_answer(
        "```json\n"
        + json.dumps(
            {
                "tipo": "NOTA",
                "modelo": "NFSE",
                "cnpj_emitente": "01.651.656/0001-37",
                "numero": "211",
                "data_emissao": "2026-10-14",
                "valor_total": "2.600,00",
                "parcelas": [{"numero": 1, "vencimento": "2026-11-20", "valor": 2600}],
            }
        )
        + "\n```"
    )
    assert reading.kind == "NOTA" and reading.source == "AI"
    assert reading.tax_id == SUPPLIER
    assert reading.document_type == "NFSE"
    assert reading.amount == Decimal("2600.00")
    assert reading.installments[0].due_date == datetime.date(2026, 11, 20)


def test_answer_with_invalid_cnpj_and_date_drops_them() -> None:
    reading = parse_answer(
        json.dumps(
            {
                "tipo": "NOTA",
                "cnpj_emitente": "01.651.656/0001-38",
                "numero": "9",
                "data_emissao": "14/10/2026",
            }
        )
    )
    assert reading.tax_id is None
    assert reading.issue_date is None
    assert reading.document_number == "9"


def test_transcribed_key_wins_over_transcribed_cnpj() -> None:
    reading = parse_answer(
        json.dumps(
            {
                "tipo": "NOTA",
                "chave_acesso": SPACED_KEY,
                "cnpj_emitente": "11222333000181",
                "numero": "1",
            }
        )
    )
    assert reading.tax_id == SUPPLIER
    assert reading.document_number == "26358"


def test_boleto_line_that_passes_its_digits_is_trusted() -> None:
    due = datetime.date(2026, 11, 10)
    line = _bank_line(79140, due).replace(".", "").replace(" ", "")
    reading = parse_answer(
        json.dumps({"tipo": "BOLETO", "linha_digitavel": line, "valor_total": "1.00"})
    )
    assert reading.kind == "BOLETO"
    assert reading.source == "FILE"
    assert reading.amount == Decimal("791.40") and reading.due_date == due


@pytest.mark.parametrize(
    "answer", ["", "não consegui ler", "{}", "[1, 2]", '{"tipo": "OUTRO"}']
)
def test_unusable_answers_are_empty(answer: str) -> None:
    assert not parse_answer(answer).is_read


def test_reader_sends_a_resized_photo_to_the_vision_model() -> None:
    llm = FakeLLM(json.dumps({"tipo": "NOTA", "valor_total": "10.00"}))
    reader = AiDocumentReader(text_llm=lambda: None, vision_llm=lambda: llm)  # type: ignore[arg-type,return-value]
    reading = reader.read_images([_photo()])
    assert reading.amount == Decimal("10.00")
    image_part = llm.messages[1].content[1]
    assert image_part.image_url.url.startswith("data:image/jpeg;base64,")


def test_reader_without_a_vision_model_reads_nothing() -> None:
    reader = AiDocumentReader(text_llm=lambda: None, vision_llm=lambda: None)
    assert not reader.read_images([_photo()]).is_read


def test_reader_survives_a_failing_model() -> None:
    class Broken:
        def invoke(self, *_: Any, **__: Any) -> str:
            raise TimeoutError

    reader = AiDocumentReader(text_llm=lambda: Broken(), vision_llm=lambda: None)  # type: ignore[arg-type,return-value]
    assert not reader.read_text("NFS-e " * 30).is_read


# ------------------------------------------------------------ checks


def _ai_note(tax_id: str) -> rules.AttachmentFacts:
    return rules.AttachmentFacts(
        id=uuid.uuid4(),
        role="INVOICE",
        name="nota.jpg",
        read_kind="NOTA",
        read_amount=Decimal("2374.20"),
        read_tax_id=tax_id,
        read_due_date=None,
        read_source="AI",
    )


def test_ai_reading_of_another_issuer_is_attention_not_block() -> None:
    results = rules.evaluate(_facts(attachments=(_ai_note("82603929000170"),)), TODAY)
    mismatch = next(result for result in results if result.code == "ATTACHMENT_TAX_ID")
    assert mismatch.severity == rules.ATTENTION
    assert not any(result.blocks_release for result in results)
    assert "READ_BY_AI" in [result.code for result in results]


def test_danfe_read_by_key_blocks_like_the_xml() -> None:
    attachment = rules.AttachmentFacts(
        id=uuid.uuid4(),
        role="INVOICE",
        name="danfe.pdf",
        read_kind="NOTA",
        read_amount=Decimal("2374.20"),
        read_tax_id="82603929000170",
        read_due_date=None,
        read_source="FILE",
    )
    results = rules.evaluate(_facts(attachments=(attachment,)), TODAY)
    assert any(
        result.code == "ATTACHMENT_TAX_ID" and result.blocks_release
        for result in results
    )
