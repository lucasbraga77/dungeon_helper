"""
Motor que efetivamente clica no jogo e espera. Não sabe nada de tkinter —
só recebe callbacks opcionais pra avisar quando uma DG começa/termina,
que a interface usa pra atualizar a tela.
"""
import time
import datetime
import ctypes
import traceback
from ctypes import wintypes
import pyautogui

import config
import state
import ocr
import persistence
import telegram_notifier

user32 = ctypes.windll.user32
VK_LBUTTON = 0x01


def _aguardar_ciclo(tempo_espera_segundos, nome_dg=None, callback_deteccao=None, multiplicador=None):
    inicio = time.time()
    pausado_acumulado = 0.0
    reconectando_acumulado = 0.0
    ultima_checagem = -config.INTERVALO_CHECAGEM_DG_FINALIZADA
    ultimo_heartbeat = 0.0
    alerta_reconexao_enviado = False

    while True:
        if state.evento_abortar.is_set():
            return

        if state.evento_pular_dg.is_set():
            state.evento_pular_dg.clear()
            persistence.log_execucao(f"[Pular] '{nome_dg}' interrompida manualmente pelo usuário.")
            print("[Pular] Aguardando clique na tela do jogo pra focar antes de continuar...")
            _aguardar_clique_manual()
            return

        if state.evento_pausado.is_set():
            inicio_pausa = time.time()
            while state.evento_pausado.is_set():
                if state.evento_abortar.is_set():
                    return
                time.sleep(0.3)
            pausado_acumulado += time.time() - inicio_pausa
            continue

        if state.evento_reconectando.is_set():
            inicio_reconexao = time.time()
            while state.evento_reconectando.is_set():
                time.sleep(0.3)
            reconectando_acumulado += time.time() - inicio_reconexao
            if (reconectando_acumulado >= config.LIMITE_ALERTA_RECONEXAO_SEGUNDOS
                    and not alerta_reconexao_enviado):
                alerta_reconexao_enviado = True
                persistence.log_execucao(
                    f"⚠️ '{nome_dg}': já são {int(reconectando_acumulado )} min gastos reconectando "
                    f"durante essa espera — conexão parece instável."
                )
                telegram_notifier.enviar_mensagem_async(
                    f"⚠️ '{nome_dg}' já gastou {int(reconectando_acumulado )} min reconectando "
                    "durante a espera. A conexão pode estar instável — vale dar uma olhada."
                )
            continue

        tempo_ativo = (time.time() - inicio) - pausado_acumulado - reconectando_acumulado

        if tempo_ativo >= tempo_espera_segundos:
            break  # esgotou o tempo estimado sem detectar (ou detecção desligada)

        if tempo_ativo - ultimo_heartbeat >= config.INTERVALO_HEARTBEAT_SEGUNDOS:
            ultimo_heartbeat = tempo_ativo
            persistence.log_execucao(
                f"💓 [Heartbeat] '{nome_dg}': {int(tempo_ativo // 60)}/{tempo_espera_segundos // 60} min "
                f"passados (tempo real), bot ativo e contando normalmente."
            )

        # ====================================================================
        # 🔍 CHECAGEM DO OCR (AGORA CORRETAMENTE DENTRO DO LOOP DE ESPERA)
        # ====================================================================
        if (persistence.deteccao_automatica_ativa
                and tempo_ativo >= config.TEMPO_MINIMO_ANTES_DETECCAO_SEGUNDOS
                and tempo_ativo - ultima_checagem >= config.INTERVALO_CHECAGEM_DG_FINALIZADA):
            
            ultima_checagem = tempo_ativo
            try:
                encontrou, texto_lido = ocr.checar_dg_finalizada(config.REGIAO_CHECAGEM_DG_FINALIZADA)
                
                if getattr(config, 'DEBUG_OCR_DETECCAO', True):
                    print(f"[Debug OCR] '{nome_dg}' aos {tempo_ativo:.0f}s (real) — leu: {texto_lido!r} | bateu: {encontrou}")

                if encontrou:
                    tempo_ativo_final = (time.time() - inicio) - pausado_acumulado - reconectando_acumulado
                    tempo_estimado_min = tempo_espera_segundos / 60
                    tempo_real_min = tempo_ativo_final / 60
                    diferenca_min = tempo_estimado_min - tempo_real_min
                    percentual = (diferenca_min / tempo_estimado_min * 100) if tempo_estimado_min > 0 else 0

                    persistence.log_execucao(
                        f"🔍 [Detecção] '{nome_dg}' finalizada em {tempo_real_min:.1f} min "
                        f"(estimado: {tempo_estimado_min:.1f} min — {percentual:.0f}% de folga no tempo programado)."
                    )
                    persistence.registrar_deteccao_arquivo(
                        nome_dg, tempo_estimado_min, tempo_real_min, diferenca_min, percentual, multiplicador
                    )

                    # Atualização automática no JSON
                    try:
                        medias = persistence.calcular_medias_por_dg()
                        if nome_dg in medias:
                            novo_tempo_base = round(medias[nome_dg]["media_tempo_base"], 1)
                            persistence.repositorio_dinamico[nome_dg]["tempo_base"] = novo_tempo_base

                            tempos_atualizados = {k: v["tempo_base"] for k, v in persistence.repositorio_dinamico.items()}
                            persistence.salvar_historico_json(
                                saved_times=tempos_atualizados,
                                ordem=persistence.fila_salva_ordem,
                                senha=persistence.senha_salva,
                                active=persistence.reconexao_ativa,
                                multiplicadores=persistence.multiplicadores_salvos,
                                historico=persistence.historico_execucoes
                            )
                            persistence.log_execucao(f"🧠 [Aprendizado] Tempo base da '{nome_dg}' atualizado para {novo_tempo_base} min no JSON.")
                    except Exception as err_tempo:
                        persistence.log_execucao(f"[Aviso] Falha ao recalcular tempo base de '{nome_dg}': {err_tempo}")

                    telegram_notifier.enviar_mensagem_async(
                        f"🔍 '{nome_dg}' finalizada em {tempo_real_min:.1f} min "
                        f"(estimado: {tempo_estimado_min:.1f} min, {percentual:.0f}% de folga)."
                    )
                    if callback_deteccao:
                        callback_deteccao(nome_dg, tempo_estimado_min, tempo_real_min, diferenca_min, percentual)
                    
                    time.sleep(1.5)
                    return  # Sai da função pois a DG foi finalizada!
            except Exception as e:
                print("\n" + "!"*50)
                print(f"[ERRO NO OCR] Falha ao checar DG '{nome_dg}': {e}")
                traceback.print_exc()
                print("!"*50 + "\n")
                persistence.log_execucao(f"[Aviso] Falha na checagem automática de finalização de '{nome_dg}': {e}")

        time.sleep(0.5)

    # Chegou no teto de tempo sem detectar
    if reconectando_acumulado > 0:
        persistence.log_execucao(
            f"[Info] '{nome_dg}': {int(reconectando_acumulado // 60)} min do tempo total foram gastos reconectando."
        )
    if persistence.deteccao_automatica_ativa:
        persistence.log_execucao(
            f"[Aviso] '{nome_dg}' não foi detectada finalizada — usou o tempo estimado inteiro "
            f"como teto de segurança ({tempo_espera_segundos // 60} min)."
        )
        telegram_notifier.enviar_mensagem_async(
            f"⏳ '{nome_dg}' finalizada pelo tempo estimado ({tempo_espera_segundos // 60} min)."
        )

def _aguardar_pausa():
    """Bloqueia (sem consumir o timer, pois é chamado FORA do ciclo de
    espera) enquanto o app estiver pausado. Usado antes de disparar os
    cliques de uma nova DG, pra não começar uma DG nova enquanto o
    usuário está com o jogo pausado pra mexer em algo. Sai na hora se um
    abortar total for pedido. Retorna True se realmente ficou pausado
    (pra quem chamar saber que precisa esperar um clique manual antes de
    clicar no jogo de novo — clicar em 'Retomar' tira o foco do jogo)."""
    pausou = False
    while state.evento_pausado.is_set():
        pausou = True
        if state.evento_abortar.is_set():
            return pausou
        time.sleep(0.5)
    return pausou


def _aguardar_clique_manual():
    """Bloqueia até detectar um clique físico do botão esquerdo do mouse
    (polling via ctypes, funciona mesmo com o jogo elevado/admin).
    Usado sempre que o Windows pode ter bloqueado a troca de foco
    programática pro jogo (ex: depois que QUALQUER botão do nosso app é
    clicado, nosso app vira a janela em foco, e o Windows só deixa
    devolver o foco pro jogo via código depois de ver um clique real)."""
    while user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000:
        time.sleep(0.01)
    while not (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000):
        time.sleep(0.01)
    while user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000:
        time.sleep(0.01)


def _calcular_datetime_alvo(hora_str):
    """hora_str no formato 'HH:MM'. Se esse horário já passou hoje,
    agenda pra amanhã no mesmo horário (útil pra rotina diária)."""
    agora = datetime.datetime.now()
    hora, minuto = map(int, hora_str.split(":"))
    alvo = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    if alvo <= agora:
        alvo += datetime.timedelta(days=1)
    return alvo


def _aguardar_horario_agendado(hora_str, callback_aguardando=None):
    """Bloqueia até o relógio bater o horário agendado. Cancelável a
    qualquer momento pelo botão Resetar (state.evento_abortar). Retorna
    True se chegou no horário normalmente, False se foi cancelado antes."""
    alvo = _calcular_datetime_alvo(hora_str)
    persistence.log_execucao(f"🕐 [Agendamento] Aguardando até {alvo.strftime('%d/%m %H:%M')} para começar...")
    while datetime.datetime.now() < alvo:
        if state.evento_abortar.is_set():
            persistence.log_execucao("[Agendamento] Cancelado pelo usuário antes do horário chegar.")
            return False
        if callback_aguardando:
            callback_aguardando(alvo, alvo - datetime.datetime.now())
        time.sleep(1)
    persistence.log_execucao("🕐 [Agendamento] Horário alcançado! Iniciando a sequência...")
    return True


def _resolver_coord_dg(nome_dg, dados_dg):
    """Busca a coordenada de uma DG, com os mesmos fallbacks usados na execução."""
    coord_dg = persistence.mapeamento_personalizado.get(nome_dg)
    if not coord_dg:
        for chave, valor in persistence.mapeamento_personalizado.items():
            if chave.endswith(nome_dg) or nome_dg in chave:
                coord_dg = valor
                break
    if not coord_dg:
        coord_dg = dados_dg.get("coord")
    return coord_dg


def rodar_macro_sequencial(lista_sequencia, repositorio_dinamico, callback_inicio=None, callback_fim=None,
                            callback_deteccao=None, horario_agendado=None, callback_aguardando_horario=None):
    """lista_sequencia: lista de tuplas (nome_dg, tempo_base_min, multiplicador).
    horario_agendado: string 'HH:MM' opcional — se informado, o bot clica
    uma vez pra focar (igual sempre fez) e DEPOIS fica esperando esse
    horário chegar antes de clicar em qualquer DG.
    callback_inicio(nome_dg, idx, total) é chamado antes de disparar a DG.
    callback_fim(nome_dg, idx, total) é chamado quando o ciclo daquela DG
    termina — seja porque o tempo acabou, seja porque o usuário pulou."""
    state.evento_fila_rodando.set()
    try:
        # --- VALIDAÇÃO PRÉVIA: garante que toda DG marcada tem coordenada mapeada ---
        dgs_sem_mapeamento = []
        for nome_dg, _, multiplicador in lista_sequencia:
            if multiplicador <= 0:
                continue
            dados_dg = repositorio_dinamico[nome_dg]
            coord_dg = _resolver_coord_dg(nome_dg, dados_dg)
            if not coord_dg:
                dgs_sem_mapeamento.append(nome_dg)

        if dgs_sem_mapeamento:
            lista_nomes = ", ".join(dgs_sem_mapeamento)
            persistence.log_execucao(
                f"❌ [Validação] Sequência cancelada: DGs sem coordenada mapeada: {lista_nomes}. "
                "Use 'Mapear coordenadas' antes de tentar novamente."
            )
            telegram_notifier.enviar_mensagem_async(
                f"❌ Sequência não iniciada — faltam coordenadas para: {lista_nomes}"
            )
            return

        print("\n>>> IMPORTANTE: Clique uma vez dentro da tela do Cabal agora para focar o mouse...")
        _aguardar_clique_manual()
        time.sleep(0.6)

        if horario_agendado:
            prosseguir = _aguardar_horario_agendado(horario_agendado, callback_aguardando_horario)
            if not prosseguir:
                return

        total = len(lista_sequencia)
        for idx, (nome_dg, tempo_base, multiplicador) in enumerate(lista_sequencia, start=1):
            if state.evento_abortar.is_set():
                persistence.log_execucao("⏹ [Abortar] Execução cancelada pelo usuário (Resetar).")
                break


            dados_dg = repositorio_dinamico[nome_dg]
            categoria_dg = dados_dg["categoria"]

            # 1. Pega a coordenada da Aba (com fallback)
            coord_aba = persistence.mapeamento_personalizado.get(f"ABA_{categoria_dg.upper()}", config.ABAS_CATEGORIAS.get(categoria_dg))

            # 2. Pega a coordenada da DG buscando PRIMEIRO no mapeamento personalizado do JSON!
            coord_dg = persistence.mapeamento_personalizado.get(nome_dg, dados_dg.get("coord"))

            # 3. Garante que pegou X e Y corretamente
            if isinstance(coord_dg, (list, tuple)):
                x_dg, y_dg = coord_dg[0], coord_dg[1]
            else:
                x_dg, y_dg = coord_dg

            # 4. Pega o Botão Iniciar (com fallback)
            coord_iniciar = persistence.mapeamento_personalizado.get("BOTAO_INICIAR", config.BOTAO_INICIAR)

            if multiplicador <= 0:
                print(f"\n[Aviso] {nome_dg} está com multiplicador 0 — pulando (não será executada).")
                continue

            if callback_inicio:
                callback_inicio(nome_dg, idx, total)

            tempo_espera_segundos = int(tempo_base * multiplicador * 60)

            persistence.log_execucao(
                f"=== ETAPA {idx}/{total}: {nome_dg} | Tempo base: {tempo_base} min | "
                f"Multiplicador: x{multiplicador} | Bloco total: {tempo_espera_segundos // 60} min ==="
            )

            if state.evento_reconectando.is_set():
                while state.evento_reconectando.is_set():
                    if state.evento_abortar.is_set():
                        break
                    time.sleep(1)
            if state.evento_abortar.is_set():
                break

            pausou = _aguardar_pausa()
            if state.evento_abortar.is_set():
                break
            if pausou:
                print("[Retomar] Aguardando clique na tela do jogo pra focar antes de continuar...")
                _aguardar_clique_manual()

    # --- RESOLUÇÃO DA DG (Busca Inteligente por Chave no JSON) ---
            # 1. Tenta pelo nome exato
            coord_dg = persistence.mapeamento_personalizado.get(nome_dg)

            # 2. Se não achar, procura a chave do JSON que contém o nome da DG
            # (Resolve a diferença entre 'Cidadela Vulcânica' e 'DG Iniciante L2: Cidadela Vulcânica')
            if not coord_dg:
                for chave, valor in persistence.mapeamento_personalizado.items():
                    if chave.endswith(nome_dg) or nome_dg in chave:
                        coord_dg = valor
                        break

            # 3. Se ainda assim não achar, usa o fallback do repositório
            if not coord_dg:
                coord_dg = dados_dg.get("coord")

            # Extrai X e Y da coordenada encontrada
            if isinstance(coord_dg, (list, tuple)) and len(coord_dg) >= 2:
                x_dg, y_dg = coord_dg[0], coord_dg[1]
            else:
                x_dg, y_dg = coord_dg

            # --- EXECUÇÃO DOS CLIQUES ---
            with state.lock_tela:
                ocr.focar_janela_cabal()
                pyautogui.press("f6")
                time.sleep(0.4)
                pyautogui.click(coord_aba)
                time.sleep(0.4)
                pyautogui.click(x_dg, y_dg)
                time.sleep(0.4)
                pyautogui.click(coord_iniciar)

            persistence.log_execucao(f"✅ Ciclo de {multiplicador} entrada(s) disparado com sucesso para '{nome_dg}'.")

            telegram_notifier.enviar_mensagem_async(
                f"🎮 DG iniciada: {nome_dg} (estimado {tempo_base * multiplicador:.1f} min)"
            )

            _aguardar_ciclo(tempo_espera_segundos, nome_dg, callback_deteccao, multiplicador)
            if state.evento_abortar.is_set():
                break

            if callback_fim:
                callback_fim(nome_dg, idx, total)

        if state.evento_abortar.is_set():
            persistence.log_execucao("⏹ Sequência interrompida (Resetar clicado durante a execução).")
        else:
            persistence.log_execucao("🎉 Sequência completa do Dungeon Helper finalizada com sucesso!")
            telegram_notifier.enviar_mensagem_async(
                f"🎉 Sequência do Dungeon Helper finalizada! {len(lista_sequencia)} DG(s) na fila."
            )
    finally:
        state.evento_fila_rodando.clear()