"""
Tudo relacionado a ler/escrever o dungeon_helper_config.json: repositório
de DGs (com tempos ajustados), fila salva, senha, opção de auto-reconnect
e histórico de execuções (quantas vezes + quando cada DG foi rodada).

Outros módulos devem importar este módulo inteiro (`import persistence`)
e acessar as variáveis como `persistence.senha_salva`, nunca com
`from persistence import senha_salva` — isso é o que garante que todo
mundo sempre enxergue o valor mais atual.
"""
import json
import os
import copy
import datetime

import config

senha_salva = ""
nome_personagem = ""
reconexao_ativa = False
deteccao_automatica_ativa = False
telegram_ativo = False
telegram_chat_id = ""
telegram_nome = ""
telegram_username = ""
telegram_ultimo_update_id = 0
resolucao_calibrada = config.RESOLUCAO_PADRAO
mapeamento_personalizado = {}
repositorio_dinamico = {}
fila_salva_ordem = []
multiplicadores_salvos = {}
historico_execucoes = {}


def carregar_historico_json():
    """Carrega tudo do disco. Sempre parte de uma cópia PROFUNDA do
    template padrão (config.REPOSITORIO_PADRAO), pra nunca sobrescrever
    o template original ao ajustar tempos em tempo de execução."""
    global nome_personagem, senha_salva, reconexao_ativa, repositorio_dinamico, fila_salva_ordem
    global multiplicadores_salvos, historico_execucoes, deteccao_automatica_ativa
    global telegram_ativo, telegram_chat_id, telegram_nome, telegram_username, telegram_ultimo_update_id
    global resolucao_calibrada, mapeamento_personalizado

    resolucao_calibrada = config.RESOLUCAO_PADRAO
    config.aplicar_perfil_resolucao(resolucao_calibrada)
    repositorio_dinamico = copy.deepcopy(config.REPOSITORIO_PADRAO)
    senha_salva = ""
    nome_personagem = ""
    reconexao_ativa = False
    deteccao_automatica_ativa = False
    telegram_ativo = False
    telegram_chat_id = ""
    telegram_nome = ""
    telegram_username = ""
    telegram_ultimo_update_id = 0
    mapeamento_personalizado = {}
    fila_salva_ordem = []
    multiplicadores_salvos = {k: 20 for k in config.REPOSITORIO_PADRAO}
    historico_execucoes = {}

    if not os.path.exists(config.CONFIG_FILE):
        return
    try:
        with open(config.CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        senha_salva = data.get("senha_cabal", "")
        nome_personagem = data.get("nome_personagem", "")
        reconexao_ativa = data.get("reconexao_ativa", False)
        deteccao_automatica_ativa = data.get("deteccao_automatica_ativa", False)
        telegram_ativo = data.get("telegram_ativo", False)
        telegram_chat_id = data.get("telegram_chat_id", "")
        telegram_nome = data.get("telegram_nome", "")
        telegram_username = data.get("telegram_username", "")
        telegram_ultimo_update_id = data.get("telegram_ultimo_update_id", 0)
        resolucao_calibrada = data.get("resolucao_calibrada", config.RESOLUCAO_PADRAO)
        if resolucao_calibrada not in config.PERFIS_RESOLUCAO:
            resolucao_calibrada = config.RESOLUCAO_PADRAO
        config.aplicar_perfil_resolucao(resolucao_calibrada)
        mapeamento_personalizado = data.get("mapeamento_personalizado", {}) or {}
        if isinstance(mapeamento_personalizado, dict):
            persistence_mapeamento = mapeamento_personalizado
            config.aplicar_mapeamento_personalizado(persistence_mapeamento)
        else:
            persistence_mapeamento = {}
        repositorio_dinamico = copy.deepcopy(config.REPOSITORIO_PADRAO)
        fila_salva_ordem = [n for n in data.get("fila_salva_ordem", []) if n in repositorio_dinamico]

        for k, v in data.get("tempos_dgs", {}).items():
            if k in repositorio_dinamico:
                try:
                    repositorio_dinamico[k]["tempo_base"] = float(v)
                except (TypeError, ValueError):
                    pass

        for k, v in data.get("multiplicadores_dgs", {}).items():
            if k in repositorio_dinamico:
                try:
                    multiplicadores_salvos[k] = max(0, min(20, int(v)))
                except (TypeError, ValueError):
                    pass

        historico_execucoes = data.get("historico_execucoes", {})
    except Exception as e:
        print(f"[Aviso] Falha ao carregar {config.CONFIG_FILE} ({e}). Usando padrões.")


def salvar_historico_json(saved_times, ordem, senha, active, multiplicadores=None, historico=None, deteccao_auto=None,
                           tg_ativo=None, tg_chat=None, tg_nome=None, tg_username=None, tg_update_id=None,
                           resolucao_calibrada=None, mapeamento_personalizado=None):
    """Salva TODO o estado persistente do app no JSON."""

    nome_personagem = globals().get("nome_personagem", "")
    
    if mapeamento_personalizado is None:
        mapeamento_personalizado = globals().get("mapeamento_personalizado", {})
    data = {
        "nome_personagem": nome_personagem,
        "senha_cabal": senha,
        "reconexao_ativa": active,
        "deteccao_automatica_ativa": deteccao_automatica_ativa if deteccao_auto is None else deteccao_auto,
        "telegram_ativo": telegram_ativo if tg_ativo is None else tg_ativo,
        "telegram_chat_id": telegram_chat_id if tg_chat is None else tg_chat,
        "telegram_nome": telegram_nome if tg_nome is None else tg_nome,
        "telegram_username": telegram_username if tg_username is None else tg_username,
        "telegram_ultimo_update_id": telegram_ultimo_update_id if tg_update_id is None else tg_update_id,
        "resolucao_calibrada": config.RESOLUCAO_CALIBRADA if resolucao_calibrada is None else resolucao_calibrada,
        "mapeamento_personalizado": mapeamento_personalizado,
        "fila_salva_ordem": ordem,
        "tempos_dgs": saved_times,
        "multiplicadores_dgs": multiplicadores or {},
        "historico_execucoes": historico or {},
    }
    try:
        with open(config.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[Aviso] Falha ao salvar {config.CONFIG_FILE}: {e}")


def registrar_execucao_no_historico(nome_dg):
    """Incrementa o contador de execuções de uma DG e grava a data/hora
    atual. Só mexe na chave 'historico_execucoes' do arquivo, preservando
    o resto do que já estava salvo. Seguro pra chamar de dentro de uma
    thread de background (não toca em nada do tkinter)."""
    global historico_execucoes
    info = historico_execucoes.setdefault(nome_dg, {"count": 0, "ultima": None})
    info["count"] += 1
    info["ultima"] = datetime.datetime.now().isoformat()
    try:
        data = {}
        if os.path.exists(config.CONFIG_FILE):
            with open(config.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        data["historico_execucoes"] = historico_execucoes
        with open(config.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[Aviso] Falha ao salvar histórico de execução: {e}")


def formatar_historico(nome_dg):
    """Texto curto tipo '✔ 3x há 2h' pra mostrar do lado de cada DG."""
    info = historico_execucoes.get(nome_dg)
    if not info or not info.get("count"):
        return "—"
    count = info["count"]
    ultima = info.get("ultima")
    quando = ""
    if ultima:
        try:
            dt = datetime.datetime.fromisoformat(ultima)
            delta = datetime.datetime.now() - dt
            if delta.days > 0:
                quando = f"há {delta.days}d"
            elif delta.seconds >= 3600:
                quando = f"há {delta.seconds // 3600}h"
            elif delta.seconds >= 60:
                quando = f"há {delta.seconds // 60}min"
            else:
                quando = "agora"
        except Exception:
            quando = ""
    return f"✔ {count}x {quando}".strip()


def registrar_deteccao_arquivo(nome_dg, tempo_estimado_min, tempo_real_min, diferenca_min, percentual, multiplicador=None):
    """Acrescenta uma linha no deteccoes_dg.txt toda vez que a detecção
    automática confirma o fim de uma DG de verdade (não confunde com o
    modo debug — isso só grava quando REALMENTE bateu, então não enche
    o arquivo com ruído).

    Grava o `multiplicador` usado nessa execução — ESSENCIAL pra depois
    normalizar corretamente (tempo_real_min é o tempo do BLOCO inteiro,
    não de uma execução só; sem saber o multiplicador usado, não dá pra
    voltar com segurança pro 'tempo por execução' que o campo de tempo
    da DG realmente representa)."""
    multiplicador_txt = f" | multiplicador={multiplicador}" if multiplicador is not None else ""
    linha = (
        f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"{nome_dg} | estimado={tempo_estimado_min:.1f}min | "
        f"real={tempo_real_min:.1f}min | folga={diferenca_min:.1f}min ({percentual:.0f}%)"
        f"{multiplicador_txt}\n"
    )
    try:
        with open(config.LOG_DETECCOES_FILE, "a", encoding="utf-8") as f:
            f.write(linha)
    except Exception as e:
        print(f"[Aviso] Falha ao gravar {config.LOG_DETECCOES_FILE}: {e}")


def log_execucao(mensagem):
    """Imprime no console (quando existir um) E grava com timestamp em
    LOG_EXECUCAO_FILE. Existe porque no .exe empacotado com --windowed
    não tem console visível nenhum — sem isso, não haveria como
    investigar depois o que aconteceu durante uma sessão longa/noturna
    (reconexões, detecções, falhas, etc.). Use pra qualquer evento
    importante do ciclo de vida da execução."""
    linha = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {mensagem}"
    print(linha)
    try:
        with open(config.LOG_EXECUCAO_FILE, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception as e:
        print(f"[Aviso] Falha ao gravar {config.LOG_EXECUCAO_FILE}: {e}")


def ler_deteccoes_log(dias=None):
    """Lê deteccoes_dg.txt e retorna uma lista de dicts com cada
    detecção registrada. Se `dias` for informado (int), filtra só as
    linhas dos últimos N dias; None = todo o histórico. O campo
    'multiplicador' vem como None em linhas antigas (gravadas antes
    dessa informação existir no log) — quem for calcular médias precisa
    tratar isso (ver calcular_medias_por_dg)."""
    registros = []
    if not os.path.exists(config.LOG_DETECCOES_FILE):
        return registros
    limite = datetime.datetime.now() - datetime.timedelta(days=dias) if dias is not None else None
    try:
        with open(config.LOG_DETECCOES_FILE, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    partes = linha.split(" | ")
                    data = datetime.datetime.strptime(partes[0], "%Y-%m-%d %H:%M:%S")
                    nome_dg = partes[1]
                    estimado = float(partes[2].split("=")[1].replace("min", ""))
                    real = float(partes[3].split("=")[1].replace("min", ""))
                    folga_bruta = partes[4].split("=")[1]  # "Zmin (P%)"
                    folga = float(folga_bruta.split("min")[0])
                    percentual = float(folga_bruta.split("(")[1].replace("%)", ""))
                    multiplicador = None
                    if len(partes) >= 6 and "multiplicador=" in partes[5]:
                        multiplicador = int(partes[5].split("=")[1].strip())
                except (IndexError, ValueError):
                    continue
                if limite and data < limite:
                    continue
                registros.append({
                    "data": data, "nome_dg": nome_dg, "estimado": estimado,
                    "real": real, "folga": folga, "percentual": percentual,
                    "multiplicador": multiplicador,
                })
    except Exception as e:
        print(f"[Aviso] Falha ao ler {config.LOG_DETECCOES_FILE}: {e}")
    return registros


def calcular_medias_por_dg(dias=None):
    """Agrupa as detecções por DG e calcula o tempo médio/mín/máx POR
    EXECUÇÃO (normalizado — ver abaixo), contagem e data da última
    detecção. Retorna {nome_dg: {"count", "media_tempo_base",
    "min_tempo_base", "max_tempo_base", "ultima_data"}}.

    IMPORTANTE — normalização: o 'real' gravado no log é o tempo do
    BLOCO INTEIRO (tempo_base × multiplicador daquela execução), não de
    uma execução só. O campo de tempo que o usuário edita na tela
    representa tempo POR EXECUÇÃO (tempo_base) — ele é multiplicado
    pelo multiplicador toda vez que um novo bloco é calculado. Sem essa
    divisão, aplicar a média direto no campo de tempo infla o próximo
    bloco em várias vezes (bug corrigido: um multiplicador x20 fazia o
    próximo tempo estimado ficar ~20x maior que deveria).

    Registros SEM multiplicador gravado (linhas antigas, de antes dessa
    informação existir no log) são ignorados aqui — não dá pra
    normalizar com segurança sem saber por quanto dividir."""
    registros = ler_deteccoes_log(dias)
    agrupado = {}
    ignorados_sem_multiplicador = 0
    for r in registros:
        if not r.get("multiplicador"):
            ignorados_sem_multiplicador += 1
            continue
        tempo_base_normalizado = r["real"] / r["multiplicador"]
        info = agrupado.setdefault(r["nome_dg"], {"tempos": [], "ultima_data": None})
        info["tempos"].append(tempo_base_normalizado)
        if info["ultima_data"] is None or r["data"] > info["ultima_data"]:
            info["ultima_data"] = r["data"]
    if ignorados_sem_multiplicador:
        print(f"[Aviso] {ignorados_sem_multiplicador} detecção(ões) antiga(s) sem multiplicador "
              f"registrado foram ignoradas no cálculo de médias (não dá pra normalizar com segurança).")
    resultado = {}
    for nome_dg, info in agrupado.items():
        tempos = info["tempos"]
        resultado[nome_dg] = {
            "count": len(tempos),
            "media_tempo_base": sum(tempos) / len(tempos),
            "min_tempo_base": min(tempos),
            "max_tempo_base": max(tempos),
            "ultima_data": info["ultima_data"],
        }
    return resultado