from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Categoria, Material, Movimentacao, Pedido, Perfil, Setor

User = get_user_model()


class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False


class UsuarioAdmin(UserAdmin):
    inlines = [PerfilInline]


admin.site.unregister(User)
admin.site.register(User, UsuarioAdmin)


class SomenteLeitura:
    """Pedidos e movimentações só mudam pelo sistema, para não quebrar o saldo."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    search_fields = ["nome"]


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ["nome"]


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nome", "categoria", "unidade", "saldo"]
    search_fields = ["codigo", "nome"]
    readonly_fields = ["saldo"]


@admin.register(Pedido)
class PedidoAdmin(SomenteLeitura, admin.ModelAdmin):
    list_display = ["id", "material", "quantidade", "solicitante", "setor", "status", "criado_em"]
    list_filter = ["status", "setor"]


@admin.register(Movimentacao)
class MovimentacaoAdmin(SomenteLeitura, admin.ModelAdmin):
    list_display = ["data", "material", "tipo", "quantidade", "saldo_apos", "responsavel"]
    list_filter = ["tipo"]
