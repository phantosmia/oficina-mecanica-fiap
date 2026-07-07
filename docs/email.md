# Notificações por E-mail

A API envia e-mails automaticamente ao cliente nas transições de status que geram comunicação.

| Evento | Assunto enviado |
|---|---|
| Orçamento enviado (`aguardando_aprovacao`) | Orçamento disponível para aprovação |
| Orçamento aprovado (`em_execucao`) | Orçamento aprovado: serviço iniciado |
| Orçamento recusado (`recusada`) | Orçamento recusado |
| OS finalizada (`finalizada`) | Veículo pronto para retirada |

As notificações são desabilitadas por padrão (`SMTP_ENABLED=false`).

## Variáveis de ambiente SMTP

| Variável | Padrão | Descrição |
|---|---|---|
| `SMTP_ENABLED` | `false` | Habilita o envio de e-mails |
| `SMTP_HOST` | `""` | Endereço do servidor SMTP |
| `SMTP_PORT` | `587` | Porta SMTP, geralmente STARTTLS |
| `SMTP_FROM` | `""` | Endereço de origem dos e-mails |
| `SMTP_USERNAME` | `""` | Usuário de autenticação SMTP |
| `SMTP_PASSWORD` | `""` | Senha ou senha de app SMTP |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | URL pública da API usada no e-mail de aprovação/recusa |

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

Edite as variáveis no `docker-compose.yml`:

```yaml
SMTP_ENABLED: "true"
SMTP_HOST: "smtp.gmail.com"
SMTP_PORT: "587"
SMTP_FROM: "seuemail@gmail.com"
SMTP_USERNAME: "seuemail@gmail.com"
SMTP_PASSWORD: "sua_senha_de_app"
PUBLIC_BASE_URL: "https://api.sua-oficina.com"
```
