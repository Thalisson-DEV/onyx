## 1. Insumos

- [ ] 1.1 Pedir contratos, editais, aditivos e apostilamentos dos contratos operacionais; identificar gestor nominal de cada um
- [ ] 1.2 Começar por Mossoró-RN 02/2023 (caso-padrão §4.1)

## 2. Modelo

- [ ] 2.1 `ContractMasterVersion` com os 5 blocos (schemas Pydantic) e evidência por campo
- [ ] 2.2 `ContractEvent` append-only e derivação de valor/prazo vigente
- [ ] 2.3 Completude por bloco/regra e resposta de bloqueio declarado
- [ ] 2.4 Mapeamentos versionados contrato ↔ unidade ↔ tomador

## 3. API e UI

- [ ] 3.1 Endpoints de cadastro, eventos, completude e vínculos com ACL por contrato
- [ ] 3.2 `ContractsPage`: lista, ficha, completude, documentos, eventos, vínculos
- [ ] 3.3 Sugestão assistida a partir de PDF marcada "proposto — confirmar"
- [ ] 3.4 Ferramentas do especialista CONTRATOS (leitura do cadastro)

## 4. Validação

- [ ] 4.1 Testes de derivação de valor vigente, completude e vínculos
- [ ] 4.2 Cadastrar Mossoró 02/2023 com a Luyla e conferir com o §4.1
- [ ] 4.3 Atualizar cobertura (especialista CONTRATOS) e `openspec/roadmap.md`
