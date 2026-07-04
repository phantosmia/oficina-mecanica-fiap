from abc import ABC, abstractmethod


class IEmailNotifier(ABC):
    """Port — define o contrato de envio de notificações por e-mail."""

    @abstractmethod
    def send(self, *, to: str, subject: str, body: str) -> None: ...


class NullEmailNotifier(IEmailNotifier):
    """Implementação no-op usada em testes e quando SMTP está desabilitado."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        pass


# ── templates de mensagem ─────────────────────────────────────────────────────

def quote_available_message(order_id: int, quote_total: float, quote_token: str, public_base_url: str) -> tuple[str, str]:
    response_url = f"{public_base_url.rstrip('/')}/service-orders/{order_id}/quote-response"
    subject = f"[OS #{order_id}] Orçamento disponível para aprovação"
    body = (
        f"Olá!\n\n"
        f"O orçamento da sua Ordem de Serviço #{order_id} está pronto.\n"
        f"Valor total: R$ {quote_total:.2f}\n\n"
        f"Para aprovar ou recusar, envie uma requisição POST para:\n"
        f"{response_url}\n\n"
        f"Token do orçamento: {quote_token}\n"
        f"Opções de decisão: approve ou reject.\n\n"
        f"Atenciosamente,\nOficina Mecânica FIAP"
    )
    return subject, body


def quote_approved_message(order_id: int) -> tuple[str, str]:
    subject = f"[OS #{order_id}] Orçamento aprovado — serviço iniciado"
    body = (
        f"Olá!\n\n"
        f"O orçamento da sua Ordem de Serviço #{order_id} foi aprovado.\n"
        f"O serviço foi iniciado e em breve entraremos em contato.\n\n"
        f"Atenciosamente,\nOficina Mecânica FIAP"
    )
    return subject, body


def quote_rejected_message(order_id: int) -> tuple[str, str]:
    subject = f"[OS #{order_id}] Orçamento recusado"
    body = (
        f"Olá!\n\n"
        f"Registramos a recusa do orçamento da sua Ordem de Serviço #{order_id}.\n"
        f"Entre em contato conosco caso queira revisar o orçamento.\n\n"
        f"Atenciosamente,\nOficina Mecânica FIAP"
    )
    return subject, body


def order_finished_message(order_id: int) -> tuple[str, str]:
    subject = f"[OS #{order_id}] Serviço finalizado — veículo pronto para retirada"
    body = (
        f"Olá!\n\n"
        f"O serviço da sua Ordem de Serviço #{order_id} foi finalizado.\n"
        f"Seu veículo está pronto para retirada.\n\n"
        f"Atenciosamente,\nOficina Mecânica FIAP"
    )
    return subject, body
