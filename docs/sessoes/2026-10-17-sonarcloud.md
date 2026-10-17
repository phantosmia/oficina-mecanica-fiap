# 2026-10-17 — SonarCloud nos 6 microsserviços

## Contexto / pedido original

Continuação da sessão de [2026-10-10](2026-10-10-servico-orcamento.md). A ordem sugerida lá começava pela justificativa da saga no README e pelo diagrama geral da arquitetura. A usuária preferiu começar pelo **SonarCloud** (etapa 5 do `docs/proximos-passos.md`), que dependia dela: criar a organização e gerar o token.

## O que foi entregue

Um PR por repositório, todos com CI verde e Quality Gate `OK` na análise do PR:

- [oficina-mecanica-fiap#44](https://github.com/phantosmia/oficina-mecanica-fiap/pull/44) (também a documentação: `docs/testes-carga-ci.md`, README, checklist e este resumo)
- [oficina-mecanica-catalogo#2](https://github.com/phantosmia/oficina-mecanica-catalogo/pull/2)
- [oficina-mecanica-estoque#2](https://github.com/phantosmia/oficina-mecanica-estoque/pull/2)
- [oficina-mecanica-orcamento#2](https://github.com/phantosmia/oficina-mecanica-orcamento/pull/2)
- [oficina-mecanica-pagamento#3](https://github.com/phantosmia/oficina-mecanica-pagamento/pull/3)
- [oficina-mecanica-execucao#2](https://github.com/phantosmia/oficina-mecanica-execucao/pull/2)

Cada PR tem `sonar-project.properties`, um passo de análise no CI depois do pytest (`SonarSource/sonarqube-scan-action@v5`, `fetch-depth: 0`, `sonar.qualitygate.wait=true`) e badges de Quality Gate e cobertura no README. Cobertura medida pelo SonarCloud nos PRs: OS Service 93,6%, Catálogo 96,9%, Estoque 93,6%, Orçamento 91,7%, Pagamento 90,3% e Execução 94,5%. Os números batem com os do pytest.

Configuração fora do código:

- Organização `phantosmia` no SonarCloud, criada pela usuária com o GitHub.
- Os 6 projetos (`phantosmia_<repositório>`, públicos) foram criados pela API, e a branch principal de cada um foi renomeada de `master` para `main`.
- Secret `SONAR_TOKEN` nos 6 repositórios. O token também fica local em `oficina-mecanica-fiap/.sonar_token`, que agora está no `.gitignore`.

## Decisões tomadas e por quê

- **Trial do plano pago aceito**: a organização veio com `subscription: PAID`. A usuária confirmou que é um *free trial* que cai sozinho para o Free em 31/10. O Free cobre repositório público, então nada deve quebrar no downgrade. Vale conferir os badges depois dessa data.
- **Projetos criados pela API, não pelo import do GitHub**: assim a análise automática do SonarCloud não fica ligada. Se ficasse, o SonarCloud recusaria a análise vinda do CI, que é a que lê o `coverage.xml`. O custo é não ter o projeto ligado ao repositório no GitHub, mas a análise de PR funcionou mesmo assim.
- **O CI falha com o Quality Gate** (`qualitygate.wait`), e o passo não é pulado quando falta o token. Assim o check pode virar obrigatório na proteção da `main`, que é o próximo item.
- **Cobertura com a raiz como único `source`** nos 5 serviços que medem `app` e `scripts`. Com `--cov=app --cov=scripts`, o `coverage.xml` tem um `<source>` por pasta, e o SonarCloud registrava `Cannot resolve the file path '__init__.py'`. O efeito era só um `__init__.py` vazio por repositório, mas o log ficava com um ERROR. Duas tentativas foram descartadas:
  - `relative_files = true` não muda nada nesse caso.
  - `include` sem `source` deixa de fora arquivos que nenhum teste importa (por exemplo `app/outbox_relay.py` do Catálogo, 0% coberto). Isso esconderia código sem teste.

  A versão final (`source = ["."]` + `omit`) dá o mesmo relatório arquivo a arquivo e os mesmos totais em todos os serviços.

## Pendências para a próxima sessão

- Fazer o merge dos 6 PRs e conferir a primeira análise da `main` (os badges só mostram valor depois disso).
- Proteção da `main` nos 6 repositórios: PR obrigatório e checks obrigatórios (testes com o Sonar, build).
- O resto das etapas 5 a 7 continua como estava em [2026-10-10](2026-10-10-servico-orcamento.md): justificativa da saga no README, diagrama geral, Terraform/deploy, New Relic, Postman, vídeo e PDF.
