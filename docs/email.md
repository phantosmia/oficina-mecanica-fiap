# Notificações por E-mail

Desde a Fase 4, três microsserviços enviam e-mail ao cliente, cada um sobre a parte do fluxo que é dele:

| Serviço | Quando | Assunto |
|---|---|---|
| [Orçamento](https://github.com/phantosmia/oficina-mecanica-orcamento) | Orçamento gerado depois do diagnóstico | `[OS #n] Orçamento disponível para aprovação` (com o link para aprovar ou recusar) |
| Orçamento | Cliente aprovou ou recusou | `[OS #n] Orçamento aprovado` / `Orçamento recusado` |
| [Pagamento](https://github.com/phantosmia/oficina-mecanica-pagamento) | Cobrança criada no Mercado Pago | `[OS #n] Link de pagamento` |
| Pagamento | Pagamento confirmado | `[OS #n] Pagamento confirmado` |
| OS Service (este repositório) | Reparo concluído (`finalizada`) | `[OS #n] Serviço finalizado — veículo pronto para retirada` |

Os três usam as mesmas variáveis SMTP abaixo e enviam **depois** de gravar a mudança, numa tentativa única: uma falha de e-mail não desfaz nada nem trava a saga. Os links também ficam disponíveis para o admin (`GET /quotes/{order_id}` no Orçamento e `GET /charges/{order_id}` no Pagamento).

As notificações são desabilitadas por padrão (`SMTP_ENABLED=false`).

## Ambiente local: caixa de entrada de teste (Mailpit)

No `docker-compose.yml`, os serviços enviam para o **[Mailpit](https://mailpit.axllent.org/)**, um servidor SMTP de desenvolvimento que **não entrega** os e-mails a ninguém: ele os guarda numa caixa de entrada web, em **`http://localhost:8025`**. Assim dá para testar e demonstrar o fluxo inteiro (clicar no link do orçamento, depois no link de pagamento) sem conta SMTP real e sem mandar e-mail para endereços inventados.

O Mailpit é ferramenta de desenvolvimento, como o LocalStack: não existe no deploy do Kubernetes nem muda nada no código (os serviços falam SMTP comum; `SMTP_HOST=mailpit`, porta `1025`, sem autenticação).

## Variáveis de ambiente SMTP

| Variável | Padrão | Descrição |
|---|---|---|
| `SMTP_ENABLED` | `false` | Habilita o envio de e-mails |
| `SMTP_HOST` | `""` | Endereço do servidor SMTP |
| `SMTP_PORT` | `587` | Porta SMTP, geralmente STARTTLS |
| `SMTP_FROM` | `""` | Endereço de origem dos e-mails |
| `SMTP_USERNAME` | `""` | Usuário de autenticação SMTP |
| `SMTP_PASSWORD` | `""` | Senha ou senha de app SMTP |
| `PUBLIC_BASE_URL` | depende do serviço | Endereço público usado nos links dos e-mails (no Orçamento, a página de aprovação; no Pagamento, a URL de retorno do checkout) |

## Provedores compatíveis

| Provedor | `SMTP_HOST` | `SMTP_PORT` |
|---|---|---|
| Gmail | `smtp.gmail.com` | `587` |
| Outlook / Hotmail | `smtp.office365.com` | `587` |
| SendGrid | `smtp.sendgrid.net` | `587` |
| Mailtrap sandbox | `sandbox.smtp.mailtrap.io` | `587` |

No Gmail, é necessário gerar uma senha de app em [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), com 2FA ativo. Não use a senha normal da conta.

Para testes, o Mailtrap é recomendado porque intercepta os e-mails sem entregá-los, permitindo validar templates sem risco de spam.

## Configuração local

Crie um arquivo `.env` na raiz do projeto. Esse arquivo não deve ser commitado.

```env
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM=seuemail@gmail.com
SMTP_USERNAME=seuemail@gmail.com
SMTP_PASSWORD=sua_senha_de_app
PUBLIC_BASE_URL=https://api.sua-oficina.com
```

## Configuração via Docker Compose

O Compose já vem apontando para o Mailpit (âncora `x-aws` no `docker-compose.yml`, usada por todos os serviços). Para enviar por um SMTP real, troque nessa âncora:

```yaml
SMTP_ENABLED: "true"
SMTP_HOST: "smtp.gmail.com"
SMTP_PORT: "587"
SMTP_FROM: "seuemail@gmail.com"
SMTP_USERNAME: "seuemail@gmail.com"
SMTP_PASSWORD: "sua_senha_de_app"
```

Com `SMTP_USERNAME` preenchido, os serviços usam STARTTLS e autenticação; sem ele (caso do Mailpit), enviam sem.
