# Vale Norte Zeev source catalog — human review

Retrieved: 2026-09-23 (America/Sao_Paulo). Environment: `https://nucleo.zeev.it`. Source: the tenant's public Swagger 2.0 contract and a bounded read-only live catalog. This report contains source metadata only. Candidate areas need human review.

## Inventory and identity

The account can start five flows. It can edit and read 35 flow definitions. The startable IDs are a subset of the 35. Thus, 30 other definitions are readable through `flows/edit`. The endpoints answer different access questions; the five-flow result is not the full inventory. No startable service was returned.

Use the tenant-scoped numeric `flowId` (`id` on the startable route) as the canonical external flow ID. Keep `flowUid`/`uid` and `flowVersion`/`version` as secondary metadata. Do not key by name. The tenant contract does not establish UID behavior across copied or imported applications.

All 35 form schemas and 35 task designs were readable. None failed. The schemas have 916 fields. The designs have 401 elements. `Active` was true for every editable flow. `Deployed` below reflects the returned `deploy` flag. A false flag does not by itself prove that an old instance cannot exist.

| Flow ID | Source flow name | Startable | Deployed | Fields |
| ---: | --- | :---: | :---: | ---: |
| 123 | CCP - Liberações Financeiras | No | Yes | 50 |
| 121 | Controladoria - Aprovações e Liberações | No | Yes | 55 |
| 148 | Cópia NTI - VALE NORTE - Pedido de Liberações Financeiras | No | Yes | 81 |
| 143 | Copy of NC3 - Manutenção | No | No | 15 |
| 145 | Copy of NÚCLEO - Chamados de TI | No | No | 23 |
| 150 | Copy of VALE NORTE - Pedido de Liberações Financeiras | No | No | 83 |
| 115 | NC3 - Abertura de Chamados | No | No | 8 |
| 146 | NC3 - Advertência e Suspensão (TESTE) | No | No | 5 |
| 127 | NC3 - Central de Comunicados | No | Yes | 9 |
| 137 | NC3 - Controle de Ressarcimento de Mercadorias | No | Yes | 23 |
| 120 | NC3 - Desligamento de Funcionários | No | Yes | 11 |
| 139 | NC3 - Manutenção | No | Yes | 15 |
| 107 | NC3 - Recrutamento e Seleção | No | Yes | 16 |
| 138 | NC3 - Solicitação de Empréstimo de Mercadoria | No | Yes | 17 |
| 119 | NC3 - Solicitação de Pagamento | No | Yes | 35 |
| 136 | NÚCLEO - Análise Jurídica de Contratos e Assinaturas | Yes | Yes | 29 |
| 140 | NÚCLEO - Chamados de TI | Yes | Yes | 27 |
| 128 | NÚCLEO - Feedback - Sistema Zeev | No | Yes | 15 |
| 144 | NÚCLEO - Migração Entre Empresas | No | Yes | 16 |
| 130 | NUCLEO - Pedido de Liberações Financeiras | No | Yes | 40 |
| 126 | NÚCLEO - Solicitação de Certidões | No | Yes | 13 |
| 149 | NÚCLEO - Solicitações da Gerência | Yes | Yes | 10 |
| 154 | NVC - Pedido de Liberações Financeiras | Yes | Yes | 68 |
| 102 | PoC - Vale (imported application) (aplicativo importado) | No | No | 78 |
| 122 | Recrutar e Selecionar Talentos | No | No | 13 |
| 147 | STAND BY - NÚCLEO - Planilha de Solicitações Financeiras - Zeev | No | No | 2 |
| 104 | Standby - Processo de Aprovação de Adiantamento | No | No | 3 |
| 112 | TESTE - NC3 - Solicitação de Autorização | No | No | 14 |
| 117 | TESTE - NÚCLEO - Autorização para saída eventual | No | No | 0 |
| 118 | TESTE - NÚCLEO - Contrato Social e Alteração | No | No | 8 |
| 135 | TESTE - NÚCLEO - Recrutamento e Seleção | No | No | 20 |
| 116 | TESTE - VALE NORTE - Abertura de Chamado de TI | No | No | 0 |
| 134 | TESTE - VALE NORTE - Recrutamento e Seleção | No | No | 21 |
| 141 | VALE NORTE - Envio das Contas a Pagar | No | No | 5 |
| 108 | VALE NORTE - Pedido de Liberações Financeiras | Yes | Yes | 88 |

## Form structure and field types

Fields expose `fieldId`, technical `name`, `label`, `typeName`, `required`, `attributes`, `groupName`, and group, row, column, and field order. The catalog keeps these structural fields. It does not keep `actionScript` or form values. `attributes` become catalog options only for choice fields.

| Source kind | Fields |
| --- | ---: |
| TEXT | 435 |
| CHOICE | 182 |
| FILE | 118 |
| NUMBER | 112 |
| DATE | 57 |
| UNKNOWN | 12 |

The raw `typeName` distribution is: Texto 307; Arquivo 112; Caixa de seleção 105; Área de texto 105; Moeda 90; Data 55; Lista de seleção 39; Lista de seleção única 38; Número 20; Campo escondido 8; CPF 6; Arquivo - Visualizador 6; CNPJ 5; Placa 4; Texto rico 3; NPS 3; Email 2; Somente números 2; and one each of Somente nÃºmeros, Data e Hora, CEP - Seach and Fill, Telefone, Telefone Celular, and Hora. The malformed spelling is preserved from the source.

File fields, single and other selection lists, checkboxes, rich text, currency, date/time, and grouped fields occur. No `Tabela` field type occurred. Some section names include “Tabela”; that alone does not prove a repeating table. No source boolean, user/person, or team field type occurred in these 35 designs. Unknown types remain unchanged in the catalog.

## Source relationships and capability matrix

The public contract calls startable flows “applications”. An editable application has a flow ID, UID, and version. A service can contain a flow reference, but this tenant returned zero startable services. An instance contains a `flow` reference and an optional `service` reference. It can contain form fields and task instances. A task instance contains a task descriptor. These are separate source structures.

| Source read capability | Contract | Live result |
| --- | --- | --- |
| Startable flows and editable flow metadata | Documented | Validated: 5 and 35 |
| Form design | Documented | Validated: 35 of 35 |
| Bounded instance report | Documented | Validated: 5 recent instances |
| Pending assignments | Documented | Validated: endpoint returned zero for this account |
| Finished tasks and timestamps in instance report | Documented | Validated in sample |
| Task assignee and team | Documented | Response keys observed; all sampled `assignees` were null |
| User detail | Documented | One single-record read validated |
| Team detail | Documented | One single-record read validated |
| Position/role detail | Documented | One single-record read validated |
| Maintenance group detail | Documented | Not live validated |
| Attachment download | No public read path found | Not validated; reference only |

The user contract exposes ID, name, email, username, and active state. The team contract exposes ID, code, name, parent, and active state. The position contract exposes ID, code, name, parent, and active state. BE-004B did not list or store people or organization datasets.

## Task design, instance, and attachment structure

The 401 design elements comprise 277 `Tarefa Humana`, 46 `Mensagem`, 35 `Início`, 25 `Relógio`, 10 `Tarefa de Regra de Negócio`, seven `Tarefa de Serviço`, and one `Subprocesso`. The catalog keeps element ID, title, source type, order, page, business-hours flag, timeout, and safe counts. The `users` field appeared as null in 217 elements, an array in 138, and a string in 46. The catalog records the representation and array length, never its contents. A design element ID is scoped to its flow until cross-flow uniqueness is proven.

The one-day, one-page sample had five instances. Each had a numeric ID and UUID, flow ID/UID/version, active flag, start time, optional end time, optional last finished task time, requester object, form field array, and embedded task array. Requester structure had ID, name, email, username, team, and position keys. These personal values were discarded. The five instances contained 14 task records, from two to four per instance. One selected detail request exposed three `formFields` entries with `id`, `name`, `row`, and string `value` keys. The values were discarded immediately.

Task instances had numeric ID, active flag, start and optional end and expected end times, result, alias, optional executor, optional assignees, and a task descriptor with ID, name, type, timeout, and business-hours flag. Six sampled task records had an executor object. All 14 sampled `assignees` fields were null. Completed tasks provide a bounded task history view. The public API may have more history, but BE-004B did not validate an event log.

The Swagger search for file, files, attachment, attachments, document, download, content, binary, and upload found only two `/api/2/files` routes. Both are POST write operations: document creation and task attachment upload. The instance contract defines `formFields[].openUrl`, and the tenant has 118 file-type fields. The selected live detail returned form field structures, with no `openUrl` key in that sample. No public file-content read route was found. Attachment read capability is **REFERENCE_ONLY**. A file-field value is a possible source reference; its exact encoding and download path need client confirmation. No open URL or file was requested.

## Provisional candidate areas

The classifier uses only flow names, section names, and field labels. Counts overlap: Financeiro 13, Compras 10, RH 8, TI 7, Contratos 6, Gerência 5, and Frota 4. Six flows have no keyword candidate. No Medição, Operações, or Compliance keyword candidate appeared. A label can cause a false positive; for example, a recruitment flow may contain a finance label. These counts are review prompts, not domain assignments.

| Candidate flow IDs | Why they may matter | Structural evidence | Unknown to confirm |
| --- | --- | --- | --- |
| 121, 123 | Controladoria and financial release work may feed TON finance views. | Names; 55 and 50 fields; supplier, total value, payment date, invoice, and due-date labels. | Which is current, and how do CCP and Controladoria differ? |
| 108, 130, 154 | Payment release flows may hold request and approval structures. | Names; 88, 40, and 68 fields; supplier, total value, payment method, and proof sections. | Which company and routine owns each variant? |
| 119 | Payment requests may precede the release flows. | Name; 35 fields; payment, supplier, invoice, and planned payment labels. | Does this feed controladoria or another team? |
| 136 | Contract review may identify document references for later comparison. | Name; 29 fields; “Dados do contrato”, “Parecer Jurídico”, and “Contrato Assinado” sections. | Where are signed contract files stored and read? |
| 137 | Merchandise reimbursement may affect payment or supplier follow-up. | Name; 23 fields; supplier, invoice/order, total, and reimbursed value labels. | Is this part of TON's target routine? |
| 141 | Accounts-payable sending may bridge Zeev and external files. | Name; five fields; due-date label; “Tabela” section name. | Is this flow active despite `deploy=false`? What file or system receives it? |
| 147 | A named financial spreadsheet flow may explain Excel handoffs. | Name; two fields, including an “Arquivo” label; `deploy=false`. | Is it a retired test or a real file source? |

Flows 148 and 150 have copy names. Flow 148 is deployed and flow 150 is not. They are possible variants of 108, but no equivalence is established. Test, copy, imported, and standby names require explicit operational confirmation before synchronization scope is selected.

## Questions requiring client confirmation

1. Which financial-release flow IDs are used in the current controladoria routine?
2. What is the difference between the CCP, NÚCLEO, NVC, and VALE NORTE payment variants?
3. Does any Zeev flow represent monthly financial closing? If yes, which flow ID?
4. Are flows 141 and 147 active sources despite their `deploy=false` flags?
5. Which flow produces data that Luyla later receives in Excel or PDF?
6. Where do signed contracts and payment proof files originate? How can authorized users read them?
7. Are copied and test flows historical evidence, or can they be excluded from future synchronization?
8. Which task assignee or team details are required for operational reporting?

## Unknowns and BE-004C readiness

This catalog is sufficient to design a candidate synchronization plan. It does not prove the final synchronization scope. Instance ID, UID, flow ID, task instance ID, and task design ID exist. The report contract offers start, end, and last-finished-task date filters. It does not prove that any one filter captures every form edit, assignment change, or attachment update. Historical backfill range, current flow variants, file access, and source-to-file relationships need confirmation. Luyla's files need a separate analysis slice.

## Live safety record

The final full run made one `POST /api/2/tokens`; one each of `GET /api/2/requests/flows`, `GET /api/2/flows/edit`, and `GET /api/2/requests/services`; 35 `GET /api/2/flows/{flowid}/design/form`; 35 `GET /api/2/flows/{flowid}/design/elements`; one each of `GET /api/2/instances/report`, `GET /api/2/instances/{instanceid}`, and `GET /api/2/assignments`; and one each of `GET /api/2/users/{userid}`, `GET /api/2/teams/{teamid}`, and `GET /api/2/positions/{positionid}`. These are 80 calls in total. Path templates contain no personal query values. The run saw zero HTTP 429 responses, zero catalog warnings, and zero business mutation calls. No real field value, personal record, raw instance payload, token, or credential was saved in this report or the catalog.
