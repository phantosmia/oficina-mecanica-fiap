from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum


class SagaState(StrEnum):
    """Estados da saga (ADR-0008, revisado pela ADR-0010; tabela em docs/saga.md)."""

    ENQUEUING_DIAGNOSIS = "ENFILEIRANDO_DIAGNOSTICO"
    AWAITING_DIAGNOSIS = "AGUARDANDO_DIAGNOSTICO"
    RESERVING_PARTS = "RESERVANDO_PECAS"
    GENERATING_QUOTE = "GERANDO_ORCAMENTO"
    AWAITING_APPROVAL = "AGUARDANDO_APROVACAO"
    CREATING_CHARGE = "GERANDO_COBRANCA"
    AWAITING_PAYMENT = "AGUARDANDO_PAGAMENTO"
    CONFIRMING_WITHDRAWAL = "CONFIRMANDO_BAIXA"
    ENQUEUING_REPAIR = "ENFILEIRANDO_REPARO"
    IN_REPAIR = "EM_REPARO"
    COMPLETED = "CONCLUIDA"
    COMPENSATING = "COMPENSANDO"
    CANCELLED = "CANCELADA"


TERMINAL_STATES = {SagaState.COMPLETED, SagaState.CANCELLED}

# Estados que esperam a resposta de um participante a um comando: têm prazo
# curto, com reenvio do comando quando ele vence.
AWAITING_REPLY_STATES = {
    SagaState.ENQUEUING_DIAGNOSIS,
    SagaState.RESERVING_PARTS,
    SagaState.GENERATING_QUOTE,
    SagaState.CREATING_CHARGE,
    SagaState.CONFIRMING_WITHDRAWAL,
    SagaState.ENQUEUING_REPAIR,
    SagaState.COMPENSATING,
}

# Participante dono de cada comando: define a fila SQS de destino.
COMMAND_DESTINATIONS = {
    "EnfileirarDiagnostico": "execucao",
    "EnfileirarReparo": "execucao",
    "ReservarPecas": "estoque",
    "ConfirmarBaixa": "estoque",
    "LiberarPecas": "estoque",
    "DevolverPecas": "estoque",
    "GerarOrcamento": "orcamento",
    "CancelarOrcamento": "orcamento",
    "CriarCobranca": "pagamento",
    "CancelarCobranca": "pagamento",
    "EstornarPagamento": "pagamento",
}

# Compensação → evento que a confirma.
COMPENSATION_CONFIRMATIONS = {
    "LiberarPecas": "PecasLiberadas",
    "DevolverPecas": "PecasDevolvidas",
    "CancelarOrcamento": "OrcamentoCancelado",
    "CancelarCobranca": "CobrancaCancelada",
    "EstornarPagamento": "PagamentoEstornado",
}

# O que compensar se um participante não responder (esgotadas as tentativas)
# em cada passo. Inclui o próprio passo: sem resposta, não dá para saber se o
# efeito aconteceu, e as compensações são seguras mesmo sem nada a desfazer.
TIMEOUT_COMPENSATIONS: dict[SagaState, list[str]] = {
    SagaState.ENQUEUING_DIAGNOSIS: [],
    SagaState.RESERVING_PARTS: ["LiberarPecas"],
    SagaState.GENERATING_QUOTE: ["CancelarOrcamento", "LiberarPecas"],
    SagaState.CREATING_CHARGE: ["CancelarCobranca", "CancelarOrcamento", "LiberarPecas"],
    SagaState.CONFIRMING_WITHDRAWAL: ["EstornarPagamento", "CancelarOrcamento", "LiberarPecas"],
    SagaState.ENQUEUING_REPAIR: ["EstornarPagamento", "CancelarOrcamento", "DevolverPecas"],
}


@dataclass(frozen=True)
class SagaTimeouts:
    reply: timedelta = timedelta(minutes=5)
    approval: timedelta = timedelta(days=7)
    payment: timedelta = timedelta(days=4)  # acima da validade da cobrança no Mercado Pago (3 dias)
    max_attempts: int = 3
