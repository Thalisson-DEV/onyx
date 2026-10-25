import datetime
import uuid
from decimal import Decimal

from onyx.ton.payables import checks as rules
from onyx.ton.payables.documents import _mod10, read_bank_line, read_invoice_xml
from onyx.ton.payables.identifiers import (
    business_days_between,
    document_key,
    name_key,
    plate,
    tax_id,
)

# Real check digits: Santo André Pneus (from the Toledo sheet) and a valid CPF.
SUPPLIER = "01651656000137"
OTHER_CNPJ = "82603929000170"


def _bank_line(amount_cents: int, due: datetime.date) -> str:
    factor = 1000 + (due - datetime.date(2025, 2, 22)).days
    field1 = "001900000"
    field2 = "0000000000"
    field3 = "0000000000"
    parts = [field + str(_mod10(field)) for field in (field1, field2, field3)]
    tail = f"{factor:04d}{amount_cents:010d}"
    return (
        f"{parts[0][:5]}.{parts[0][5:]} {parts[1][:5]}.{parts[1][5:]} "
        f"{parts[2][:5]}.{parts[2][5:]} 1 {tail}"
    )


def _facts(**overrides: object) -> rules.TitleFacts:
    values: dict[str, object] = dict(
        id=uuid.uuid4(),
        kind="REAL",
        status="RECEIVED",
        document_label="NF 38371",
        account_code="3.02",
        amount=Decimal("791.40"),
        purchase_total=Decimal("2374.20"),
        installment_number=3,
        installment_count=3,
        due_date=datetime.date(2026, 11, 10),
        submitted_on=datetime.date(2026, 10, 26),
        estimate_until=None,
        supplier=rules.SupplierFacts(
            tax_id=SUPPLIER, status="ACTIVE", pix_key_type="CNPJ", pix_key=SUPPLIER
        ),
        attachments=(
            rules.AttachmentFacts(
                id=uuid.uuid4(),
                role="BOLETO",
                name="boleto.pdf",
                read_kind="BOLETO",
                read_amount=Decimal("791.40"),
                read_tax_id=None,
                read_due_date=datetime.date(2026, 11, 10),
            ),
        ),
    )
    values.update(overrides)
    return rules.TitleFacts(**values)  # type: ignore[arg-type]


def _codes(results: list[rules.CheckResult]) -> list[str]:
    return [result.code for result in results]


TODAY = datetime.date(2026, 10, 26)


def test_identifiers() -> None:
    assert tax_id("01.651.656/0001-37") == SUPPLIER
    assert tax_id("01.651.656/0001-38") is None
    assert tax_id("529.982.247-25") == "52998224725"
    assert tax_id("111.111.111-11") is None
    assert plate("jbe-7i24") == "JBE7I24"
    assert plate("JAW 3J07") == "JAW3J07"
    assert plate("VEICULO") is None
    assert document_key("NF 009151") == "9151"
    assert document_key("9.151") == "9151"
    assert document_key("113/114/115") == "113/114/115"
    assert document_key("NFSe 03") == "3"
    assert name_key("Santo André Pneus Ltda.") == "SANTO ANDRE PNEUS"


def test_business_days_skip_weekends() -> None:
    friday = datetime.date(2026, 10, 23)
    assert business_days_between(friday, datetime.date(2026, 10, 26)) == 1
    assert business_days_between(friday, datetime.date(2026, 10, 30)) == 5
    assert business_days_between(datetime.date(2026, 10, 30), friday) == -5


def test_bank_line_reads_amount_and_due_date() -> None:
    due = datetime.date(2026, 10, 28)
    reading = read_bank_line("Linha digitável: " + _bank_line(79140, due))
    assert reading.kind == "BOLETO"
    assert reading.amount == Decimal("791.40")
    assert reading.due_date == due


def test_bank_line_with_bad_check_digit_is_ignored() -> None:
    line = _bank_line(79140, datetime.date(2026, 10, 28))
    broken = line[:10] + ("1" if line[10] != "1" else "2") + line[11:]
    assert not read_bank_line(broken).is_read


def test_nfe_xml_reading() -> None:
    xml = f"""<?xml version="1.0"?>
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe>
      <ide><nNF>38371</nNF></ide>
      <emit><CNPJ>{SUPPLIER}</CNPJ><xNome>SANTO ANDRE</xNome></emit>
      <dest><CNPJ>{OTHER_CNPJ}</CNPJ></dest>
      <total><ICMSTot><vNF>2374.20</vNF></ICMSTot></total>
    </infNFe></NFe></nfeProc>""".encode()
    reading = read_invoice_xml(xml)
    assert reading.kind == "XML"
    assert reading.tax_id == SUPPLIER
    assert reading.amount == Decimal("2374.20")
    assert reading.document_number == "38371"


def test_clean_title_has_no_blocking_check() -> None:
    results = rules.evaluate(_facts(), TODAY)
    assert not [result for result in results if result.blocks_release]


def test_duplicate_installment_blocks_until_decided() -> None:
    other = rules.OtherTitle(
        id=uuid.uuid4(),
        number=45,
        unit_name="TOLEDO-PR",
        installment_number=3,
        installment_count=3,
        amount=Decimal("791.40"),
        status="RELEASED",
    )
    results = rules.evaluate(_facts(same_document=(other,)), TODAY)
    duplicate = next(result for result in results if result.code == "DUPLICATE")
    assert duplicate.blocks_release
    assert "CP-000045" in duplicate.detail
    decided = rules.evaluate(
        _facts(
            same_document=(other,),
            decisions=frozenset({("DUPLICATE", str(other.id))}),
        ),
        TODAY,
    )
    assert not [result for result in decided if result.blocks_release]


def test_other_installment_is_not_a_duplicate() -> None:
    other = rules.OtherTitle(
        id=uuid.uuid4(),
        number=44,
        unit_name="TOLEDO-PR",
        installment_number=2,
        installment_count=3,
        amount=Decimal("791.40"),
        status="RELEASED",
    )
    assert "DUPLICATE" not in _codes(
        rules.evaluate(_facts(same_document=(other,)), TODAY)
    )


def test_boleto_amount_differs() -> None:
    attachment = rules.AttachmentFacts(
        id=uuid.uuid4(),
        role="BOLETO",
        name="boleto.pdf",
        read_kind="BOLETO",
        read_amount=Decimal("791.40"),
        read_tax_id=None,
        read_due_date=None,
    )
    results = rules.evaluate(
        _facts(amount=Decimal("1582.80"), attachments=(attachment,)), TODAY
    )
    mismatch = next(result for result in results if result.code == "ATTACHMENT_AMOUNT")
    assert mismatch.blocks_release
    assert "R$ 791,40" in mismatch.detail and "R$ 1.582,80" in mismatch.detail


def test_no_attachment_blocks() -> None:
    results = rules.evaluate(_facts(attachments=()), TODAY)
    assert results[0].code == "NO_ATTACHMENT"
    assert results[0].blocks_release


def test_invoice_from_another_issuer() -> None:
    attachment = rules.AttachmentFacts(
        id=uuid.uuid4(),
        role="INVOICE",
        name="nota.xml",
        read_kind="XML",
        read_amount=Decimal("2374.20"),
        read_tax_id=OTHER_CNPJ,
        read_due_date=None,
    )
    assert "ATTACHMENT_TAX_ID" in _codes(
        rules.evaluate(_facts(attachments=(attachment,)), TODAY)
    )


def test_pix_in_someone_else_name_and_pending_supplier() -> None:
    supplier = rules.SupplierFacts(
        tax_id=SUPPLIER, status="PENDING", pix_key_type="CPF", pix_key="529.982.247-25"
    )
    codes = _codes(rules.evaluate(_facts(supplier=supplier), TODAY))
    assert "PAYEE_MISMATCH" in codes
    assert "SUPPLIER_PENDING" in codes


def test_late_notice() -> None:
    late = rules.evaluate(_facts(due_date=datetime.date(2026, 10, 28)), TODAY)
    notice = next(result for result in late if result.code == "LATE_NOTICE")
    assert notice.severity == rules.ATTENTION
    assert "2 dias úteis" in notice.detail
    past = rules.evaluate(_facts(due_date=datetime.date(2026, 10, 20)), TODAY)
    assert (
        "depois do vencimento"
        in next(result for result in past if result.code == "LATE_NOTICE").detail
    )


def test_installments_that_do_not_add_up() -> None:
    others = tuple(
        rules.OtherTitle(
            id=uuid.uuid4(),
            number=40 + number,
            unit_name="TOLEDO-PR",
            installment_number=number,
            installment_count=3,
            amount=Decimal("791.40"),
            status="RECEIVED",
        )
        for number in (1, 2)
    )
    ok = rules.evaluate(_facts(same_document=others), TODAY)
    assert "INSTALLMENTS_SUM" not in _codes(ok)
    wrong = rules.evaluate(
        _facts(same_document=others, purchase_total=Decimal("3000.00")), TODAY
    )
    assert "INSTALLMENTS_SUM" in _codes(wrong)


def test_estimate_without_invoice_after_tolerance() -> None:
    estimate = _facts(
        kind="ESTIMATE",
        status="ESTIMATE_OPEN",
        estimate_until=datetime.date(2026, 10, 15),
        attachments=(),
    )
    assert "ESTIMATE_WITHOUT_INVOICE" in _codes(
        rules.evaluate(estimate, datetime.date(2026, 10, 21))
    )
    assert "ESTIMATE_WITHOUT_INVOICE" not in _codes(
        rules.evaluate(estimate, datetime.date(2026, 10, 20))
    )
    # An estimate is never asked for attachments.
    assert "NO_ATTACHMENT" not in _codes(rules.evaluate(estimate, TODAY))


def test_payroll_nature_is_flagged() -> None:
    assert "PAYROLL_NATURE" in _codes(
        rules.evaluate(_facts(account_code="2.01"), TODAY)
    )


def test_nfe_xml_reads_installments_issue_date_and_issuer() -> None:
    xml = f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe>
      <ide><nNF>924</nNF><dhEmi>2026-09-02T10:15:00-03:00</dhEmi></ide>
      <emit><CNPJ>{SUPPLIER}</CNPJ><xNome>JOAO VITOR BUTZGE</xNome></emit>
      <total><ICMSTot><vNF>16228.00</vNF></ICMSTot></total>
      <cobr><dup><nDup>002</nDup><dVenc>2026-10-15</dVenc><vDup>4057.00</vDup></dup>
      <dup><nDup>001</nDup><dVenc>2026-10-02</dVenc><vDup>4057.00</vDup></dup></cobr>
    </infNFe></NFe></nfeProc>""".encode()
    reading = read_invoice_xml(xml)
    assert reading.document_type == "NF"
    assert reading.issue_date == datetime.date(2026, 9, 2)
    assert reading.issuer_name == "JOAO VITOR BUTZGE"
    assert [item.number for item in reading.installments] == [1, 2]
    assert reading.installments[0].amount == Decimal("4057.00")


def test_confirmations_show_what_matched() -> None:
    lines = {line.label: line for line in rules.confirmations(_facts())}
    assert lines["Documento e parcela enviados uma vez só"].state == "OK"
    assert lines["Valor do boleto é o do título"].state == "OK"
    assert lines["CNPJ da nota é o do fornecedor"].state == "UNKNOWN"
    assert lines["Pagamento no nome do próprio favorecido"].state == "OK"
    late = rules.confirmations(_facts(due_date=datetime.date(2026, 10, 28)))
    notice = next(line for line in late if "antecedência" in line.label)
    assert notice.state == "ATTENTION"


def test_payment_batch_workbook() -> None:
    from onyx.ton.payables.payment_batch import BatchRow, build_xlsx

    row = BatchRow(
        due_date=datetime.date(2026, 10, 31),
        number="CP-000031",
        unit="TOLEDO-PR",
        payee="JOAO VITOR BUTZGE",
        tax_id="01.651.656/0001-37",
        method="PIX CNPJ",
        pix_key=SUPPLIER,
        bank="",
        document="NF 924",
        installment="3/4",
        nature="3.02 MANUTENÇÃO",
        amount=Decimal("4057.00"),
        ng_history="TOLEFREIOS · NF 924 3/4",
        boleto_file="",
    )
    content = build_xlsx([row, row])
    assert content[:2] == b"PK"
