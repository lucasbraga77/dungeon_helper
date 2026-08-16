"""
Envio de notificações para o Telegram.

- Não precisa instalar requests.
- Utiliza apenas a biblioteca padrão do Python.
- Permite descobrir automaticamente o Chat ID do usuário.
"""

import json
import secrets
import threading
import urllib.parse
import urllib.request

import config
import persistence


# ============================================================
# UTILIDADES
# ============================================================

def _token(token=None):
    """Retorna o token informado ou o padrão (centralizado em config.py)."""
    return token or config.TELEGRAM_BOT_TOKEN


def _prefixar_nome(texto):
    """
    Prefixa a mensagem com o nome do personagem, se configurado.

    Exemplo:
        [Lukas]

        <mensagem>
    """
    nome = getattr(persistence, "nome_personagem", "").strip()
    if nome:
        return f"[{nome}]\n\n{texto}"
    return texto


# ============================================================
# GERACAO DO CODIGO DE VINCULACAO
# ============================================================

def gerar_codigo():
    """
    Gera um codigo que o usuario devera enviar para o bot.

    Exemplo:
        TG-9AF31C
    """
    return "TG-" + secrets.token_hex(3).upper()


# ============================================================
# CONSULTAR UPDATES
# ============================================================

def obter_updates(token=None, limit=100):
    """
    Obtem as mensagens mais recentes recebidas pelo bot.

    Usa offset=-<limit> para buscar as ultimas mensagens sem confirma-las,
    garantindo que multiplas instancias (PCs diferentes) consigam ler
    as mesmas mensagens sem que uma consuma a fila da outra.
    """
    token = _token(token)

    try:
        url = (
            f"https://api.telegram.org/bot{token}/getUpdates"
            f"?offset=-{limit}&limit={limit}"
        )

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            dados = json.loads(resp.read().decode("utf-8"))

        if not dados.get("ok"):
            return False, dados

        return True, dados.get("result", [])

    except Exception as e:
        return False, str(e)


# ============================================================
# PROCURAR CHAT ID PELO CODIGO
# ============================================================

def procurar_chat_id(codigo, token=None):
    """
    Procura uma mensagem igual ao codigo informado entre os ultimos updates.

    Percorre do mais recente para o mais antigo para encontrar a mensagem
    mais proxima ao momento da vinculacao.
    """
    ok, updates = obter_updates(token)

    if not ok:
        return False, updates

    codigo_limpo = codigo.strip().upper()

    for update in reversed(updates):
        mensagem = update.get("message")
        if not mensagem:
            continue

        texto = mensagem.get("text", "").strip().upper()

        if texto == codigo_limpo:
            chat = mensagem.get("chat", {})
            return True, {
                "chat_id":  chat.get("id"),
                "nome":     chat.get("first_name", ""),
                "username": chat.get("username", ""),
            }

    return False, "Codigo nao encontrado."


# ============================================================
# CONECTAR USUARIO (FLUXO COMPLETO)
# ============================================================

def conectar_usuario(
    codigo,
    token=None,
    intervalo_segundos=2,
    timeout_segundos=300,
    callback_status=None,
):
    """
    Orquestra o fluxo completo de vinculacao: fica consultando getUpdates
    a cada `intervalo_segundos` ate encontrar uma mensagem igual a `codigo`
    ou ate estourar `timeout_segundos` (padrao 5 minutos).

    E uma chamada BLOQUEANTE -- quem chamar isso de uma GUI (tkinter, etc.)
    deve rodar numa thread separada.

    Ao encontrar o codigo:
        - Atualiza persistence.telegram_chat_id / telegram_nome /
          telegram_username / telegram_ativo (em memoria).
        - Envia mensagem automatica de confirmacao para o Telegram.

    Retorna:
        (True, {"chat_id": ..., "nome": ..., "username": ...})
    ou
        (False, "Usuario ja esta conectado." | "Tempo esgotado. Gere um novo codigo." | erro)

    ATENCAO -- multiplos PCs:
        Cada PC precisa fazer o fluxo de vinculacao individualmente, pois
        o chat_id fica salvo no dungeon_helper_config.json LOCAL de cada
        maquina. O bot Telegram e compartilhado, mas o JSON nao e.
        Se o usuario ja enviou o codigo ao bot anteriormente, o app ainda
        consegue encontra-lo via getUpdates (offset negativo nao consome
        a fila), desde que a mensagem esteja entre as ultimas 100 recebidas.
        Se a mensagem for mais antiga que isso, basta enviar o codigo
        novamente ao bot.
    """
    import time

    if persistence.telegram_ativo and persistence.telegram_chat_id:
        return False, "Usuario ja esta conectado ao Telegram."

    inicio = time.time()

    while time.time() - inicio < timeout_segundos:

        ok, resultado = procurar_chat_id(codigo, token)

        if ok:
            persistence.telegram_chat_id  = str(resultado["chat_id"])
            persistence.telegram_nome     = resultado["nome"]
            persistence.telegram_username = resultado["username"]
            persistence.telegram_ativo    = True

            enviar_mensagem(
                "Conta vinculada com sucesso ao Cabal Helper!\n"
                "Voce recebera os alertas das DGs por aqui.",
                token=token,
                chat_id=persistence.telegram_chat_id,
            )

            return True, resultado

        if callback_status:
            callback_status("Aguardando confirmacao no Telegram...")

        time.sleep(intervalo_segundos)

    return False, "Tempo esgotado. Gere um novo codigo."


# ============================================================
# LISTAR CHATS (OPCIONAL)
# ============================================================

def obter_chat_ids(token=None):
    """
    Lista todos os usuarios que ja conversaram com o bot.
    """
    ok, updates = obter_updates(token)

    if not ok:
        return False, updates

    usuarios = []
    vistos   = set()

    for item in updates:
        mensagem = item.get("message")
        if not mensagem:
            continue

        chat    = mensagem.get("chat", {})
        chat_id = chat.get("id")

        if chat_id in vistos:
            continue

        vistos.add(chat_id)
        usuarios.append({
            "chat_id":  chat_id,
            "nome":     chat.get("first_name", ""),
            "username": chat.get("username", ""),
        })

    return True, usuarios


# ============================================================
# ENVIAR MENSAGEM
# ============================================================

def enviar_mensagem(texto, token=None, chat_id=None):
    """
    Envia uma mensagem imediatamente.
    """
    token   = _token(token)
    chat_id = chat_id or persistence.telegram_chat_id

    texto = _prefixar_nome(texto)

    if not chat_id:
        return False, "Chat ID nao configurado."

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"

        dados = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text":    texto,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=dados, method="POST")

        with urllib.request.urlopen(req, timeout=10) as resp:
            corpo = json.loads(resp.read().decode("utf-8"))

        if corpo.get("ok"):
            return True, "Mensagem enviada com sucesso."

        return False, corpo.get("description", "Erro desconhecido.")

    except Exception as e:
        return False, str(e)


# ============================================================
# ENVIO ASSINCRONO
# ============================================================

def enviar_mensagem_async(texto):
    """
    Envia a mensagem em background -- nao bloqueia a interface.
    """
    if not persistence.telegram_ativo:
        return

    threading.Thread(
        target=enviar_mensagem,
        args=(texto,),
        daemon=True,
    ).start()


# ============================================================
# DESCONECTAR USUARIO
# ============================================================

def desconectar_usuario():
    """
    Remove a vinculacao atual do Telegram (limpa chat_id, nome, username
    e desativa o envio de notificacoes). Persiste a mudanca no JSON para
    nao voltar depois de reiniciar o app.
    """
    persistence.telegram_ativo    = False
    persistence.telegram_chat_id  = ""
    persistence.telegram_nome     = ""
    persistence.telegram_username = ""

    try:
        persistence.salvar_historico_json(
            saved_times={
                k: v["tempo_base"]
                for k, v in persistence.repositorio_dinamico.items()
            },
            ordem=persistence.fila_salva_ordem,
            senha=persistence.senha_salva,
            active=persistence.reconexao_ativa,
            multiplicadores=persistence.multiplicadores_salvos,
            historico=persistence.historico_execucoes,
            deteccao_auto=persistence.deteccao_automatica_ativa,
            tg_ativo=False,
            tg_chat="",
            tg_nome="",
            tg_username="",
            mapeamento_personalizado=persistence.mapeamento_personalizado,
        )
        return True, "Conta desvinculada com sucesso."
    except Exception as e:
        return False, str(e)
