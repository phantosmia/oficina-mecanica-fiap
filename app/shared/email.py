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
# Os e-mails de orçamento e de pagamento são enviados pelos serviços de
# Orçamento e de Pagamento (RFC-0008); aqui fica só o aviso de OS finalizada.

def order_finished_message(order_id: int) -> tuple[str, str]:
    subject = f"[OS #{order_id}] Serviço finalizado — veículo pronto para retirada"
    body = (
        f"Olá!\n\n"
        f"O serviço da sua Ordem de Serviço #{order_id} foi finalizado.\n"
        f"Seu veículo está pronto para retirada.\n\n"
        f"Atenciosamente,\nOficina Mecânica FIAP"
    )
    return subject, body
