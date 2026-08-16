"""
Tudo relacionado a "enxergar a tela": OCR (easyocr) e foco de janela.
Nenhuma lógica de decisão mora aqui, só leitura bruta.
"""
import os
import sys
import time
import unicodedata
import ctypes
import pyautogui
import pygetwindow as gw
import easyocr
import numpy as np

import config

# --- CORREÇÃO DE DPI (Essencial para o .exe não cortar a tela no lugar errado) ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDpiAware()
    except Exception:
        pass


def _obter_caminho_modelos_easyocr():
    """Retorna o diretório de modelos dando PRIORIDADE MÁXIMA ao executável empacotado."""
    candidatos = []

    # 1. Se estiver rodando empacotado via .exe (PyInstaller/cx_Freeze)
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        candidatos.append(os.path.join(exe_dir, "easyocr_models", "model"))
        if hasattr(sys, "_MEIPASS"):
            candidatos.append(os.path.join(sys._MEIPASS, "easyocr_models", "model"))

    # 2. Se estiver rodando via script (Dev / VS Code)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidatos.append(os.path.join(base_dir, "easyocr_models", "model"))
    candidatos.append(os.path.join(base_dir, "easyocr_models"))
    candidatos.append(os.path.join(base_dir, "assets", "easyocr_models"))

    # 3. Fallback: Pasta de cache padrão do usuário no Windows
    candidatos.append(os.path.join(os.path.expanduser("~"), ".EasyOCR", "model"))

    for caminho in candidatos:
        if os.path.isdir(caminho):
            # Valida se a pasta realmente possui arquivos .pth do EasyOCR
            files = os.listdir(caminho)
            if any(f.endswith(".pth") for f in files):
                return caminho

    return None


MODEL_DIR = _obter_caminho_modelos_easyocr()
reader = None

print(f"[OCR LOG] Diretório de modelos localizado: {MODEL_DIR}")

# Inicialização com fallback transparente e logs
try:
    if MODEL_DIR:
        reader = easyocr.Reader(
            ["pt", "en"],
            gpu=False,
            model_storage_directory=MODEL_DIR,
            download_enabled=False,
        )
    else:
        print("[OCR ALERTA] Nenhum modelo local encontrado! Tentando modo padrão...")
        reader = easyocr.Reader(["pt", "en"], gpu=False, download_enabled=True)
except Exception as e:
    print(f"[OCR ERRO CRÍTICO] Falha ao inicializar o Reader do EasyOCR: {e}")
    reader = None


def _normalizar(texto):
    """Minúsculo e SEM acento — importante porque o OCR frequentemente
    lê 'não' como 'nao' (perde o til). Normalizando os dois lados da
    comparação (o texto lido e o texto alvo) esse tipo de erro comum
    deixa de causar falha de detecção."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def ler_texto_da_regiao(regiao):
    if reader is None:
        print("[OCR ERRO] Operação abortada: Reader não foi inicializado.")
        return ""

    try:
        x1, y1, x2, y2 = regiao
        screenshot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
        
        # Pré-processamento: escala de cinza + upscale 2x.
        screenshot = screenshot.convert("L").resize(
            (screenshot.width * 2, screenshot.height * 2)
        )
        img_np = np.array(screenshot)
        resultados = reader.readtext(img_np)
        
        texto_capturado = " ".join([res[1] for res in resultados])
        return texto_capturado
    except Exception as e:
        print(f"[OCR ERRO] Falha ao capturar/processar imagem na região {regiao}: {e}")
        return ""


def focar_janela_cabal():
    janelas = gw.getWindowsWithTitle(config.TITULO_JANELA_CABAL)
    if janelas:
        try:
            if janelas[0].isMinimized:
                janelas[0].restore()
            janelas[0].activate()
            time.sleep(0.5)
        except Exception:
            pass


def ainda_na_tela_canal(regiao):
    return _normalizar(config.TEXTO_TELA_CANAL) in _normalizar(ler_texto_da_regiao(regiao))


def checar_tela_login(regiao):
    txt = ler_texto_da_regiao(regiao)
    return _normalizar(config.TEXTO_TELA_LOGIN) in _normalizar(txt), txt


def checar_tela_desconectado(regiao):
    txt = ler_texto_da_regiao(regiao)
    return _normalizar(config.TEXTO_TELA_DESCONECTADO) in _normalizar(txt), txt

from difflib import SequenceMatcher

def checar_tela_login_duplo(regiao):
    txt = ler_texto_da_regiao(regiao)
    alvo = _normalizar(config.TEXTO_TELA_LOGIN_DUPLO)
    lido = _normalizar(txt)
    similaridade = SequenceMatcher(None, alvo, lido).ratio()
    bateu = alvo in lido or similaridade > 0.5
    return bateu, txt


def checar_dg_finalizada(regiao):
    """True/False + o texto bruto lido (pra quem chamar poder logar em
    modo debug e entender por que bateu ou não bateu). Checa 'nao' e
    'entradas' como duas palavras-chave separadas (em vez da frase
    inteira 'não possui entradas') — mais tolerante a erros de OCR que
    quebram ou alteram palavras no meio da frase."""
    txt = ler_texto_da_regiao(regiao)
    norm = _normalizar(txt)
    return ("nao" in norm and "entradas" in norm), txt


def esperar_tela_aparecer(checar_func, regiao, timeout=15):
    inicio = time.time()
    while time.time() - inicio < timeout:
        if checar_func(regiao):
            return True
        if getattr(config, 'DEBUG_OCR_DETECCAO', True):
            texto_debug = ler_texto_da_regiao(regiao)
            print(f"[Debug OCR] esperar_tela_aparecer — leu: {texto_debug!r}")
        time.sleep(1)
    return False


def esperar_tela_sumir(checar_func, regiao, timeout=15):
    inicio = time.time()
    while time.time() - inicio < timeout:
        if not checar_func(regiao):
            return True
        time.sleep(1)
    return False