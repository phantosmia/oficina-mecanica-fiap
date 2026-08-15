from enum import Enum


class ClientStatus(str, Enum):
    """Status do cliente — ver docs/regras-negocio.md.

    Diferente do status de uma ordem de serviço (máquina de estados com
    transições restritas, ver `app/service_orders/domain/value_objects.py`),
    o status do cliente é um alternância simples sem regra de transição: um
    admin pode reativar um cliente inativo livremente.
    """

    ATIVO = "ativo"
    INATIVO = "inativo"
