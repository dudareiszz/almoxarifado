from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import transaction

from .models import Categoria, Material, Pedido, Perfil, Setor

User = get_user_model()


def obter_ou_criar(modelo, nome):
    """Busca por nome (sem diferenciar maiúsculas) ou cria."""
    nome = " ".join(nome.split())
    existente = modelo.objects.filter(nome__iexact=nome).first()
    return existente or modelo.objects.create(nome=nome)


def _rotulo_material(material):
    return f"{material.codigo} – {material.nome} (saldo: {material.saldo} {material.unidade})"


class MaterialForm(forms.ModelForm):
    categoria_nome = forms.CharField(
        label="Categoria",
        max_length=80,
        help_text="Digite a categoria. Se ainda não existir, ela será criada.",
    )
    field_order = ["codigo", "nome", "categoria_nome", "unidade"]

    class Meta:
        model = Material
        fields = ["codigo", "nome", "unidade"]
        labels = {
            "codigo": "Código",
            "nome": "Nome do material",
            "unidade": "Unidade de medida",
        }
        help_texts = {
            "codigo": "Exemplo: PAP-001. Não pode repetir.",
            "unidade": "Exemplo: unidade, resma, caixa, pacote.",
        }
        error_messages = {
            "codigo": {"unique": "Já existe um material com este código."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["categoria_nome"].initial = self.instance.categoria.nome

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()

    def save(self, commit=True):
        self.instance.categoria = obter_ou_criar(
            Categoria, self.cleaned_data["categoria_nome"]
        )
        return super().save(commit)


class EntradaForm(forms.Form):
    material = forms.ModelChoiceField(
        queryset=Material.objects.order_by("nome"),
        label="Material",
        empty_label="Selecione um material",
        error_messages={"required": "Escolha o material que está entrando."},
    )
    quantidade = forms.IntegerField(
        label="Quantidade recebida",
        min_value=1,
        widget=forms.NumberInput(attrs={"min": 1}),
        error_messages={
            "required": "Informe a quantidade.",
            "min_value": "A quantidade deve ser maior que zero.",
            "invalid": "Informe um número inteiro.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["material"].label_from_instance = _rotulo_material


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["material", "quantidade", "justificativa"]
        labels = {
            "material": "Material",
            "quantidade": "Quantidade desejada",
            "justificativa": "Justificativa",
        }
        help_texts = {"justificativa": "Explique para que o material será usado."}
        widgets = {
            "quantidade": forms.NumberInput(attrs={"min": 1}),
            "justificativa": forms.Textarea(attrs={"rows": 3}),
        }
        error_messages = {
            "material": {"required": "Escolha um material."},
            "quantidade": {
                "required": "Informe a quantidade.",
                "invalid": "Informe um número inteiro.",
            },
            "justificativa": {"required": "Informe a justificativa do pedido."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["material"].queryset = Material.objects.order_by("nome")
        self.fields["material"].empty_label = "Selecione um material"
        self.fields["material"].label_from_instance = _rotulo_material

    def clean_justificativa(self):
        texto = self.cleaned_data["justificativa"].strip()
        if not texto:
            raise forms.ValidationError("Informe a justificativa do pedido.")
        return texto


class RecusaForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo da recusa",
        widget=forms.Textarea(attrs={"rows": 3}),
        error_messages={"required": "Informe o motivo da recusa."},
    )

    def clean_motivo(self):
        motivo = self.cleaned_data["motivo"].strip()
        if not motivo:
            raise forms.ValidationError("Informe o motivo da recusa.")
        return motivo


class SolicitanteForm(forms.Form):
    nome = forms.CharField(label="Nome completo", max_length=150)
    usuario = forms.CharField(
        label="Usuário (login)",
        max_length=150,
        validators=[UnicodeUsernameValidator()],
        help_text="Letras, números e os símbolos @ . + - _",
    )
    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(render_value=False),
        help_text="Mínimo de 8 caracteres, sem ser só números nem muito comum.",
    )
    setor = forms.CharField(
        label="Setor de lotação",
        max_length=100,
        help_text="Digite o setor. Se ainda não existir, ele será criado.",
    )

    def clean_usuario(self):
        usuario = self.cleaned_data["usuario"].strip()
        if User.objects.filter(username__iexact=usuario).exists():
            raise forms.ValidationError("Este usuário já existe. Escolha outro.")
        return usuario

    def clean_senha(self):
        senha = self.cleaned_data["senha"]
        validate_password(senha)
        return senha

    @transaction.atomic
    def salvar(self):
        dados = self.cleaned_data
        usuario = User.objects.create_user(
            username=dados["usuario"],
            password=dados["senha"],
            first_name=dados["nome"].strip(),
        )
        Perfil.objects.create(usuario=usuario, setor=obter_ou_criar(Setor, dados["setor"]))
        return usuario
