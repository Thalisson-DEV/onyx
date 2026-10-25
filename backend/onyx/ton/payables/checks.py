"""Deterministic checks of a payable title.

Pure functions over plain facts, so each check is tested without a database.
A ``BLOCK`` check stops the release until it is fixed or a person decides it
does not apply (with a reason); ``ATTENTION`` and ``INFO`` only inform.
"""

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from onyx.ton.payables.identifiers import business_days_between, format_tax_id

BLOCK = "BLOCK"
ATTENTION = "ATTENTION"
INFO = "INFO"

# Working days between sending and due date below which the title is late.
# Provisional: the Zeev flow alerts at "menos de 5 dias úteis" and the
# Controladoria still has to approve the rule for unit payables.
NOTICE_BUSINESS_DAYS = 5
# Days after an estimate's period before it is flagged without an invoice.
ESTIMATE_TOLERANCE_DAYS = 5
# Natureza code prefixes that come from the DP, not from unit payables.
PAYROLL_PREFIXES = ("2.01", "2.02", "2.03", "2.04", "2.05")
# Codes a person may set aside with a reason.
DECIDABLE = frozenset(
    {"DUPLICATE", "ATTACHMENT_AMOUNT", "ATTACHMENT_TAX_ID", "PAYEE_MISMATCH"}
)


def brl(value: Decimal) -> str:
    text = f"{value:,.2f}"
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def br_date(value: datetime.date) -> str:
    return value.strftime("%d/%m/%Y")


@dataclass(frozen=True)
class AttachmentFacts:
    id: UUID
    role: str
    name: str
    read_kind: str | None
    read_amount: Decimal | None
    read_tax_id: str | None
    read_due_date: datetime.date | None


@dataclass(frozen=True)
class OtherTitle:
    id: UUID
    number: int
    unit_name: str
    installment_number: int
    installment_count: int
    amount: Decimal
    status: str


@dataclass(frozen=True)
class SupplierFacts:
    tax_id: str
    status: str
    pix_key_type: str | None
    pix_key: str | None
    # Other suppliers that share this one's PIX key or bank account.
    shared_with: tuple[str, ...] = ()


@dataclass(frozen=True)
class TitleFacts:
    id: UUID
    kind: str
    status: str
    document_label: str
    account_code: str
    amount: Decimal
    purchase_total: Decimal
    installment_number: int
    installment_count: int
    due_date: datetime.date
    submitted_on: datetime.date
    estimate_until: datetime.date | None
    supplier: SupplierFacts
    attachments: tuple[AttachmentFacts, ...] = ()
    # Real titles of the same supplier and document, other than this one.
    same_document: tuple[OtherTitle, ...] = ()
    # (check code, subject) pairs a person already set aside.
    decisions: frozenset[tuple[str, str]] = field(default_factory=frozenset)


@dataclass(frozen=True)
class CheckResult:
    code: str
    severity: str
    title: str
    detail: str
    subject: str = ""
    decided: bool = False

    @property
    def blocks_release(self) -> bool:
        return self.severity == BLOCK and not self.decided


def _number(value: int) -> str:
    return f"CP-{value:06d}"


def _duplicates(facts: TitleFacts) -> list[CheckResult]:
    results = []
    for other in facts.same_document:
        if other.status == "CANCELLED":
            continue
        if (other.installment_number, other.installment_count) != (
            facts.installment_number,
            facts.installment_count,
        ):
            continue
        results.append(
            CheckResult(
                code="DUPLICATE",
                severity=BLOCK,
                title="Documento já enviado",
                detail=(
                    f"{facts.document_label} parcela {facts.installment_number}/"
                    f"{facts.installment_count} também está em {_number(other.number)}"
                    f" ({other.unit_name})."
                ),
                subject=str(other.id),
            )
        )
    return results


def _installments(facts: TitleFacts) -> list[CheckResult]:
    others = [
        other
        for other in facts.same_document
        if other.status != "CANCELLED"
        and other.installment_count == facts.installment_count
    ]
    numbers = {other.installment_number for other in others} | {
        facts.installment_number
    }
    if facts.installment_count < 2 or len(numbers) < facts.installment_count:
        return []
    by_number = {other.installment_number: other.amount for other in others}
    by_number[facts.installment_number] = facts.amount
    total = sum(by_number.values(), Decimal(0))
    if abs(total - facts.purchase_total) <= Decimal("0.05"):
        return []
    return [
        CheckResult(
            code="INSTALLMENTS_SUM",
            severity=ATTENTION,
            title="Parcelas não fecham com a compra",
            detail=(
                f"As {facts.installment_count} parcelas somam {brl(total)}; "
                f"a compra é de {brl(facts.purchase_total)}."
            ),
        )
    ]


def _attachments(facts: TitleFacts) -> list[CheckResult]:
    if not facts.attachments:
        return [
            CheckResult(
                code="NO_ATTACHMENT",
                severity=BLOCK,
                title="Sem anexo",
                detail="Anexe a nota e o boleto, ou o recibo.",
            )
        ]
    results: list[CheckResult] = []
    supplier = facts.supplier.tax_id
    for attachment in facts.attachments:
        if attachment.read_kind == "BOLETO" and attachment.read_amount is not None:
            if abs(attachment.read_amount - facts.amount) > Decimal("0.01"):
                results.append(
                    CheckResult(
                        code="ATTACHMENT_AMOUNT",
                        severity=BLOCK,
                        title="Valor do boleto diferente",
                        detail=(
                            f"Boleto de {brl(attachment.read_amount)}; "
                            f"título de {brl(facts.amount)}."
                        ),
                        subject=str(attachment.id),
                    )
                )
            if (
                attachment.read_due_date is not None
                and attachment.read_due_date != facts.due_date
            ):
                results.append(
                    CheckResult(
                        code="ATTACHMENT_DUE",
                        severity=ATTENTION,
                        title="Vencimento do boleto diferente",
                        detail=(
                            f"Boleto vence em {br_date(attachment.read_due_date)}; "
                            f"título em {br_date(facts.due_date)}."
                        ),
                        subject=str(attachment.id),
                    )
                )
        if attachment.read_kind == "XML":
            if attachment.read_amount is not None and abs(
                attachment.read_amount - facts.purchase_total
            ) > Decimal("0.01"):
                results.append(
                    CheckResult(
                        code="ATTACHMENT_AMOUNT",
                        severity=BLOCK,
                        title="Valor da nota diferente",
                        detail=(
                            f"Nota de {brl(attachment.read_amount)}; compra "
                            f"informada de {brl(facts.purchase_total)}."
                        ),
                        subject=str(attachment.id),
                    )
                )
            if attachment.read_tax_id and attachment.read_tax_id != supplier:
                results.append(
                    CheckResult(
                        code="ATTACHMENT_TAX_ID",
                        severity=BLOCK,
                        title="Nota de outro emitente",
                        detail=(
                            f"A nota foi emitida por {format_tax_id(attachment.read_tax_id)};"
                            f" o fornecedor do título é {format_tax_id(supplier)}."
                        ),
                        subject=str(attachment.id),
                    )
                )
    if not any(attachment.read_kind for attachment in facts.attachments):
        results.append(
            CheckResult(
                code="NEEDS_HUMAN_LOOK",
                severity=INFO,
                title="Conferência manual do anexo",
                detail=(
                    "O TON não conseguiu ler valor nem CNPJ do anexo. "
                    "Confira com o título."
                ),
            )
        )
    return results


def _supplier(facts: TitleFacts) -> list[CheckResult]:
    supplier = facts.supplier
    results: list[CheckResult] = []
    if supplier.status != "ACTIVE":
        results.append(
            CheckResult(
                code="SUPPLIER_PENDING",
                severity=BLOCK,
                title="Fornecedor sem aprovação",
                detail="O cadastro do fornecedor aguarda aprovação do financeiro.",
            )
        )
    if (
        supplier.pix_key_type in ("CPF", "CNPJ")
        and supplier.pix_key
        and "".join(c for c in supplier.pix_key if c.isdigit()) != supplier.tax_id
    ):
        results.append(
            CheckResult(
                code="PAYEE_MISMATCH",
                severity=BLOCK,
                title="PIX em nome de outra pessoa",
                detail=(
                    f"A chave PIX ({supplier.pix_key}) não é o "
                    f"{supplier.pix_key_type} do fornecedor."
                ),
                subject=supplier.pix_key,
            )
        )
    if supplier.shared_with:
        results.append(
            CheckResult(
                code="SHARED_ACCOUNT",
                severity=ATTENTION,
                title="Conta usada por outro cadastro",
                detail=(
                    "A mesma chave PIX ou conta bancária está em: "
                    + ", ".join(supplier.shared_with)
                    + "."
                ),
            )
        )
    return results


def _timing(facts: TitleFacts, today: datetime.date) -> list[CheckResult]:
    if facts.kind == "ESTIMATE":
        if (
            facts.status == "ESTIMATE_OPEN"
            and facts.estimate_until is not None
            and today
            > facts.estimate_until + datetime.timedelta(days=ESTIMATE_TOLERANCE_DAYS)
        ):
            return [
                CheckResult(
                    code="ESTIMATE_WITHOUT_INVOICE",
                    severity=ATTENTION,
                    title="Estimativa sem nota",
                    detail=(
                        f"O período terminou em {br_date(facts.estimate_until)} "
                        "e a nota ainda não foi enviada."
                    ),
                )
            ]
        return []
    days = business_days_between(facts.submitted_on, facts.due_date)
    if days >= NOTICE_BUSINESS_DAYS:
        return []
    detail = (
        "Enviado depois do vencimento."
        if facts.due_date < facts.submitted_on
        else f"Enviado a {days} {'dia útil' if days == 1 else 'dias úteis'} do "
        f"vencimento (o prazo é de {NOTICE_BUSINESS_DAYS})."
    )
    return [
        CheckResult(
            code="LATE_NOTICE",
            severity=ATTENTION,
            title="Em cima do vencimento",
            detail=detail,
        )
    ]


def _nature(facts: TitleFacts) -> list[CheckResult]:
    if facts.account_code.startswith(PAYROLL_PREFIXES):
        return [
            CheckResult(
                code="PAYROLL_NATURE",
                severity=ATTENTION,
                title="Folha no contas a pagar",
                detail="Folha, encargos e rescisões vêm do DP, não da unidade.",
            )
        ]
    return []


def evaluate(facts: TitleFacts, today: datetime.date) -> list[CheckResult]:
    """Every check of the title, blocking ones first."""
    if facts.status == "CANCELLED":
        return []
    results: list[CheckResult] = []
    if facts.kind == "REAL":
        results += _duplicates(facts)
        results += _attachments(facts)
        results += _installments(facts)
    results += _supplier(facts)
    results += _timing(facts, today)
    results += _nature(facts)
    decided = [
        CheckResult(
            code=result.code,
            severity=result.severity,
            title=result.title,
            detail=result.detail,
            subject=result.subject,
            decided=(result.code, result.subject) in facts.decisions,
        )
        for result in results
    ]
    order = {BLOCK: 0, ATTENTION: 1, INFO: 2}
    return sorted(decided, key=lambda result: (result.decided, order[result.severity]))


@dataclass(frozen=True)
class Confirmation:
    """One line of "conferido pelo TON": what was compared and how it came out.

    ``state`` is ``OK``, ``ATTENTION``, ``MISMATCH`` or ``UNKNOWN`` (nothing to
    compare yet, so a person checks it).
    """

    label: str
    value: str
    state: str


def confirmations(facts: TitleFacts) -> list[Confirmation]:
    """The comparisons the conference screen shows, in a fixed order."""
    if facts.kind != "REAL" or facts.status == "CANCELLED":
        return []
    supplier = facts.supplier
    result: list[Confirmation] = []
    read_ids = [a.read_tax_id for a in facts.attachments if a.read_tax_id]
    result.append(
        Confirmation(
            label="CNPJ da nota é o do fornecedor",
            value=format_tax_id(read_ids[0]) if read_ids else "Sem leitura",
            state="UNKNOWN"
            if not read_ids
            else "OK"
            if all(found == supplier.tax_id for found in read_ids)
            else "MISMATCH",
        )
    )
    boletos = [
        a for a in facts.attachments if a.read_kind == "BOLETO" and a.read_amount
    ]
    if boletos:
        amount = boletos[0].read_amount
        assert amount is not None
        result.append(
            Confirmation(
                label="Valor do boleto é o do título",
                value=brl(amount),
                state="OK"
                if abs(amount - facts.amount) <= Decimal("0.01")
                else "MISMATCH",
            )
        )
        due = boletos[0].read_due_date
        if due is not None:
            result.append(
                Confirmation(
                    label="Vencimento do boleto é o do título",
                    value=br_date(due),
                    state="OK" if due == facts.due_date else "ATTENTION",
                )
            )
    else:
        result.append(
            Confirmation(
                label="Valor do boleto é o do título",
                value="Sem boleto lido",
                state="UNKNOWN",
            )
        )
    invoices = [a for a in facts.attachments if a.read_kind == "XML" and a.read_amount]
    if invoices:
        amount = invoices[0].read_amount
        assert amount is not None
        result.append(
            Confirmation(
                label="Total da nota é o total da compra",
                value=brl(amount),
                state="OK"
                if abs(amount - facts.purchase_total) <= Decimal("0.01")
                else "MISMATCH",
            )
        )
    if facts.installment_count > 1:
        sums = _installments(facts)
        others = {
            other.installment_number
            for other in facts.same_document
            if other.status != "CANCELLED"
        } | {facts.installment_number}
        result.append(
            Confirmation(
                label=f"{facts.installment_count} parcelas somam o total da compra",
                value=f"{len(others)} de {facts.installment_count} enviadas",
                state="MISMATCH"
                if sums
                else "OK"
                if len(others) >= facts.installment_count
                else "UNKNOWN",
            )
        )
    pix_digits = "".join(c for c in (supplier.pix_key or "") if c.isdigit())
    own = supplier.pix_key_type not in ("CPF", "CNPJ") or pix_digits == supplier.tax_id
    result.append(
        Confirmation(
            label="Pagamento no nome do próprio favorecido",
            value=f"PIX {supplier.pix_key_type}"
            if supplier.pix_key
            else "Conta bancária",
            state="OK" if own else "MISMATCH",
        )
    )
    days = business_days_between(facts.submitted_on, facts.due_date)
    result.append(
        Confirmation(
            label=f"Enviado com {NOTICE_BUSINESS_DAYS} dias úteis de antecedência",
            value="depois do vencimento"
            if days < 0
            else f"{days} {'dia útil' if days == 1 else 'dias úteis'}",
            state="OK" if days >= NOTICE_BUSINESS_DAYS else "ATTENTION",
        )
    )
    duplicates = _duplicates(facts)
    numbers = {str(other.id): _number(other.number) for other in facts.same_document}
    open_duplicates = [
        check
        for check in duplicates
        if (check.code, check.subject) not in facts.decisions
    ]
    result.insert(
        0,
        Confirmation(
            label="Documento e parcela enviados uma vez só",
            value="também em "
            + ", ".join(
                numbers.get(check.subject, "outro título") for check in duplicates
            )
            if open_duplicates
            else "Dispensado com motivo"
            if duplicates
            else "Único",
            state="MISMATCH" if open_duplicates else "OK",
        ),
    )
    return result
