"""Carrega dados fictícios para a demonstração. Pode ser rodado mais de uma vez."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from almoxarifado import services
from almoxarifado.models import Categoria, Material, Perfil, Setor
from almoxarifado.permissions import GRUPO_GERENCIA

User = get_user_model()

SENHA_GERENTE = "Gerente@123"
SENHA_SOLICITANTE = "Solic@123"
SENHA_ADMIN = "Admin@123"

SOLICITANTES = [
    ("ana", "Ana Souza (fictícia)", "Coordenação de Informática"),
    ("bruno", "Bruno Lima (fictício)", "Secretaria Acadêmica"),
]

# (código, nome, categoria, unidade, saldo inicial). A resma de papel A4 fica
# de fora de propósito: ela é cadastrada ao vivo na demonstração.
MATERIAIS = [
    ("PAP-002", "Caneta esferográfica azul", "Papelaria", "unidade", 40),
    ("PAP-003", "Marcador para quadro branco", "Papelaria", "unidade", 15),
    ("PAP-004", "Pasta suspensa", "Papelaria", "unidade", 25),
    ("INF-001", "Cabo de rede 2 m", "Informática", "unidade", 8),
    ("INF-002", "Cartucho de tinta preta", "Informática", "unidade", 0),
    ("LIM-001", "Detergente neutro 500 ml", "Limpeza", "frasco", 12),
]


class Command(BaseCommand):
    help = "Cria gerência, solicitantes, setores e materiais fictícios."

    @transaction.atomic
    def handle(self, *args, **options):
        grupo, _ = Group.objects.get_or_create(name=GRUPO_GERENCIA)

        gerente, criado = User.objects.get_or_create(
            username="gerente", defaults={"first_name": "Gerente do Almoxarifado"}
        )
        if criado:
            gerente.set_password(SENHA_GERENTE)
            gerente.save()
        gerente.groups.add(grupo)

        admin, criado = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True, "first_name": "Administrador"},
        )
        if criado:
            admin.set_password(SENHA_ADMIN)
            admin.save()

        for usuario, nome, nome_setor in SOLICITANTES:
            setor, _ = Setor.objects.get_or_create(nome=nome_setor)
            conta, criado = User.objects.get_or_create(
                username=usuario, defaults={"first_name": nome}
            )
            if criado:
                conta.set_password(SENHA_SOLICITANTE)
                conta.save()
            Perfil.objects.get_or_create(usuario=conta, defaults={"setor": setor})

        for codigo, nome, nome_categoria, unidade, saldo in MATERIAIS:
            categoria, _ = Categoria.objects.get_or_create(nome=nome_categoria)
            material, criado = Material.objects.get_or_create(
                codigo=codigo,
                defaults={"nome": nome, "categoria": categoria, "unidade": unidade},
            )
            if criado and saldo > 0:
                services.registrar_entrada(material.pk, saldo, gerente)

        self.stdout.write(self.style.SUCCESS("Dados fictícios carregados."))
        self.stdout.write(f"  Gerência:     gerente / {SENHA_GERENTE}")
        self.stdout.write(f"  Solicitantes: ana, bruno / {SENHA_SOLICITANTE}")
        self.stdout.write(f"  Admin Django: admin / {SENHA_ADMIN}")
