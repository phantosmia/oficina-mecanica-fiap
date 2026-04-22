#!/usr/bin/env python3
"""
Script para popular o banco de dados com dados de exemplo.
Executar: poetry run python scripts/populate_db.py
"""

import sys
from datetime import datetime
from pathlib import Path

# Adicionar o diretório raiz ao path para importar módulos
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.shared.database import get_session, init_database
from app.shared.models import Client, Vehicle, CatalogService, Part, ServiceOrder, ServiceOrderService, ServiceOrderPart


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
    # Inicializar banco se necessário
    init_database()

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

        # Criar serviços do catálogo
        services = [
            CatalogService(
                name="Troca de óleo",
                description="Troca completa de óleo do motor",
                base_price=150.00,
                estimated_minutes=30,
                active=True
            ),
            CatalogService(
                name="Revisão de freios",
                description="Verificação e ajuste do sistema de freios",
                base_price=200.00,
                estimated_minutes=60,
                active=True
            ),
            CatalogService(
                name="Alinhamento e balanceamento",
                description="Alinhamento das rodas e balanceamento dos pneus",
                base_price=120.00,
                estimated_minutes=45,
                active=True
            ),
            CatalogService(
                name="Troca de filtros",
                description="Troca de filtro de ar, combustível e óleo",
                base_price=80.00,
                estimated_minutes=20,
                active=True
            ),
            CatalogService(
                name="Diagnóstico eletrônico",
                description="Verificação de códigos de erro no sistema eletrônico",
                base_price=100.00,
                estimated_minutes=30,
                active=True
            ),
        ]
        session.add_all(services)
        session.flush()

        # Criar peças
        parts = [
            Part(
                name="Óleo sintético 5W30",
                sku="OLEO-5W30-1L",
                description="Óleo sintético para motores",
                unit_price=45.00,
                stock_quantity=50,
                min_stock_level=10
            ),
            Part(
                name="Filtro de óleo",
                sku="FILTRO-OLEO-GENERIC",
                description="Filtro de óleo genérico",
                unit_price=25.00,
                stock_quantity=30,
                min_stock_level=5
            ),
            Part(
                name="Pastilha de freio dianteira",
                sku="PAST-FREIO-DIAN",
                description="Conjunto de pastilhas de freio dianteiras",
                unit_price=180.00,
                stock_quantity=20,
                min_stock_level=3
            ),
            Part(
                name="Disco de freio",
                sku="DISCO-FREIO-DIAN",
                description="Disco de freio dianteiro",
                unit_price=250.00,
                stock_quantity=15,
                min_stock_level=2
            ),
            Part(
                name="Filtro de ar",
                sku="FILTRO-AR-GENERIC",
                description="Filtro de ar do motor",
                unit_price=35.00,
                stock_quantity=25,
                min_stock_level=5
            ),
        ]
        session.add_all(parts)
        session.flush()

        # Criar ordens de serviço
        orders = [
            ServiceOrder(
                client_id=clients[0].id,
                vehicle_id=vehicles[0].id,
                status="recebida",
                problem_description="Carro com barulho estranho no motor",
                labor_total=150.00,
                parts_total=70.00,
                quote_total=220.00
            ),
            ServiceOrder(
                client_id=clients[1].id,
                vehicle_id=vehicles[2].id,
                status="em_diagnostico",
                problem_description="Freios rangendo",
                diagnosis_notes="Verificado desgaste nas pastilhas",
                labor_total=200.00,
                parts_total=180.00,
                quote_total=380.00
            ),
            ServiceOrder(
                client_id=clients[2].id,
                vehicle_id=vehicles[3].id,
                status="aguardando_aprovacao",
                problem_description="Revisão geral",
                labor_total=300.00,
                parts_total=140.00,
                quote_total=440.00,
                quote_sent_at=datetime(2024, 1, 15, 10, 0, 0)
            ),
            ServiceOrder(
                client_id=clients[0].id,
                vehicle_id=vehicles[1].id,
                status="em_execucao",
                problem_description="Troca de óleo preventiva",
                labor_total=150.00,
                parts_total=70.00,
                quote_total=220.00,
                approved_at=datetime(2024, 1, 10, 9, 0, 0),
                started_at=datetime(2024, 1, 10, 14, 0, 0)
            ),
            ServiceOrder(
                client_id=clients[1].id,
                vehicle_id=vehicles[2].id,
                status="finalizada",
                problem_description="Alinhamento e balanceamento",
                labor_total=120.00,
                parts_total=0.00,
                quote_total=120.00,
                approved_at=datetime(2024, 1, 5, 8, 0, 0),
                started_at=datetime(2024, 1, 5, 10, 0, 0),
                finished_at=datetime(2024, 1, 5, 11, 0, 0)
            ),
        ]
        session.add_all(orders)
        session.flush()

        # Adicionar itens das ordens de serviço
        # Ordem 1: Troca de óleo
        session.add(ServiceOrderService(
            service_order_id=orders[0].id,
            service_id=services[0].id,
            quantity=1,
            unit_price=150.00,
            subtotal=150.00
        ))
        session.add(ServiceOrderPart(
            service_order_id=orders[0].id,
            part_id=parts[0].id,
            quantity=4,
            unit_price=45.00,
            subtotal=180.00
        ))
        session.add(ServiceOrderPart(
            service_order_id=orders[0].id,
            part_id=parts[1].id,
            quantity=1,
            unit_price=25.00,
            subtotal=25.00
        ))

        # Ordem 2: Revisão de freios
        session.add(ServiceOrderService(
            service_order_id=orders[1].id,
            service_id=services[1].id,
            quantity=1,
            unit_price=200.00,
            subtotal=200.00
        ))
        session.add(ServiceOrderPart(
            service_order_id=orders[1].id,
            part_id=parts[2].id,
            quantity=1,
            unit_price=180.00,
            subtotal=180.00
        ))

        # Ordem 3: Revisão geral
        session.add(ServiceOrderService(
            service_order_id=orders[2].id,
            service_id=services[0].id,
            quantity=1,
            unit_price=150.00,
            subtotal=150.00
        ))
        session.add(ServiceOrderService(
            service_order_id=orders[2].id,
            service_id=services[3].id,
            quantity=1,
            unit_price=80.00,
            subtotal=80.00
        ))
        session.add(ServiceOrderPart(
            service_order_id=orders[2].id,
            part_id=parts[0].id,
            quantity=4,
            unit_price=45.00,
            subtotal=180.00
        ))
        session.add(ServiceOrderPart(
            service_order_id=orders[2].id,
            part_id=parts[4].id,
            quantity=1,
            unit_price=35.00,
            subtotal=35.00
        ))

        # Ordem 4: Troca de óleo
        session.add(ServiceOrderService(
            service_order_id=orders[3].id,
            service_id=services[0].id,
            quantity=1,
            unit_price=150.00,
            subtotal=150.00
        ))
        session.add(ServiceOrderPart(
            service_order_id=orders[3].id,
            part_id=parts[0].id,
            quantity=4,
            unit_price=45.00,
            subtotal=180.00
        ))

        # Ordem 5: Alinhamento
        session.add(ServiceOrderService(
            service_order_id=orders[4].id,
            service_id=services[2].id,
            quantity=1,
            unit_price=120.00,
            subtotal=120.00
        ))

        session.commit()
        print("Banco populado com sucesso!")
        print(f"- {len(clients)} clientes")
        print(f"- {len(vehicles)} veículos")
        print(f"- {len(services)} serviços no catálogo")
        print(f"- {len(parts)} peças")
        print(f"- {len(orders)} ordens de serviço")

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