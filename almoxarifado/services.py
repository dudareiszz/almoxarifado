"""Regras de negócio do estoque. Tudo que altera saldo passa por aqui."""
from django.db import transaction
from django.utils import timezone

from .models import Material, Movimentacao, Pedido


class PedidoJaDecidido(Exception):
    """O pedido já foi atendido ou recusado (evita baixa em duplicidade)."""


class SaldoInsuficiente(Exception):
    def __init__(self, pedido, material):
        self.pedido = pedido
        self.material = material
        super().__init__(
            f"Saldo insuficiente: o pedido solicita {pedido.quantidade} {material.unidade} "
            f"de «{material.nome}», mas o saldo atual é {material.saldo}. "
            "O pedido continua pendente; registre uma entrada para poder atendê-lo."
        )


@transaction.atomic
def registrar_entrada(material_id, quantidade, usuario):
    if quantidade < 1:
        raise ValueError("A quantidade da entrada deve ser positiva.")
    material = Material.objects.select_for_update().get(pk=material_id)
    material.saldo += quantidade
    material.save(update_fields=["saldo"])
    return Movimentacao.objects.create(
        material=material,
        tipo=Movimentacao.ENTRADA,
        quantidade=quantidade,
        responsavel=usuario,
        saldo_apos=material.saldo,
    )


@transaction.atomic
def atender_pedido(pedido_id, gerente):
    """Dá baixa no estoque uma única vez ou levanta SaldoInsuficiente."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido_id)
    if pedido.status != Pedido.PENDENTE:
        raise PedidoJaDecidido()
    material = Material.objects.select_for_update().get(pk=pedido.material_id)
    if pedido.quantidade > material.saldo:
        raise SaldoInsuficiente(pedido, material)

    material.saldo -= pedido.quantidade
    material.save(update_fields=["saldo"])
    Movimentacao.objects.create(
        material=material,
        tipo=Movimentacao.SAIDA,
        quantidade=pedido.quantidade,
        responsavel=gerente,
        pedido=pedido,
        saldo_apos=material.saldo,
    )
    pedido.status = Pedido.ATENDIDO
    pedido.decidido_por = gerente
    pedido.decidido_em = timezone.now()
    pedido.save(update_fields=["status", "decidido_por", "decidido_em"])
    return pedido


@transaction.atomic
def recusar_pedido(pedido_id, gerente, motivo):
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValueError("O motivo da recusa é obrigatório.")
    pedido = Pedido.objects.select_for_update().get(pk=pedido_id)
    if pedido.status != Pedido.PENDENTE:
        raise PedidoJaDecidido()
    pedido.status = Pedido.RECUSADO
    pedido.decidido_por = gerente
    pedido.decidido_em = timezone.now()
    pedido.motivo_recusa = motivo
    pedido.save(update_fields=["status", "decidido_por", "decidido_em", "motivo_recusa"])
    return pedido
