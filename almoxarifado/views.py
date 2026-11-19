from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import (
    EntradaForm,
    MaterialForm,
    PedidoForm,
    RecusaForm,
    SolicitanteForm,
)
from .models import Material, Movimentacao, Pedido, Perfil
from .permissions import gerente_required, solicitante_required


# ---------------------------------------------------------------- catálogo
@login_required
def catalogo(request):
    busca = request.GET.get("q", "").strip()
    materiais = Material.objects.select_related("categoria")
    if busca:
        materiais = materiais.filter(
            Q(nome__icontains=busca) | Q(codigo__icontains=busca)
        )
    return render(
        request,
        "almoxarifado/catalogo.html",
        {"materiais": materiais, "busca": busca},
    )


# --------------------------------------------------------------- gerência
@gerente_required
def material_novo(request):
    form = MaterialForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        material = form.save()
        messages.success(
            request,
            f"Material «{material.nome}» cadastrado. Registre uma entrada para criar saldo.",
        )
        return redirect("catalogo")
    return render(
        request,
        "almoxarifado/form.html",
        {"form": form, "titulo": "Novo material", "botao": "Salvar material"},
    )


@gerente_required
def material_editar(request, pk):
    material = get_object_or_404(Material, pk=pk)
    form = MaterialForm(request.POST or None, instance=material)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Material «{material.nome}» atualizado.")
        return redirect("catalogo")
    return render(
        request,
        "almoxarifado/form.html",
        {
            "form": form,
            "titulo": f"Editar material: {material.nome}",
            "intro": f"Saldo atual: {material.saldo} {material.unidade}. "
            "O saldo só muda por entradas e atendimentos.",
            "botao": "Salvar alterações",
        },
    )


@gerente_required
def entrada_nova(request):
    inicial = {}
    if request.GET.get("material", "").isdigit():
        inicial["material"] = request.GET["material"]
    form = EntradaForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        material = form.cleaned_data["material"]
        mov = services.registrar_entrada(
            material.pk, form.cleaned_data["quantidade"], request.user
        )
        messages.success(
            request,
            f"Entrada de {mov.quantidade} {material.unidade} registrada em «{material.nome}». "
            f"Novo saldo: {mov.saldo_apos}.",
        )
        return redirect("catalogo")
    return render(
        request,
        "almoxarifado/form.html",
        {"form": form, "titulo": "Registrar entrada", "botao": "Registrar entrada"},
    )


@gerente_required
def solicitantes(request):
    perfis = Perfil.objects.select_related("usuario", "setor").order_by(
        "usuario__first_name", "usuario__username"
    )
    return render(request, "almoxarifado/solicitantes.html", {"perfis": perfis})


@gerente_required
def solicitante_novo(request):
    form = SolicitanteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.salvar()
        messages.success(request, f"Conta de «{usuario.username}» criada.")
        return redirect("solicitantes")
    return render(
        request,
        "almoxarifado/form.html",
        {"form": form, "titulo": "Nova conta de solicitante", "botao": "Criar conta"},
    )


def _contexto_pendentes():
    return {
        "pendentes": Pedido.objects.filter(status=Pedido.PENDENTE).select_related(
            "material", "solicitante", "setor"
        ),
        "decididos": Pedido.objects.exclude(status=Pedido.PENDENTE)
        .select_related("material", "solicitante", "setor", "decidido_por")
        .order_by("-decidido_em", "-id")[:10],
    }


@gerente_required
def pedidos_pendentes(request):
    return render(request, "almoxarifado/pendentes.html", _contexto_pendentes())


@gerente_required
@require_POST
def pedido_atender(request, pk):
    try:
        pedido = services.atender_pedido(pk, request.user)
    except Pedido.DoesNotExist:
        raise Http404
    except services.SaldoInsuficiente as erro:
        contexto = _contexto_pendentes()
        contexto["erro_id"] = erro.pedido.pk
        contexto["erro_msg"] = str(erro)
        return render(request, "almoxarifado/pendentes.html", contexto)
    except services.PedidoJaDecidido:
        messages.warning(request, "Este pedido já foi decidido e não pode ser alterado.")
        return redirect("pedidos_pendentes")
    messages.success(
        request,
        f"Pedido #{pedido.pk} atendido: saída de {pedido.quantidade} {pedido.material.unidade} "
        f"de «{pedido.material.nome}» para {pedido.solicitante.get_full_name() or pedido.solicitante.username}.",
    )
    return redirect("pedidos_pendentes")


@gerente_required
def pedido_recusar(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related("material", "solicitante", "setor"), pk=pk
    )
    if pedido.status != Pedido.PENDENTE:
        messages.warning(request, "Este pedido já foi decidido e não pode ser alterado.")
        return redirect("pedidos_pendentes")
    form = RecusaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.recusar_pedido(pedido.pk, request.user, form.cleaned_data["motivo"])
        except services.PedidoJaDecidido:
            messages.warning(request, "Este pedido já foi decidido e não pode ser alterado.")
        else:
            messages.success(request, f"Pedido #{pedido.pk} recusado.")
        return redirect("pedidos_pendentes")
    return render(
        request, "almoxarifado/recusar.html", {"pedido": pedido, "form": form}
    )


@gerente_required
def historico(request):
    movimentacoes = Movimentacao.objects.select_related(
        "material", "responsavel", "pedido__solicitante", "pedido__setor"
    )[:200]
    return render(
        request, "almoxarifado/historico.html", {"movimentacoes": movimentacoes}
    )


# ------------------------------------------------------------ solicitante
@solicitante_required
def pedido_novo(request):
    perfil = getattr(request.user, "perfil", None)
    if perfil is None:
        messages.error(
            request,
            "Sua conta não tem setor de lotação. Peça à gerência para completar o cadastro.",
        )
        return redirect("catalogo")
    inicial = {}
    if request.GET.get("material", "").isdigit():
        inicial["material"] = request.GET["material"]
    form = PedidoForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        pedido = form.save(commit=False)
        pedido.solicitante = request.user
        pedido.setor = perfil.setor
        pedido.save()
        messages.success(
            request,
            f"Pedido #{pedido.pk} enviado. Acompanhe a resposta em «Meus pedidos».",
        )
        return redirect("meus_pedidos")
    return render(
        request,
        "almoxarifado/form.html",
        {"form": form, "titulo": "Novo pedido", "botao": "Enviar pedido"},
    )


@login_required
def meus_pedidos(request):
    pedidos = (
        Pedido.objects.filter(solicitante=request.user)
        .select_related("material", "decidido_por")
        .order_by("-criado_em", "-id")
    )
    return render(request, "almoxarifado/meus_pedidos.html", {"pedidos": pedidos})
