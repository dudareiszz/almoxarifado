from .permissions import eh_gerente


def papel(request):
    return {"eh_gerente": eh_gerente(request.user)}
