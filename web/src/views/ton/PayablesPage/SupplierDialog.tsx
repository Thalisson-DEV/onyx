"use client";

import { SideModal } from "@/views/ton/components/kit";
import { useState } from "react";
import { Button, InputTypeIn, Text } from "@opal/components";
import { SvgAlertTriangle } from "@opal/icons";
import {
  PIX_TYPES,
  SUPPLIER_KINDS,
  errorText,
  maskTaxId,
  payablesJson,
  validTaxId,
  type PayablesContext,
  type PixKeyType,
  type Supplier,
  type SupplierInput,
  type SupplierKind,
} from "@/lib/ton/payables";
import { PatternField } from "@/views/ton/components/pattern";
import { Segmented, Select } from "@/views/ton/PayablesPage/fields";

type PaymentMode = "PIX" | "BANK";

interface SupplierDialogProps {
  /** null: a new supplier. */
  supplier: Supplier | null;
  context: PayablesContext;
  /** Read from an invoice, for a supplier not registered yet. */
  initialTaxId?: string;
  initialName?: string;
  onClose: () => void;
  onSaved: (supplier: Supplier) => void;
}

/** Register or correct a supplier. A unit's new supplier waits for finance. */
export default function SupplierDialog({
  supplier,
  context,
  initialTaxId,
  initialName,
  onClose,
  onSaved,
}: SupplierDialogProps) {
  const startTaxId = maskTaxId(supplier?.tax_id ?? initialTaxId ?? "");
  const [taxId, setTaxId] = useState(startTaxId);
  const [legalName, setLegalName] = useState(
    supplier?.legal_name ?? initialName ?? ""
  );
  const [tradeName, setTradeName] = useState(supplier?.trade_name ?? "");
  const [kind, setKind] = useState<SupplierKind>(
    supplier?.kind ??
      (startTaxId.replace(/\D/g, "").length === 11 ? "PERSON" : "COMPANY")
  );
  const [accountId, setAccountId] = useState(
    supplier?.default_account_id ?? ""
  );
  const [mode, setMode] = useState<PaymentMode>(
    supplier?.bank_account && !supplier.pix_key ? "BANK" : "PIX"
  );
  const [pixType, setPixType] = useState<PixKeyType>(
    supplier?.pix_key_type ??
      (startTaxId.replace(/\D/g, "").length === 11 ? "CPF" : "CNPJ")
  );
  const [pixKey, setPixKey] = useState(
    supplier?.pix_key ?? (supplier ? "" : startTaxId)
  );
  const [bankCode, setBankCode] = useState(supplier?.bank_code ?? "");
  const [agency, setAgency] = useState(supplier?.bank_agency ?? "");
  const [account, setAccount] = useState(supplier?.bank_account ?? "");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const digits = taxId.replace(/\D/g, "");
  const taxIdError =
    submitted || digits.length >= 11
      ? digits.length !== 11 && digits.length !== 14
        ? "Digite os 11 dígitos do CPF ou os 14 do CNPJ."
        : !validTaxId(digits)
          ? "Os dígitos verificadores não conferem."
          : null
      : null;
  const pixDigits = pixKey.replace(/\D/g, "");
  const pixOwnerWarning =
    mode === "PIX" &&
    (pixType === "CPF" || pixType === "CNPJ") &&
    pixDigits.length >= 11 &&
    digits.length >= 11 &&
    pixDigits !== digits;
  const paymentReady =
    mode === "PIX"
      ? pixKey.trim().length > 0
      : [bankCode, agency, account].every((value) => value.trim());
  const ready =
    validTaxId(digits) && legalName.trim().length >= 2 && paymentReady;

  async function save() {
    setSubmitted(true);
    if (!ready) return;
    setBusy(true);
    setFailure(null);
    const body: SupplierInput = {
      tax_id: digits,
      legal_name: legalName.trim(),
      trade_name: tradeName.trim() || null,
      kind,
      default_account_id: accountId || null,
      pix_key_type: mode === "PIX" ? pixType : null,
      pix_key: mode === "PIX" ? pixKey.trim() : null,
      bank_code: mode === "BANK" ? bankCode.trim() : null,
      bank_agency: mode === "BANK" ? agency.trim() : null,
      bank_account: mode === "BANK" ? account.trim() : null,
    };
    try {
      onSaved(
        supplier
          ? await payablesJson<Supplier>(
              "PUT",
              `/suppliers/${supplier.id}`,
              body
            )
          : await payablesJson<Supplier>("POST", "/suppliers", body)
      );
    } catch (error) {
      setFailure(errorText(error, "Não foi possível salvar o fornecedor."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SideModal open onOpenChange={(open) => !open && !busy && onClose()}>
      <SideModal.Content width="md">
        <SideModal.Header
          title={supplier ? "Fornecedor" : "Novo fornecedor"}
          description={
            context.is_finance
              ? "O CPF ou CNPJ identifica o fornecedor. O pagamento vai sempre para o próprio favorecido."
              : "O financeiro aprova o cadastro antes do primeiro pagamento. Você já pode enviar a conta."
          }
          onClose={() => !busy && onClose()}
        />
        <SideModal.Body>
          <div className="w-full tp-form-section">
            <PatternField
              label="CPF ou CNPJ"
              span={6}
              note={taxIdError}
              noteTone="error"
              filled={Boolean(initialTaxId) && taxId === startTaxId}
            >
              <InputTypeIn
                value={taxId}
                inputMode="numeric"
                placeholder="00.000.000/0000-00"
                aria-label="CPF ou CNPJ"
                variant={
                  supplier ? "readOnly" : taxIdError ? "error" : "primary"
                }
                onChange={(event) => {
                  const next = maskTaxId(event.target.value);
                  // The usual PIX key is the payee's own CPF or CNPJ.
                  if (!pixKey || pixKey === taxId) {
                    setPixKey(next);
                    setPixType(
                      next.replace(/\D/g, "").length > 11 ? "CNPJ" : "CPF"
                    );
                  }
                  setTaxId(next);
                }}
              />
            </PatternField>
            <PatternField label="Tipo" span={6}>
              <Select
                value={kind}
                label="Tipo"
                placeholder="Tipo"
                searchAbove={99}
                options={SUPPLIER_KINDS}
                onChange={(value) => setKind(value as SupplierKind)}
              />
            </PatternField>
            <PatternField
              label="Razão social ou nome completo"
              note={
                submitted && legalName.trim().length < 2
                  ? "Informe o nome como está na nota."
                  : null
              }
              noteTone="error"
              filled={Boolean(initialName) && legalName === initialName}
            >
              <InputTypeIn
                value={legalName}
                maxLength={300}
                aria-label="Razão social"
                placeholder="Como está na nota fiscal"
                onChange={(event) => setLegalName(event.target.value)}
              />
            </PatternField>
            <PatternField
              label="Nome do dia a dia"
              span={6}
              note="Opcional; ajuda na busca"
            >
              <InputTypeIn
                value={tradeName}
                maxLength={300}
                aria-label="Nome do dia a dia"
                placeholder="Ex.: Tolefreios"
                onChange={(event) => setTradeName(event.target.value)}
              />
            </PatternField>
            <PatternField
              label="Natureza padrão"
              span={6}
              note="Opcional; sugerida nas contas"
            >
              <Select
                value={accountId}
                label="Natureza padrão"
                placeholder="Escolha a natureza"
                options={context.accounts.map((item) => ({
                  value: item.id,
                  label: `${item.code} · ${item.label}`,
                }))}
                onChange={setAccountId}
              />
            </PatternField>
            <PatternField label="Como pagar">
              <Segmented
                label="Forma de pagamento"
                value={mode}
                options={[
                  { value: "PIX", label: "PIX" },
                  { value: "BANK", label: "Conta" },
                ]}
                onChange={setMode}
              />
            </PatternField>
            {mode === "PIX" ? (
              <>
                <PatternField label="Tipo da chave" span={4}>
                  <Select
                    value={pixType}
                    label="Tipo da chave"
                    placeholder="Tipo"
                    searchAbove={99}
                    options={PIX_TYPES}
                    onChange={(value) => setPixType(value as PixKeyType)}
                  />
                </PatternField>
                <PatternField
                  label="Chave PIX"
                  span={8}
                  note={submitted && !pixKey.trim() ? "Informe a chave." : null}
                  noteTone="error"
                >
                  <InputTypeIn
                    value={pixKey}
                    maxLength={140}
                    aria-label="Chave PIX"
                    placeholder="Chave PIX"
                    variant={submitted && !pixKey.trim() ? "error" : "primary"}
                    onChange={(event) => setPixKey(event.target.value)}
                  />
                </PatternField>
              </>
            ) : (
              <>
                <PatternField label="Banco" span={4}>
                  <InputTypeIn
                    value={bankCode}
                    maxLength={8}
                    inputMode="numeric"
                    aria-label="Banco"
                    placeholder="Ex.: 001"
                    onChange={(event) => setBankCode(event.target.value)}
                  />
                </PatternField>
                <PatternField label="Agência" span={4}>
                  <InputTypeIn
                    value={agency}
                    maxLength={16}
                    aria-label="Agência"
                    placeholder="0000"
                    onChange={(event) => setAgency(event.target.value)}
                  />
                </PatternField>
                <PatternField label="Conta com dígito" span={4}>
                  <InputTypeIn
                    value={account}
                    maxLength={32}
                    aria-label="Conta"
                    placeholder="00000-0"
                    onChange={(event) => setAccount(event.target.value)}
                  />
                </PatternField>
              </>
            )}
            {pixOwnerWarning && (
              <div
                className="tp-alert"
                data-tone="warning"
                style={{ gridColumn: "1 / -1" }}
              >
                <SvgAlertTriangle
                  size={16}
                  className="text-status-warning-05 shrink-0"
                />
                <Text font="secondary-body" color="text-04">
                  Esta chave não é o CPF/CNPJ do fornecedor. O pagamento precisa
                  ir para o próprio favorecido.
                </Text>
              </div>
            )}
            {failure && (
              <div style={{ gridColumn: "1 / -1" }}>
                <Text as="p" font="secondary-body" color="status-error-05">
                  {failure}
                </Text>
              </div>
            )}
          </div>
        </SideModal.Body>
        <SideModal.Footer>
          <Button prominence="secondary" disabled={busy} onClick={onClose}>
            Cancelar
          </Button>
          <Button disabled={busy} onClick={() => void save()}>
            {busy
              ? "Salvando…"
              : supplier
                ? "Salvar"
                : context.is_finance
                  ? "Cadastrar"
                  : "Enviar para aprovação"}
          </Button>
        </SideModal.Footer>
      </SideModal.Content>
    </SideModal>
  );
}
