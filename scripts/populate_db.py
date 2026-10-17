#!/usr/bin/env python3
"""
Script para popular o banco de dados com dados de exemplo.
Execute as migrations antes de rodar este script: poetry run alembic upgrade head
Executar: poetry run python scripts/populate_db.py
"""

import sys
from datetime import datetime
from pathlib import Path

# Adicionar o diretório raiz ao path para importar módulos
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.shared.database import get_session
from app.shared.models import Client, Vehicle


def generate_valid_cpf() -> str:
    """Gera um CPF válido para testes."""
    import random
    
    # Gera 9 dígitos aleatórios
    base = ''.join(str(random.randint(0, 9)) for _ in range(9))
    
    # Calcular primeiro dígito verificador
    factor = 10
    total = sum(int(digit) * weight for digit, weight in zip(base, range(factor, 1, -1)))
    remainder = 11 - (total % 11)
    first_digit = 0 if remainder >= 10 else remainder
    
    # Calcular segundo dígito verificador
    base_with_first = base + str(first_digit)
    factor = 11
    total = sum(int(digit) * weight for digit, weight in zip(base_with_first, range(factor, 1, -1)))
    remainder = 11 - (total % 11)
    second_digit = 0 if remainder >= 10 else remainder
    
    return base + str(first_digit) + str(second_digit)


def generate_valid_cnpj() -> str:
    """Gera um CNPJ válido para testes."""
    import random
    
    # Gera 12 dígitos aleatórios
    base = ''.join(str(random.randint(0, 9)) for _ in range(12))
    
    # Calcular primeiro dígito verificador
    weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digit) * weight for digit, weight in zip(base, weights))
    remainder = total % 11
    first_digit = 0 if remainder < 2 else 11 - remainder
    
    # Calcular segundo dígito verificador
    base_with_first = base + str(first_digit)
    weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digit) * weight for digit, weight in zip(base_with_first, weights))
    remainder = total % 11
    second_digit = 0 if remainder < 2 else 11 - remainder
    
    return base + str(first_digit) + str(second_digit)


def populate_database():
    """Popula o banco com dados de exemplo."""
    session = get_session()

    try:
        # Verificar se já existem dados
        if session.query(Client).count() > 0:
            print("Banco já possui dados. Pulando população.")
            return

        print("Populando banco de dados com dados de exemplo...")

        # Criar clientes
        clients = [
            Client(
                name="João Silva",
                document_type="CPF",
                document_number=generate_valid_cpf(),
                email="joao.silva@email.com",
                phone="(11) 99999-0001"
            ),
            Client(
                name="Empresa ABC Ltda",
                document_type="CNPJ",
                document_number=generate_valid_cnpj(),
                email="contato@empresaabc.com",
                phone="(11) 99999-0002"
            ),
            Client(
                name="Maria Santos",
                document_type="CPF",
                document_number=generate_valid_cpf(),
                email="maria.santos@email.com",
                phone="(11) 99999-0003"
            ),
        ]
        session.add_all(clients)
        session.flush()  # Para obter IDs

        # Criar veículos
        vehicles = [
            Vehicle(
                client_id=clients[0].id,
                brand="Toyota",
                model="Corolla",
                year=2020,
                license_plate="ABC-1234"
            ),
            Vehicle(
                client_id=clients[0].id,
                brand="Honda",
                model="Civic",
                year=2019,
                license_plate="DEF-5678"
            ),
            Vehicle(
                client_id=clients[1].id,
                brand="Ford",
                model="F-250",
                year=2021,
                license_plate="GHI-9012"
            ),
            Vehicle(
                client_id=clients[2].id,
                brand="Volkswagen",
                model="Golf",
                year=2018,
                license_plate="JKL-3456"
            ),
        ]
        session.add_all(vehicles)
        session.flush()

        # Catálogo, peças e saldo agora são dos microsserviços de Catálogo e
        # Estoque (cada um com os próprios dados de exemplo). Ordens de serviço
        # não são semeadas: toda OS precisa nascer pela API, que inicia a saga.
        session.commit()

        print("Banco populado com sucesso!")
        print(f"- {len(clients)} clientes")
        print(f"- {len(vehicles)} veículos")

    except Exception as e:
        session.rollback()
        print(f"Erro ao popular banco: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    populate_database()


def main():
    populate_database()