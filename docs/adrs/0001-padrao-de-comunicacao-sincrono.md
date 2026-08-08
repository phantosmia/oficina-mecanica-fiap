# ADR-0001: Padrão de comunicação síncrono via REST/HTTP

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-04-21 |

## Contexto

`app/service_orders` é o contexto central do sistema: orquestra diagnóstico, orçamento, aprovação com baixa de estoque, finalização e entrega, e para isso precisa fazer *lookups* cruzados em outros contextos de domínio (`clients`, `vehicles`, `service_catalog`, `parts`). Além disso, o envio de e-mail de orçamento (`send-quote`) é um efeito colateral de uma requisição administrativa. Era preciso decidir como esses componentes conversam entre si e como a API se expõe para o mundo externo.

## Decisão

Adotar um **monólito modular** (Clean Architecture por contexto de domínio) que se comunica **em-processo**, por chamadas diretas a interfaces (`IXxxRepository`, casos de uso), e expor um único **contrato HTTP síncrono** (FastAPI/REST) para o mundo externo — sem mensageria (fila, broker, pub/sub) e sem chamadas de rede entre contextos internos.

Concretamente:

- `app/service_orders` acessa clientes, veículos, catálogo e peças através da própria interface de repositório (não via HTTP interno nem por importar módulos de outro contexto diretamente), mantendo a regra de dependência `controller -> application -> domain`.
- O envio de e-mail (`app/shared/email.py` + `smtp_notifier.py`) acontece de forma síncrona, dentro da mesma requisição que dispara o orçamento — não há fila de mensageria entre a API e o envio de e-mail.
- Toda comunicação externa (admin e cliente) acontece por request/response HTTP; não há webhook, WebSocket ou streaming.

## Alternativas consideradas

- **Microsserviços com REST interno**: cada contexto de domínio como serviço independente, comunicando-se por HTTP. Descartado para o escopo do MVP: multiplicaria a complexidade operacional (deploy, descoberta de serviço, tratamento de falha de rede) sem necessidade real de escalar ou deployar contextos de forma independente.
- **Arquitetura orientada a eventos (mensageria)**: um broker (SQS/RabbitMQ) desacoplando, por exemplo, o envio de e-mail da requisição de `send-quote`, ou propagando mudanças de status de OS como eventos. Descartado por adicionar um componente de infraestrutura extra (broker, filas, DLQ) sem que o volume ou os requisitos de resiliência do MVP justifiquem o custo.
- **Chamadas HTTP internas entre contextos dentro do mesmo processo**: rejeitado por ser estritamente pior que uma chamada de método direto — mesma ausência de desacoplamento real, com o custo de serialização e latência de uma chamada de rede.

## Consequências

- Simplicidade operacional: não há broker, fila ou DLQ para operar, monitorar ou versionar — coerente com o escopo de MVP acadêmico.
- Escalabilidade é tratada no nível do **processo inteiro** (réplicas do `Deployment` via HPA — ver [ADR-0002](0002-uso-de-hpa-para-escalabilidade.md)), não por contexto de domínio individualmente; não é possível hoje escalar `service_orders` separado de `clients`, por exemplo.
- O envio de e-mail acontece inline com a requisição de `send-quote`: se o SMTP estiver lento ou fora do ar, a requisição administrativa sofre esse atraso/erro diretamente (mitigado por ser uma ação pontual, não o caminho quente da API).
- Se o sistema crescer a ponto de contextos precisarem de ciclos de deploy ou escala independentes, ou de comunicação verdadeiramente assíncrona (ex.: reprocessar envios de e-mail com retry), esta decisão precisa ser revisitada.
