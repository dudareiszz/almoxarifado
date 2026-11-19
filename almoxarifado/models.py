from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Setor(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nome"]
        verbose_name_plural = "setores"

    def __str__(self):
        return self.nome


class Perfil(models.Model):
    """Dados extras da conta (usuário do Django): setor de lotação."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    setor = models.ForeignKey(Setor, on_delete=models.PROTECT, related_name="perfis")

    def __str__(self):
        return f"{self.usuario} ({self.setor})"


class Categoria(models.Model):
    nome = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Material(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    nome = models.CharField(max_length=120)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="materiais"
    )
    unidade = models.CharField(max_length=20)
    # O saldo só muda por entradas e saídas (services.py), nunca por edição direta.
    saldo = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    @property
    def disponivel(self):
        return self.saldo > 0

    @property
    def situacao(self):
        return "Disponível" if self.disponivel else "Sem estoque"


class Pedido(models.Model):
    PENDENTE = "PENDENTE"
    ATENDIDO = "ATENDIDO"
    RECUSADO = "RECUSADO"
    STATUS = [
        (PENDENTE, "Pendente"),
        (ATENDIDO, "Atendido"),
        (RECUSADO, "Recusado"),
    ]

    material = models.ForeignKey(
        Material, on_delete=models.PROTECT, related_name="pedidos"
    )
    quantidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    justificativa = models.TextField()
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos"
    )
    # Setor registrado no momento do pedido (preserva o histórico).
    setor = models.ForeignKey(Setor, on_delete=models.PROTECT, related_name="pedidos")
    criado_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS, default=PENDENTE)
    decidido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pedidos_decididos",
    )
    decidido_em = models.DateTimeField(null=True, blank=True)
    motivo_recusa = models.TextField(blank=True)

    class Meta:
        ordering = ["criado_em", "id"]

    def __str__(self):
        return f"Pedido #{self.pk} - {self.material} x{self.quantidade}"


class Movimentacao(models.Model):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"
    TIPOS = [(ENTRADA, "Entrada"), (SAIDA, "Saída")]

    material = models.ForeignKey(
        Material, on_delete=models.PROTECT, related_name="movimentacoes"
    )
    tipo = models.CharField(max_length=10, choices=TIPOS)
    quantidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    data = models.DateTimeField(auto_now_add=True)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movimentacoes"
    )
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes",
    )
    saldo_apos = models.PositiveIntegerField()

    class Meta:
        ordering = ["-data", "-id"]
        verbose_name = "movimentação"
        verbose_name_plural = "movimentações"

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.quantidade} - {self.material}"
