from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html", redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.catalogo, name="catalogo"),
    # solicitante
    path("pedidos/novo/", views.pedido_novo, name="pedido_novo"),
    path("pedidos/meus/", views.meus_pedidos, name="meus_pedidos"),
    # gerência
    path("gerencia/materiais/novo/", views.material_novo, name="material_novo"),
    path("gerencia/materiais/<int:pk>/editar/", views.material_editar, name="material_editar"),
    path("gerencia/entradas/nova/", views.entrada_nova, name="entrada_nova"),
    path("gerencia/solicitantes/", views.solicitantes, name="solicitantes"),
    path("gerencia/solicitantes/novo/", views.solicitante_novo, name="solicitante_novo"),
    path("gerencia/pedidos/", views.pedidos_pendentes, name="pedidos_pendentes"),
    path("gerencia/pedidos/<int:pk>/atender/", views.pedido_atender, name="pedido_atender"),
    path("gerencia/pedidos/<int:pk>/recusar/", views.pedido_recusar, name="pedido_recusar"),
    path("gerencia/historico/", views.historico, name="historico"),
]
