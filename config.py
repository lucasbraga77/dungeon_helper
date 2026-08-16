
"""
Configurações gerais do aplicativo e template padrão do repositório de DGs.

As coordenadas NÃO ficam mais neste arquivo.

Cada instalação/usuário deve realizar o próprio mapeamento pelo aplicativo,
e essas coordenadas são salvas em dungeon_helper_config.json.

O REPOSITORIO_PADRAO contém somente informações estruturais das DGs:
- nome
- categoria
- tempo_base padrão

Nenhuma coordenada específica de resolução fica neste arquivo.
"""

import os
import sys


# ============================================================
# CONFIGURAÇÕES GERAIS
# ============================================================

TITULO_JANELA_CABAL = "Cabal"
VERSAO_ATUAL = "1.0.0"

# ============================================================
# CAMINHO DOS ARQUIVOS PERSISTENTES
# ============================================================

def _pasta_base():
    """
    Pasta onde o aplicativo está instalado.

    Quando estiver rodando como .exe, usa a pasta do executável.
    Quando estiver rodando pelo Python, usa a pasta deste arquivo.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    return os.path.dirname(os.path.abspath(__file__))


CONFIG_FILE = os.path.join(
    _pasta_base(),
    "dungeon_helper_config.json"
)


# Arquivo onde as detecções automáticas de fim de DG são registradas.
LOG_DETECCOES_FILE = os.path.join(
    _pasta_base(),
    "deteccoes_dg.txt"
)


# Log geral de execução.
LOG_EXECUCAO_FILE = os.path.join(
    _pasta_base(),
    "log_execucao.txt"
)


# ============================================================
# RECONEXÃO
# ============================================================

MAX_FALHAS_RECONEXAO_CONSECUTIVAS = 3

LIMITE_ALERTA_RECONEXAO_SEGUNDOS = 60


# ============================================================
# TELEGRAM
# ============================================================

# Mantenha aqui o mesmo token que já existe no seu config.py atual.
TELEGRAM_BOT_TOKEN = "8863708030:AAFXYLWd0HlhFZ_m7t6RbYHvNzWg8c4JeA4"

TELEGRAM_BOT_USERNAME = "@CabalneoBot"


# ============================================================
# MAPEAMENTO
# ============================================================
#
# Estes são os pontos/regiões que o usuário precisa capturar.
#
# Os valores reais NÃO ficam mais neste arquivo.
# Eles serão carregados do dungeon_helper_config.json.
#

MAPEAMENTO_KEYS = [
    "BOTAO_INICIAR",
    "BOTAO_ABA_INICIANTE",
    "BOTAO_ABA_INTERMEDIARIO",
    "BOTAO_ABA_AVANCADO",

    "REGIAO_CHECAGEM_DESCONECTADO",
    "BOTAO_OK_DESCONECTADO",

    "REGIAO_CHECAGEM_LOGIN",
    "CAMPO_SENHA",
    "BOTAO_LOGIN",
    "REGIAO_LOGIN_DUPLO",
    "BOTAO_SIM_LOGIN_DUPLO",


    "CANAL_3",
    "BOTAO_CONECTAR",

    "REGIAO_VERIFICACAO_TELA",
    "BOTAO_COMECAR",

    "REGIAO_CHECAGEM_DG_FINALIZADA",
]


# ============================================================
# COORDENADAS INICIAIS
# ============================================================
#
# Não existem mais coordenadas padrão de resolução.
#
# O usuário deverá realizar o mapeamento pelo aplicativo.
#

BOTAO_INICIAR = None

BOTAO_ABA_INICIANTE = None
BOTAO_ABA_INTERMEDIARIO = None
BOTAO_ABA_AVANCADO = None

REGIAO_CHECAGEM_DESCONECTADO = None
BOTAO_OK_DESCONECTADO = None

REGIAO_CHECAGEM_LOGIN = None
CAMPO_SENHA = None
BOTAO_LOGIN = None
REGIAO_LOGIN_DUPLO = None
BOTAO_SIM_LOGIN_DUPLO = None

CANAL_3 = None
BOTAO_CONECTAR = None

REGIAO_VERIFICACAO_TELA = None
BOTAO_COMECAR = None

REGIAO_CHECAGEM_DG_FINALIZADA = None


# ============================================================
# COMPATIBILIDADE COM O PERSISTENCE ATUAL
# ============================================================
#
# A lógica antiga de resolução foi removida.
#
# Estes símbolos permanecem temporariamente para que o
# persistence.py atual não quebre antes de ser atualizado.
#
# Eles NÃO representam mais uma resolução real.
#

RESOLUCAO_PADRAO = None
RESOLUCAO_CALIBRADA = None

RESOLUCOES_DISPONIVEIS = []

PERFIS_RESOLUCAO = {}


def aplicar_perfil_resolucao(perfil=None):
    """
    Compatibilidade com o persistence.py antigo.

    A antiga lógica de perfis de resolução foi desativada.
    As coordenadas agora vêm exclusivamente do mapeamento
    salvo pelo usuário.
    """
    global RESOLUCAO_CALIBRADA

    RESOLUCAO_CALIBRADA = None


# ============================================================
# CATEGORIAS DAS DGs
# ============================================================

def _atualizar_abas_categorias():
    """
    Atualiza o mapa das abas utilizando as coordenadas atualmente
    carregadas pelo mapeamento personalizado.
    """
    global ABAS_CATEGORIAS

    ABAS_CATEGORIAS = {
        "iniciante": BOTAO_ABA_INICIANTE,
        "intermediario": BOTAO_ABA_INTERMEDIARIO,
        "avancado": BOTAO_ABA_AVANCADO,
    }


ABAS_CATEGORIAS = {
    "iniciante": None,
    "intermediario": None,
    "avancado": None,
}


# ============================================================
# CONVERSÃO DE LISTAS PARA TUPLAS
# ============================================================

def _to_tuples(value):
    """
    Converte listas vindas do JSON para tuplas.

    Exemplo:

        [100, 200]

    vira:

        (100, 200)

    E regiões:

        [100, 200, 300, 400]

    viram:

        (100, 200, 300, 400)
    """
    if isinstance(value, list):
        return tuple(_to_tuples(v) for v in value)

    if isinstance(value, dict):
        return {
            k: _to_tuples(v)
            for k, v in value.items()
        }

    return value


# ============================================================
# APLICAÇÃO DO MAPEAMENTO DO USUÁRIO
# ============================================================

def aplicar_mapeamento_personalizado(mapeamentos):
    """
    Aplica as coordenadas capturadas pelo usuário.

    O JSON possui as coordenadas separadas do REPOSITORIO_PADRAO.

    Exemplo:

        {
            "BOTAO_LOGIN": [951, 719],
            "Estação Ruína": [805, 388]
        }

    As coordenadas são aplicadas diretamente às variáveis
    utilizadas pelo restante do programa.
    """

    global BOTAO_INICIAR
    global BOTAO_ABA_INICIANTE
    global BOTAO_ABA_INTERMEDIARIO
    global BOTAO_ABA_AVANCADO

    global REGIAO_CHECAGEM_DESCONECTADO
    global BOTAO_OK_DESCONECTADO

    global REGIAO_CHECAGEM_LOGIN
    global CAMPO_SENHA
    global BOTAO_LOGIN
    global REGIAO_LOGIN_DUPLO
    global BOTAO_SIM_LOGIN_DUPLO

    global CANAL_3
    global BOTAO_CONECTAR

    global REGIAO_VERIFICACAO_TELA
    global BOTAO_COMECAR
    global REGIAO_CHECAGEM_DG_FINALIZADA

    global CANAIS_BASE

    if not isinstance(mapeamentos, dict):
        return

    for chave, valor in mapeamentos.items():

        # Coordenadas armazenadas no JSON são listas.
        # O restante do programa trabalha com tuplas.
        valor = _to_tuples(valor)

        # O REPOSITORIO_PADRAO NÃO deve mais ser sobrescrito
        # pelas coordenadas do usuário.
        #
        # Caso exista um arquivo antigo contendo essa chave,
        # simplesmente ignoramos para evitar que coordenadas
        # antigas contaminem o novo repositório.
        if chave == "REPOSITORIO_PADRAO":
            continue

        # CANAIS_BASE continua sendo tratado separadamente
        # para manter compatibilidade com versões anteriores.
        elif chave == "CANAIS_BASE":
            try:
                CANAIS_BASE = [
                    (nome, tuple(coord))
                    for nome, coord in valor
                ]
            except Exception:
                pass

        else:
            # Só aplica variáveis que realmente existem no config.
            if chave in MAPEAMENTO_KEYS:
                globals()[chave] = valor

    # Se CANAL_3 foi capturado, mantém CANAIS_BASE sincronizado.
    if CANAL_3 is not None:
        CANAIS_BASE = [
            ("Canal 3", CANAL_3)
        ]

    _atualizar_abas_categorias()


# ============================================================
# RECURSOS DO APLICATIVO
# ============================================================

ASSETS_DIR = "assets"

IMAGEM_REFERENCIA_UI = os.path.join(
    ASSETS_DIR,
    "config_ui_referencia.png"
)


def resource_path(relative_path):
    """
    Retorna o caminho absoluto de um recurso.

    Funciona tanto executando pelo Python quanto pelo .exe
    empacotado com PyInstaller.
    """

    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(
            os.path.abspath(__file__)
        )

    return os.path.join(
        base_path,
        relative_path
    )


# ============================================================
# TEXTOS UTILIZADOS PELO OCR
# ============================================================

TEXTO_TELA_LOGIN = "Login de Conta"

TEXTO_TELA_DESCONECTADO = "Desconectado"

TEXTO_TELA_LOGIN_DUPLO = "Duplo"

TEXTO_TELA_CANAL = "Selecionar Servidor"

TEXTO_DG_FINALIZADA = "não possui entradas"


# ============================================================
# OCR / DETECÇÃO
# ============================================================

INTERVALO_CHECAGEM_DG_FINALIZADA = 4

INTERVALO_HEARTBEAT_SEGUNDOS = 600

DEBUG_OCR_DETECCAO = True

TEMPO_MINIMO_ANTES_DETECCAO_SEGUNDOS = 30


# ============================================================
# TEMPOS GERAIS DO MOTOR
# ============================================================

INTERVALO_CHECAGEM_SEGUNDOS = 5

TEMPO_CARREGAMENTO_APOS_LOGIN = 15

TEMPO_ESPERA_APOS_CLICAR_CANAL = 2

TIMEOUT_ESPERA_TELA_CANAL_APOS_LOGIN = 15

TIMEOUT_ESPERA_CANAL_CONECTAR = 8

MAX_TENTATIVAS_LOGIN = 3


# ============================================================
# CANAIS
# ============================================================

CANAIS_BASE = []


# ============================================================
# PALETA / FONTES
# ============================================================

COLOR_BG = "#f4f6fa"

COLOR_HEADER_BG = "#243447"

COLOR_BOTTOM_BG = "#eef1f5"

COLOR_SELECTED = "#dbeeff"

COLOR_RUNNING = "#fff3cd"

COLOR_MUTED = "#7f8c8d"

COLOR_ACCENT = "#2980b9"

COLOR_SUCCESS = "#27ae60"

COLOR_DANGER = "#c0392b"

COLOR_SKIP = "#f39c12"


FONT_BASE = ("Segoe UI", 9)

FONT_BOLD = ("Segoe UI", 9, "bold")

FONT_TINY = ("Segoe UI", 7)

FONT_TINY_BOLD = ("Segoe UI", 7, "bold")


# ============================================================
# REPOSITÓRIO PADRÃO DE DGs
# ============================================================
#
# IMPORTANTE:
#
# Aqui ficam somente os dados ESTRUTURAIS das DGs.
#
# Não existe mais "coord".
#
# As coordenadas são responsabilidade do
# dungeon_helper_config.json de cada usuário.
#
# Os tempos abaixo continuam existindo como valores padrão.
# O persistence.py pode sobrescrevê-los pelos valores salvos
# no JSON do usuário.
# ============================================================

REPOSITORIO_PADRAO = {

    # ------------------ INICIANTES (Aba 1) ------------------

    "Estação Ruína": {
        "categoria": "iniciante",
        "tempo_base": 2.1
    },

    "Cidadela Vulcânica": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Templo Esquecido 1SS": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Ilha Proibida": {
        "categoria": "iniciante",
        "tempo_base": 5.0
    },

    "Altar de Siena 1SS": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Castelo das Ilusões": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Caverna do Pânico(Premium)": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Locomotiva Louca(Premium)": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Catacumba Gélida(Premium)": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Morada das Chamas Infernais(Premium)": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Morada das Chamas Infernais(Desperto)": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Caverna do Pânico(Desperto)": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Locomotiva Fantasma(Desperto)": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Catacumba Gélida(Desperto)": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Pandemônio": {
        "categoria": "iniciante",
        "tempo_base": 3.5
    },

    "Moinho Sagrado": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },

    "Torre Gélida dos Mortos 1SS": {
        "categoria": "iniciante",
        "tempo_base": 2.0
    },


    # ------------------ INTERMEDIÁRIAS (Aba 2) ------------------

    "Templo Esquecido 2SS": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Altar de Siena 2SS": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Posto Avançado de Máquinas": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Torre dos Mortos 3SS": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Templo Esquecido 2SS (Desperto)": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Vale Tempestuoso (Desperto)": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Torre dos Mortos 3SS (Parte 2)": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Castelo das Ilusões (Apócrifos)": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Salão Radiante do Castelo (Apócrifos)": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Crista Ilusória": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Arena Acheron": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Torre Diabólica": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Torre Diabólica (Parte 2)": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Keldrasil Sagrado": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },

    "Salão Radiante do Castelo": {
        "categoria": "intermediario",
        "tempo_base": 5.0
    },


    # ------------------ AVANÇADAS (Aba 3) ------------------

    "Cidade Abandonada": {
        "categoria": "avancado",
        "tempo_base": 5.0
    },

    "Templo Esquecido 3SS": {
        "categoria": "avancado",
        "tempo_base": 5.0
    },

    "Ilha da Miragem": {
        "categoria": "avancado",
        "tempo_base": 5.0
    },

    "Solo Flamejante": {
        "categoria": "avancado",
        "tempo_base": 5.0
    },

    "Tumba Ancestral": {
        "categoria": "avancado",
        "tempo_base": 5.0
    },

    "Desfiladeiro Congelado": {
        "categoria": "avancado",
        "tempo_base": 5.0
    },

    "Terminus Machina": {
        "categoria": "avancado",
        "tempo_base": 5.0
    },

    "Celestia": {
        "categoria": "avancado",
        "tempo_base": 5.0
    },
}