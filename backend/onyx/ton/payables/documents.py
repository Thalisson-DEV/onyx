"""Deterministic reading of payable attachments.

Two kinds of file are read without any model:

* an NF-e or NFS-e XML: issuer tax ID, number and total;
* a boleto, from the typed line printed on the PDF: amount and due date.

Anything else returns an empty reading, and the title is marked for a human
look instead of guessing.
"""

import datetime
import io
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import Element

from defusedxml import ElementTree

from onyx.ton.payables.identifiers import digits, tax_id
from onyx.utils.logger import setup_logger

logger = setup_logger()

# Boletos issued since 2025-02-22 count the due-date factor from 1000 again.
_FACTOR_BASE = datetime.date(2025, 2, 22)
_BANK_LINE = re.compile(
    r"(\d{5})\.?\s?(\d{5})\s+(\d{5})\.?\s?(\d{6})\s+(\d{5})\.?\s?(\d{6})\s+(\d)\s+(\d{14})"
)
_COLLECTION_LINE = re.compile(
    r"(8\d{10})\s?-?\s?(\d)\s+(\d{11})\s?-?\s?(\d)\s+(\d{11})\s?-?\s?(\d)\s+(\d{11})\s?-?\s?(\d)"
)
_TAX_ID_TEXT = re.compile(
    r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}|\d{3}\.?\d{3}\.?\d{3}-?\d{2}"
)

_ISSUER_PATHS = (
    ("emit", "CNPJ"),
    ("emit", "CPF"),
    ("Prestador", "Cnpj"),
    ("PrestadorServico", "Cnpj"),
    ("IdentificacaoPrestador", "Cnpj"),
    ("prest", "CNPJ"),
    ("prest", "CPF"),
)
_NUMBER_TAGS = ("nNF", "nNFSe", "Numero")
_AMOUNT_TAGS = ("vNF", "ValorLiquidoNfse", "vLiq", "ValorServicos", "vServ")
_ISSUE_TAGS = ("dhEmi", "dEmi", "DataEmissao", "dhProc")
_ISSUER_NAME_PARENTS = ("emit", "Prestador", "PrestadorServico", "prest")
_ISSUER_NAME_TAGS = ("xNome", "RazaoSocial", "xFant", "NomeFantasia")


@dataclass(frozen=True)
class Installment:
    number: int
    due_date: datetime.date
    amount: Decimal


@dataclass(frozen=True)
class DocumentReading:
    kind: str | None = None
    amount: Decimal | None = None
    tax_id: str | None = None
    document_number: str | None = None
    due_date: datetime.date | None = None
    # XML only: what the unit would otherwise type by hand.
    document_type: str | None = None
    issue_date: datetime.date | None = None
    issuer_name: str | None = None
    installments: tuple[Installment, ...] = ()

    @property
    def is_read(self) -> bool:
        return self.kind is not None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_text(root: Element, names: tuple[str, ...]) -> str | None:
    for name in names:
        for element in root.iter():
            if _local(element.tag) == name and element.text and element.text.strip():
                return element.text.strip()
    return None


def _issuer(root: Element) -> str | None:
    for parent_name, child_name in _ISSUER_PATHS:
        for element in root.iter():
            if _local(element.tag) != parent_name:
                continue
            for child in element.iter():
                if _local(child.tag) == child_name and child.text:
                    found = tax_id(child.text)
                    if found:
                        return found
    return None


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value.replace(",", ".")).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _date(value: str | None) -> datetime.date | None:
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _issuer_name(root: Element) -> str | None:
    for element in root.iter():
        if _local(element.tag) not in _ISSUER_NAME_PARENTS:
            continue
        for child in element.iter():
            if (
                _local(child.tag) in _ISSUER_NAME_TAGS
                and child.text
                and child.text.strip()
            ):
                return child.text.strip()[:300]
    return None


def _installments(root: Element) -> tuple[Installment, ...]:
    """The NF-e duplicatas (``cobr/dup``): number, due date and amount."""
    found: list[Installment] = []
    for element in root.iter():
        if _local(element.tag) != "dup":
            continue
        values = {_local(child.tag): (child.text or "").strip() for child in element}
        due = _date(values.get("dVenc"))
        amount = _decimal(values.get("vDup"))
        if due is None or amount is None:
            continue
        number_digits = digits(values.get("nDup", ""))
        number = int(number_digits) if number_digits else len(found) + 1
        found.append(Installment(number=number, due_date=due, amount=amount))
    return tuple(sorted(found, key=lambda item: item.due_date))


def read_invoice_xml(data: bytes) -> DocumentReading:
    try:
        root = ElementTree.fromstring(data)
    except Exception:
        return DocumentReading()
    amount = _decimal(_first_text(root, _AMOUNT_TAGS))
    issuer = _issuer(root)
    if amount is None and issuer is None:
        return DocumentReading()
    tags = {_local(element.tag) for element in root.iter()}
    return DocumentReading(
        kind="XML",
        amount=amount,
        tax_id=issuer,
        document_number=_first_text(root, _NUMBER_TAGS),
        document_type="NF" if "infNFe" in tags else "NFSE",
        issue_date=_date(_first_text(root, _ISSUE_TAGS)),
        issuer_name=_issuer_name(root),
        installments=_installments(root),
    )


def _mod10(block: str) -> int:
    total = 0
    for index, char in enumerate(reversed(block)):
        product = int(char) * (2 if index % 2 == 0 else 1)
        total += product // 10 + product % 10
    return (10 - total % 10) % 10


def read_bank_line(text: str) -> DocumentReading:
    """Amount and due date from a bank boleto line (47 digits) or a
    collection line (48 digits, starting with 8)."""
    for match in _BANK_LINE.finditer(text):
        groups = match.groups()
        field1 = groups[0] + groups[1]
        field2 = groups[2] + groups[3]
        field3 = groups[4] + groups[5]
        if not all(
            _mod10(field[:-1]) == int(field[-1]) for field in (field1, field2, field3)
        ):
            continue
        tail = groups[7]
        factor = int(tail[:4])
        cents = int(tail[4:])
        due = (
            _FACTOR_BASE + datetime.timedelta(days=factor - 1000)
            if factor >= 1000
            else None
        )
        return DocumentReading(
            kind="BOLETO",
            amount=Decimal(cents) / Decimal(100) if cents else None,
            due_date=due,
        )
    for match in _COLLECTION_LINE.finditer(text):
        blocks = match.groups()[0::2]
        barcode = "".join(blocks)
        # Third digit 6 or 8: the barcode carries the real amount.
        if barcode[2] not in "68":
            continue
        cents = int(barcode[4:15])
        return DocumentReading(
            kind="BOLETO",
            amount=Decimal(cents) / Decimal(100) if cents else None,
        )
    return DocumentReading()


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages[:5])
    except Exception:
        logger.info("TON payables: PDF text could not be read")
        return ""


def read_attachment(
    data: bytes, content_type: str, filename: str, supplier_tax_id: str | None
) -> DocumentReading:
    """What the TON can state about the file without a person."""
    lowered = filename.lower()
    if lowered.endswith(".xml") or "xml" in content_type:
        return read_invoice_xml(data)
    if not (lowered.endswith(".pdf") or content_type == "application/pdf"):
        return DocumentReading()
    text = _pdf_text(data)
    reading = read_bank_line(text)
    found_supplier = (
        supplier_tax_id
        if supplier_tax_id
        and any(digits(raw) == supplier_tax_id for raw in _TAX_ID_TEXT.findall(text))
        else None
    )
    if reading.is_read:
        return DocumentReading(
            kind=reading.kind,
            amount=reading.amount,
            due_date=reading.due_date,
            tax_id=found_supplier,
        )
    if found_supplier:
        return DocumentReading(kind="PDF", tax_id=found_supplier)
    return DocumentReading()
