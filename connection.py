"""
Motor de reconexão: detecta queda de conexão e refaz login + seleção de
canal automaticamente. Roda numa única thread de background, iniciada
uma vez em main.py.
"""
import time
import pyautogui

import config
import state
import persistence
import ocr
import telegram_notifier

ultimo_canal_index = 0

# Contador de tentativas de reconexão SEGUIDAS que falharam (zera assim
# que uma reconexão dá certo). Usado pra mandar um alerta no Telegram se
# o bot ficar preso tentando reconectar por muito tempo sem conseguir —
# sem isso, ele ficaria tentando silenciosamente pra sempre e o usuário
# só descobriria horas depois (foi exatamente o que aconteceu numa
# sessão noturna).
_falhas_consecutivas = 0
_alerta_ja_enviado = False


def _falhar(motivo):
    """Registra uma falha de reconexão: loga, incrementa o contador, e
    dispara UM alerta no Telegram quando cruza o limite (não fica
    reenviando a cada nova falha, só quando bate o limite pela primeira
    vez depois do último sucesso)."""
    global _falhas_consecutivas, _alerta_ja_enviado
    _falhas_consecutivas += 1
    persistence.log_execucao(
        f"❌ [Reconexão] Falhou ({motivo}). Tentativas consecutivas sem sucesso: {_falhas_consecutivas}."
    )
    if _falhas_consecutivas >= config.MAX_FALHAS_RECONEXAO_CONSECUTIVAS and not _alerta_ja_enviado:
        _alerta_ja_enviado = True
        telegram_notifier.enviar_mensagem_async(
            f"🚨 O Dungeon Helper falhou em reconectar {_falhas_consecutivas} vezes seguidas ({motivo}).\n"
            "Pode estar travado numa tela que ele não reconhece. Dá uma olhada quando puder!"
        )
    return False


def reconectar():
    global ultimo_canal_index, _falhas_consecutivas, _alerta_ja_enviado

    if not persistence.reconexao_ativa:
        persistence.log_execucao(
            "[Aviso] Desconexão detectada, mas o Auto-Reconnect está desativado nas opções."
        )
        return False

    persistence.log_execucao(
        "⚠️ [Reconexão] Desconexão detectada! Ativando protocolo de re-autenticação..."
    )

    print("[Reconexão] Focando janela do Cabal...")
    ocr.focar_janela_cabal()
    time.sleep(0.5)

    print("[Reconexão] Checando popup de Desconectado...")
    caiu_popup, _ = ocr.checar_tela_desconectado(
        config.REGIAO_CHECAGEM_DESCONECTADO
    )
    print(f"[Reconexão] Popup Desconectado detectado: {caiu_popup}")

    if caiu_popup:
        persistence.log_execucao(
            "⚠️ [Reconexão] Desconexão detectada pelo OCR!"
        )

        telegram_notifier.enviar_mensagem_async(
            "⚠️ Dungeon Helper: desconexão detectada! Iniciando reconexão..."
        )

        print("[Reconexão] Clicando em OK do popup Desconectado...")
        pyautogui.click(config.BOTAO_OK_DESCONECTADO)
        time.sleep(1)

    tentativas = 0
    login_ok = False
    while tentativas < config.MAX_TENTATIVAS_LOGIN and not login_ok:
        tentativas += 1
        print(f"[Reconexão] === Tentativa de login {tentativas}/{config.MAX_TENTATIVAS_LOGIN} ===")

        print("[Reconexão] Clicando no campo de senha...")
        pyautogui.click(config.CAMPO_SENHA)
        time.sleep(0.3)

        print("[Reconexão] Digitando senha...")
        pyautogui.typewrite(persistence.senha_salva, interval=0.03)
        time.sleep(0.3)

        print("[Reconexão] Clicando no botão de Login...")
        pyautogui.click(config.BOTAO_LOGIN)
        time.sleep(0.8)

        print("[Reconexão] Checando popup de Login Duplo...")
        login_duplo, texto_login_duplo = ocr.checar_tela_login_duplo(
            config.REGIAO_LOGIN_DUPLO
        )
        if getattr(config, 'DEBUG_OCR_DETECCAO', True):
            print(f"[Debug OCR] Login Duplo — leu: {texto_login_duplo!r} | bateu: {login_duplo}")

        if login_duplo:
            persistence.log_execucao(
                "⚠️ [Reconexão] Login duplo detectado. Confirmando acesso..."
            )
            print("[Reconexão] Clicando em Sim do popup Login Duplo...")
            pyautogui.click(config.BOTAO_SIM_LOGIN_DUPLO)
            time.sleep(1)

        print(f"[Reconexão] Aguardando tela de canal aparecer (timeout={config.TIMEOUT_ESPERA_TELA_CANAL_APOS_LOGIN}s)...")
        login_ok = ocr.esperar_tela_aparecer(
            ocr.ainda_na_tela_canal, config.REGIAO_VERIFICACAO_TELA,
            timeout=config.TIMEOUT_ESPERA_TELA_CANAL_APOS_LOGIN
        )
        print(f"[Reconexão] Tela de canal apareceu: {login_ok}")

    if not login_ok:
        print("[Reconexão] Esgotou tentativas de login sem sucesso.")
        return _falhar("não conseguiu logar de volta")

    canal_prioritario = config.CANAIS_BASE[ultimo_canal_index]
    canais_ordenados = [canal_prioritario] + [
        c for idx, c in enumerate(config.CANAIS_BASE) if idx != ultimo_canal_index
    ]

    sucesso = False
    for nome_canal, coord_canal in canais_ordenados:
        print(f"[Reconexão] Tentando entrar no canal '{nome_canal}'...")
        pyautogui.click(coord_canal)
        time.sleep(0.3)

        print("[Reconexão] Clicando em Conectar...")
        pyautogui.click(config.BOTAO_CONECTAR)
        time.sleep(config.TEMPO_ESPERA_APOS_CLICAR_CANAL)

        print(f"[Reconexão] Aguardando tela de canal sumir (timeout={config.TIMEOUT_ESPERA_CANAL_CONECTAR}s)...")
        if ocr.esperar_tela_sumir(
            ocr.ainda_na_tela_canal, config.REGIAO_VERIFICACAO_TELA,
            timeout=config.TIMEOUT_ESPERA_CANAL_CONECTAR
        ):
            print(f"[Reconexão] Canal '{nome_canal}' conectado com sucesso.")
            ultimo_canal_index = config.CANAIS_BASE.index((nome_canal, coord_canal))
            sucesso = True
            break
        else:
            print(f"[Reconexão] Canal '{nome_canal}' NÃO conectou dentro do timeout.")

    if not sucesso:
        print("[Reconexão] Nenhum canal conseguiu conectar.")
        return _falhar("não conseguiu entrar em nenhum canal")

    print("[Reconexão] Aguardando 2s antes de clicar em Começar...")
    time.sleep(2)

    print("[Reconexão] Clicando em Começar...")
    pyautogui.click(config.BOTAO_COMECAR)
    time.sleep(0.3)

    print("[Reconexão] Pressionando Enter...")
    pyautogui.press("enter")

    print(f"[Reconexão] Aguardando carregamento pós-login ({config.TEMPO_CARREGAMENTO_APOS_LOGIN}s)...")
    time.sleep(5.0)

    
    print("[Reconexão] Pressionando F7 para retomar a DG...")
    pyautogui.press("f7")
    time.sleep(0.3)


    _falhas_consecutivas = 0
    _alerta_ja_enviado = False
    persistence.log_execucao("✅ [Reconexão] Login e canal recuperados com sucesso.")
    return True

def thread_monitoramento_conexao():
    """Roda UMA ÚNICA VEZ durante toda a vida do app (chamada em
    main.py). Nunca é recriada a cada execução da fila."""
    while True:
        time.sleep(config.INTERVALO_CHECAGEM_SEGUNDOS)
        if not persistence.reconexao_ativa or not state.evento_fila_rodando.is_set():
            continue
        caiu = False
        try:
            caiu_popup, _ = ocr.checar_tela_desconectado(config.REGIAO_CHECAGEM_DESCONECTADO)
            if caiu_popup:
                caiu = True
            else:
                caiu_login, _ = ocr.checar_tela_login(config.REGIAO_CHECAGEM_LOGIN)
                if caiu_login:
                    caiu = True
        except Exception:
            continue
        if caiu:
            state.evento_reconectando.set()
            try:
                with state.lock_tela:
                    reconectar()
            finally:
                state.evento_reconectando.clear()
