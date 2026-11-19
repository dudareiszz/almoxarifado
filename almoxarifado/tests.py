from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from . import services
from .models import Categoria, Material, Movimentacao, Pedido, Perfil, Setor
from .permissions import GRUPO_GERENCIA

SENHA = "Senha@12345"


class BaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        grupo = Group.objects.create(name=GRUPO_GERENCIA)
        cls.gerente = User.objects.create_user("gerente", password=SENHA, first_name="Gerente")
        cls.gerente.groups.add(grupo)
        cls.ana = User.objects.create_user("ana", password=SENHA, first_name="Ana")
        cls.bruno = User.objects.create_user("bruno", password=SENHA, first_name="Bruno")
        Perfil.objects.create(usuario=cls.ana, setor=Setor.objects.create(nome="Biblioteca"))
        Perfil.objects.create(usuario=cls.bruno, setor=Setor.objects.create(nome="Secretaria"))
        cls.resma = Material.objects.create(
            codigo="PAP-001",
            nome="Resma de papel A4",
            categoria=Categoria.objects.create(nome="Papelaria"),
            unidade="resma",
        )
        services.registrar_entrada(cls.resma.pk, 1, cls.gerente)

    def entrar(self, usuario):
        self.client.logout()
        self.assertTrue(self.client.login(username=usuario.username, password=SENHA))

    def pedir(self, usuario, justificativa, quantidade=1):
        self.entrar(usuario)
        return self.client.post(
            reverse("pedido_novo"),
            {"material": self.resma.pk, "quantidade": quantidade, "justificativa": justificativa},
        )

    def saldo(self):
        self.resma.refresh_from_db()
        return self.resma.saldo


class FluxoDemonstracaoTest(BaseTest):
    def test_fluxo_completo(self):
        # 2. dois pedidos antes de qualquer atendimento; saldo não muda
        r1 = self.pedir(self.ana, "Justificativa da Ana")
        self.assertRedirects(r1, reverse("meus_pedidos"))
        self.pedir(self.bruno, "Justificativa do Bruno")
        self.assertEqual(self.saldo(), 1)
        primeiro, segundo = Pedido.objects.order_by("id")
        self.assertEqual(primeiro.setor.nome, "Biblioteca")
        self.assertEqual(primeiro.solicitante, self.ana)

        # cada solicitante vê só o próprio pedido
        self.entrar(self.ana)
        resp = self.client.get(reverse("meus_pedidos"))
        self.assertContains(resp, "Justificativa da Ana")
        self.assertNotContains(resp, "Justificativa do Bruno")

        # 3. gerente atende o primeiro
        self.entrar(self.gerente)
        self.client.post(reverse("pedido_atender", args=[primeiro.pk]))
        primeiro.refresh_from_db()
        self.assertEqual(primeiro.status, Pedido.ATENDIDO)
        self.assertEqual(primeiro.decidido_por, self.gerente)
        self.assertIsNotNone(primeiro.decidido_em)
        self.assertEqual(self.saldo(), 0)
        saida = Movimentacao.objects.get(tipo=Movimentacao.SAIDA)
        self.assertEqual(saida.pedido, primeiro)
        self.assertEqual(saida.responsavel, self.gerente)

        # 4. segundo pedido: saldo insuficiente, continua pendente
        resp = self.client.post(reverse("pedido_atender", args=[segundo.pk]))
        self.assertContains(resp, "Saldo insuficiente")
        segundo.refresh_from_db()
        self.assertEqual(segundo.status, Pedido.PENDENTE)
        self.assertEqual(self.saldo(), 0)

        # atender de novo o primeiro não dá baixa duas vezes
        self.client.post(reverse("pedido_atender", args=[primeiro.pk]))
        self.assertEqual(self.saldo(), 0)
        self.assertEqual(Movimentacao.objects.filter(tipo=Movimentacao.SAIDA).count(), 1)

        # 5. nova entrada e atendimento do restante
        self.client.post(reverse("entrada_nova"), {"material": self.resma.pk, "quantidade": 1})
        self.assertEqual(self.saldo(), 1)
        self.client.post(reverse("pedido_atender", args=[segundo.pk]))
        segundo.refresh_from_db()
        self.assertEqual(segundo.status, Pedido.ATENDIDO)
        self.assertEqual(self.saldo(), 0)


class PermissoesTest(BaseTest):
    def test_anonimo_vai_para_login(self):
        for nome in ["catalogo", "meus_pedidos", "pedido_novo", "entrada_nova", "pedidos_pendentes"]:
            url = reverse(nome)
            self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_solicitante_nao_acessa_rotas_da_gerencia(self):
        self.pedir(self.ana, "Teste")
        pedido = Pedido.objects.get()
        self.entrar(self.bruno)
        for nome in ["entrada_nova", "pedidos_pendentes", "material_novo", "solicitantes", "solicitante_novo", "historico"]:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 403, nome)
        self.assertEqual(
            self.client.post(reverse("entrada_nova"), {"material": self.resma.pk, "quantidade": 5}).status_code, 403
        )
        self.assertEqual(self.client.post(reverse("pedido_atender", args=[pedido.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("pedido_recusar", args=[pedido.pk])).status_code, 403)
        self.assertEqual(self.saldo(), 1)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.PENDENTE)

    def test_gerente_nao_faz_pedido(self):
        self.entrar(self.gerente)
        self.assertEqual(self.client.get(reverse("pedido_novo")).status_code, 403)


class ValidacaoTest(BaseTest):
    def test_quantidade_do_pedido_deve_ser_positiva(self):
        for qtd in (0, -2):
            resp = self.pedir(self.ana, "Teste", quantidade=qtd)
            self.assertEqual(resp.status_code, 200)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_quantidade_da_entrada_deve_ser_positiva(self):
        self.entrar(self.gerente)
        resp = self.client.post(reverse("entrada_nova"), {"material": self.resma.pk, "quantidade": 0})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.saldo(), 1)

    def test_recusa_exige_motivo(self):
        self.pedir(self.ana, "Teste")
        pedido = Pedido.objects.get()
        self.entrar(self.gerente)
        resp = self.client.post(reverse("pedido_recusar", args=[pedido.pk]), {"motivo": "  "})
        self.assertContains(resp, "Informe o motivo da recusa")
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.PENDENTE)
        self.client.post(reverse("pedido_recusar", args=[pedido.pk]), {"motivo": "Sem previsão de compra"})
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.RECUSADO)
        self.assertEqual(pedido.decidido_por, self.gerente)
        self.assertEqual(self.saldo(), 1)

    def test_codigo_de_material_unico(self):
        self.entrar(self.gerente)
        resp = self.client.post(
            reverse("material_novo"),
            {"codigo": "pap-001", "nome": "Outro", "categoria_nome": "Papelaria", "unidade": "un"},
        )
        self.assertContains(resp, "Já existe um material com este código")

    def test_gerencia_cadastra_solicitante_com_setor(self):
        self.entrar(self.gerente)
        self.client.post(
            reverse("solicitante_novo"),
            {"nome": "Carla Teste", "usuario": "carla", "senha": "Carla@98765", "setor": "Laboratório"},
        )
        carla = User.objects.get(username="carla")
        self.assertEqual(carla.perfil.setor.nome, "Laboratório")


class CatalogoTest(BaseTest):
    def test_busca_e_situacao(self):
        Material.objects.create(
            codigo="INF-002", nome="Cartucho preto",
            categoria=Categoria.objects.get(nome="Papelaria"), unidade="un",
        )
        self.entrar(self.ana)
        resp = self.client.get(reverse("catalogo"), {"q": "papel"})
        self.assertContains(resp, "Resma de papel A4")
        self.assertNotContains(resp, "Cartucho preto")
        self.assertContains(resp, "Disponível")
        resp = self.client.get(reverse("catalogo"), {"q": "inf-002"})
        self.assertContains(resp, "Sem estoque")
