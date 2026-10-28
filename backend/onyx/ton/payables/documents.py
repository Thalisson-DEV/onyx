"""Reading of payable attachments.

Three kinds of file are read without any model:

* an NF-e or NFS-e XML: issuer tax ID, number and total;
* a boleto, from the typed line printed on the PDF: amount and due date;
* a DANFE PDF, from its 44-digit access key: issuer, model and number.

What is left (an NFS-e PDF in each city hall's layout, a scanned PDF, a
photo) goes to an optional ``AttachmentReader``, which marks its result as
read by AI. Without one, or when it reads nothing, the reading is empty and
the title is marked for a human look instead of guessing.
"""

import datetime
import io
import re
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import Literal, Protocol
from xml.etree.ElementTree import Element

from defusedxml import ElementTree

from onyx.ton.payables.identifiers import access_key, digits, tax_id
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
# The key is printed in groups of four, sometimes with dots.
_KEY_RUN = re.compile(r"\d[\d .]{42,80}\d")
# A value on the same line as its label; on the next line it may belong to
# another column of the DANFE grid, so it is not trusted.
_DANFE_TOTAL = re.compile(
    r"VALOR\s+TOTAL\s+DA\s+NOTA[^\d\n]{0,40}?(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE
)
_DANFE_ISSUE = re.compile(
    r"DATA\s+(?:DA\s+|DE\s+)?EMISS[AÃ]O[^\d\n]{0,40}?(\d{2}/\d{2}/\d{4})", re.IGNORECASE
)
# Below this many characters a PDF page has no usable text (a scan).
_MIN_TEXT = 80
# Who stated the values: the file itself, or a model that read it.
ReadSource = Literal["FILE", "AI"]


@dataclass(frozen=True)
class Installment:
    number: int
    due_date: datetime.date
    amount: Decimal


@dataclass(frozen=True)
class DocumentReading:
    # XML, NOTA (a note read from a PDF or photo), BOLETO or PDF (only the
    # supplier's tax ID found in the text).
    kind: str | None = None
    amount: Decimal | None = None
    tax_id: str | None = None
    document_number: str | None = None
    due_date: datetime.date | None = None
    # Notes only: what the unit would otherwise type by hand.
    document_type: str | None = None
    issue_date: datetime.date | None = None
    issuer_name: str | None = None
    installments: tuple[Installment, ...] = ()
    source: ReadSource = "FILE"

    @property
    def is_read(self) -> bool:
        return self.kind is not None


class AttachmentReader(Protocol):
    """Reads what the deterministic readers could not; see ``ai_reading``."""

    def read_text(self, text: str) -> DocumentReading: ...

    def read_images(self, images: list[bytes]) -> DocumentReading: ...


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


def brl_amount(value: str | None) -> Decimal | None:
    """A positive amount written "7.479,00", "7479,00" or "7479.00"."""
    if not value:
        return None
    text = re.sub(r"[^\d.,]", "", value)
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        amount = Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    return amount if Decimal(0) < amount < Decimal(1000000000) else None


def find_access_key(text: str) -> str | None:
    for run in _KEY_RUN.finditer(text):
        number = digits(run.group())
        for start in range(len(number) - 43):
            key = access_key(number[start : start + 44])
            if key:
                return key
    return None


def reading_from_key(key: str) -> DocumentReading:
    """What the access key states on its own: issuer, model and number."""
    issuer = tax_id(key[6:20]) or tax_id(key[9:20])
    return DocumentReading(
        kind="NOTA",
        tax_id=issuer,
        document_type="NF",
        document_number=str(int(key[25:34])),
    )


def read_danfe_text(text: str) -> DocumentReading:
    """A DANFE: the key, plus the total and issue date when each is printed
    beside its label. A date outside the key's month is dropped."""
    key = find_access_key(text)
    if key is None:
        return DocumentReading()
    reading = reading_from_key(key)
    total = _DANFE_TOTAL.search(text)
    issued = _DANFE_ISSUE.search(text)
    issue_date = None
    if issued:
        try:
            issue_date = datetime.datetime.strptime(issued.group(1), "%d/%m/%Y").date()
        except ValueError:
            issue_date = None
        if issue_date and issue_date.strftime("%y%m") != key[2:6]:
            issue_date = None
    return replace(
        reading,
        amount=brl_amount(total.group(1)) if total else None,
        issue_date=issue_date,
    )


def _merge(base: DocumentReading, extra: DocumentReading) -> DocumentReading:
    """``base`` completed with what ``extra`` adds; any field taken from an AI
    reading makes the whole reading AI."""
    if not extra.is_read:
        return base
    filled = {
        name: getattr(extra, name)
        for name in (
            "amount",
            "tax_id",
            "document_number",
            "due_date",
            "document_type",
            "issue_date",
            "issuer_name",
        )
        if getattr(base, name) is None and getattr(extra, name) is not None
    }
    if not base.installments and extra.installments:
        filled["installments"] = extra.installments
    if not filled:
        return base
    source: ReadSource = "AI" if extra.source == "AI" else base.source
    return replace(base, **filled, source=source)


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages[:5])
    except Exception:
        logger.info("TON payables: PDF text could not be read")
        return ""


def _pdf_images(data: bytes, pages: int = 2) -> list[bytes]:
    """The largest picture of each of the first pages of a scanned PDF."""
    from pypdf import PdfReader

    found: list[bytes] = []
    try:
        reader = PdfReader(io.BytesIO(data))
        for page in reader.pages[:pages]:
            images = sorted(
                page.images, key=lambda image: len(image.data), reverse=True
            )
            if images:
                found.append(images[0].data)
    except Exception:  # noqa: BLE001 — a damaged PDF is left for a person
        logger.info("TON payables: PDF images could not be read")
    return found


def _is_image(lowered: str, content_type: str) -> bool:
    return lowered.endswith((".jpg", ".jpeg", ".png")) or content_type in (
        "image/jpeg",
        "image/png",
    )


def read_attachment(
    data: bytes,
    content_type: str,
    filename: str,
    supplier_tax_id: str | None,
    reader: AttachmentReader | None = None,
) -> DocumentReading:
    """What the TON can state about the file without a person.

    The file's own content always wins; the reader only fills what is left.
    """
    lowered = filename.lower()
    if lowered.endswith(".xml") or "xml" in content_type:
        return read_invoice_xml(data)
    if _is_image(lowered, content_type):
        return reader.read_images([data]) if reader else DocumentReading()
    if not (lowered.endswith(".pdf") or content_type == "application/pdf"):
        return DocumentReading()
    text = _pdf_text(data)
    found_supplier = (
        supplier_tax_id
        if supplier_tax_id
        and any(digits(raw) == supplier_tax_id for raw in _TAX_ID_TEXT.findall(text))
        else None
    )
    boleto = read_bank_line(text)
    if boleto.is_read:
        return DocumentReading(
            kind=boleto.kind,
            amount=boleto.amount,
            due_date=boleto.due_date,
            tax_id=found_supplier,
        )
    danfe = read_danfe_text(text)
    if danfe.is_read:
        if reader and danfe.amount is None:
            return _merge(danfe, reader.read_text(text))
        return danfe
    if reader:
        if len(text.strip()) >= _MIN_TEXT:
            reading = reader.read_text(text)
        else:
            images = _pdf_images(data)
            reading = reader.read_images(images) if images else DocumentReading()
        if reading.is_read:
            return reading
    if found_supplier:
        return DocumentReading(kind="PDF", tax_id=found_supplier)
    return DocumentReading()
