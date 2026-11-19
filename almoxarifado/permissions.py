"""Perfis e permissões. Toda checagem é feita no servidor."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

GRUPO_GERENCIA = "Gerencia"


def eh_gerente(user):
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name=GRUPO_GERENCIA).exists()


def gerente_required(view):
    """Exige login e perfil de gerência (senão 403, mesmo acessando a URL direto)."""

    @wraps(view)
    def interno(request, *args, **kwargs):
        if not eh_gerente(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return login_required(interno)


def solicitante_required(view):
    """Exige login e conta de solicitante (gerência não faz pedidos)."""

    @wraps(view)
    def interno(request, *args, **kwargs):
        if eh_gerente(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return login_required(interno)
