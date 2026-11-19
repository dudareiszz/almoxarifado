import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Setor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=100, unique=True)),
            ],
            options={"verbose_name_plural": "setores", "ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="Categoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=80, unique=True)),
            ],
            options={"ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="Perfil",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("usuario", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="perfil", to=settings.AUTH_USER_MODEL)),
                ("setor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="perfis", to="almoxarifado.setor")),
            ],
        ),
        migrations.CreateModel(
            name="Material",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=30, unique=True)),
                ("nome", models.CharField(max_length=120)),
                ("unidade", models.CharField(max_length=20)),
                ("saldo", models.PositiveIntegerField(default=0, editable=False)),
                ("categoria", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="materiais", to="almoxarifado.categoria")),
            ],
            options={"ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="Pedido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantidade", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("justificativa", models.TextField()),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("status", models.CharField(choices=[("PENDENTE", "Pendente"), ("ATENDIDO", "Atendido"), ("RECUSADO", "Recusado")], default="PENDENTE", max_length=10)),
                ("decidido_em", models.DateTimeField(blank=True, null=True)),
                ("motivo_recusa", models.TextField(blank=True)),
                ("decidido_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="pedidos_decididos", to=settings.AUTH_USER_MODEL)),
                ("material", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pedidos", to="almoxarifado.material")),
                ("setor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pedidos", to="almoxarifado.setor")),
                ("solicitante", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pedidos", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["criado_em", "id"]},
        ),
        migrations.CreateModel(
            name="Movimentacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("ENTRADA", "Entrada"), ("SAIDA", "Saída")], max_length=10)),
                ("quantidade", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("data", models.DateTimeField(auto_now_add=True)),
                ("saldo_apos", models.PositiveIntegerField()),
                ("material", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="movimentacoes", to="almoxarifado.material")),
                ("pedido", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movimentacoes", to="almoxarifado.pedido")),
                ("responsavel", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="movimentacoes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "movimentação", "verbose_name_plural": "movimentações", "ordering": ["-data", "-id"]},
        ),
    ]
