# Coleção Postman

Fluxo completo de uma ordem de serviço pelos 6 microsserviços e as compensações da saga.

| Arquivo | Conteúdo |
|---|---|
| `oficina-mecanica.postman_collection.json` | A coleção |
| `local.postman_environment.json` | URLs do `docker compose up` (portas 8000 a 8005) |
| `homologacao.postman_environment.json` | URLs do ambiente na AWS (preencher, ver abaixo) |

No Postman: **Import** dos três arquivos e escolha do ambiente no canto superior direito.

A senha do admin não vem nos arquivos. Preencha `admin_password` no ambiente: no `local`, é o padrão do README do OS Service; no `homologacao`, é o valor de `ADMIN_PASSWORD` do ambiente, que enquanto não tiver secret próprio também é o padrão.

## O que tem na coleção

| Pasta | O que faz |
|---|---|
| 0. Saúde dos serviços | `GET /health` nos 6 serviços, para conferir as URLs |
| 1. Preparação | Login do admin e escolha do serviço e da peça do catálogo (Revisão de freios e Disco de freio, dos dados de exemplo) |
| 2. Fluxo completo | Abertura → diagnóstico → reserva → orçamento → aprovação pelo link → pagamento → baixa → reparo → entrega, e a consulta do cliente com o token da Lambda |
| 3. Compensações | Orçamento recusado (a reserva é liberada) e estoque insuficiente (a OS é cancelada) |

Detalhes que valem para todas as pastas:

- **Login automático.** O token de admin emitido pelo OS Service vale nas rotas de admin dos 6 serviços. Se a variável `admin_token` estiver vazia, a coleção faz o login sozinha. Quando o token expirar, rode **Login admin** de novo.
- **A saga é assíncrona.** Cada passo que depende dela é uma requisição **Aguardar ...**, que repete sozinha a cada poucos segundos até o status esperado (no Collection Runner e no Newman). Se você estiver enviando à mão, é só reenviar.
- **Variáveis.** As requisições guardam nas variáveis da coleção o que as próximas precisam (`order_id`, `saga_id`, `quote_token`, `checkout_url`...). Por isso cada pasta deve rodar em ordem.

## Pagamento: o único passo manual

Na pasta **2.3**, **Ver cobrança e link de pagamento** imprime o `checkout_url` no console. Abra o link no navegador e pague no sandbox do Mercado Pago, entrando antes com o **comprador de teste**. O README do [Pagamento](https://github.com/phantosmia/oficina-mecanica-pagamento) explica como fazer isso. Enquanto isso, **Aguardar pagamento confirmado** espera até 6 minutos. Para não esperar a reconciliação periódica, use **Sincronizar cobrança**.

## Ambiente `homologacao` (AWS)

Na AWS, só OS Service, Orçamento e Pagamento têm LoadBalancer público. Catálogo, Estoque e Execução ficam dentro do cluster e são acessados por `kubectl port-forward`, nas mesmas portas do Compose:

```bash
aws eks update-kubeconfig --name oficina-mecanica-fiap-homologacao --region us-east-1
kubectl port-forward -n oficina-catalogo svc/catalogo-api 8001:8000 &
kubectl port-forward -n oficina-estoque svc/estoque-api 8002:8000 &
kubectl port-forward -n oficina-execucao svc/execucao-api 8003:8000 &
```

Os endereços públicos mudam a cada recriação do ambiente. Para pegar os atuais e preencher `os_url`, `orcamento_url`, `pagamento_url` e `auth_url` no ambiente:

```bash
kubectl get svc -A | grep LoadBalancer
aws apigatewayv2 get-apis --query 'Items[].ApiEndpoint' --output text
```

`auth_url` é o API Gateway da Lambda de autenticação via CPF. A Lambda não roda no Compose, então no ambiente `local` a pasta **2.5** não funciona.

## Pela linha de comando (Newman)

Todas as pastas, exceto as que dependem do pagamento manual:

```bash
npx newman run postman/oficina-mecanica.postman_collection.json \
  -e postman/local.postman_environment.json \
  --folder "0. Saúde dos serviços" --folder "1. Preparação" \
  --folder "2.1 Abertura e diagnóstico" --folder "2.2 Aprovação do orçamento" \
  --folder "3.1 Orçamento recusado (libera a reserva)" --folder "3.2 Estoque insuficiente (cancela a OS)"
```

Contra o `homologacao` em 2026-10-24: 50 requisições e 69 asserções, sem falhas.
