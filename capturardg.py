import time
import json
import os
import persistence
from pynput import mouse, keyboard

# Lista de TODOS os locais que seu código precisa mapear/recalibrar, na ordem!
ROTEIRO = [
    # --- 1. RECONEXÃO / LOGIN ---
    {"nome": "REGIAO_CHECAGEM_DESCONECTADO", "tipo": "REGIAO", "desc": "Arraste no aviso de Desconectado (OCR)"},
    {"nome": "BOTAO_OK_DESCONECTADO", "tipo": "PONTO", "desc": "Clique no botão OK do aviso de Desconectado"},
    {"nome": "REGIAO_CHECAGEM_LOGIN", "tipo": "REGIAO", "desc": "Arraste na caixa da tela de Login (OCR)"},
    {"nome": "CAMPO_SENHA", "tipo": "PONTO", "desc": "Clique no campo de digitar a Senha"},
    {"nome": "BOTAO_LOGIN", "tipo": "PONTO", "desc": "Clique no botão de Login"},
    {"nome": "REGIAO_LOGIN_DUPLO", "tipo": "REGIAO", "desc": "Arraste na caixa do popup 'Login Duplo' (OCR)"},
    {"nome": "BOTAO_SIM_LOGIN_DUPLO", "tipo": "PONTO", "desc": "Clique no botão Sim do popup de Login Duplo"},
    {"nome": "REGIAO_VERIFICACAO_TELA", "tipo": "REGIAO", "desc": "Arraste na região de verificação de tela (OCR)"},
    {"nome": "CANAL_3", "tipo": "PONTO", "desc": "Clique no Canal 3"},
    {"nome": "BOTAO_CONECTAR", "tipo": "PONTO", "desc": "Clique no botão Conectar do Canal"},
    {"nome": "BOTAO_COMECAR", "tipo": "PONTO", "desc": "Clique no botão Começar (Entrar no jogo)"},
    {"nome": "BOTAO_INICIAR", "tipo": "PONTO", "desc": "Clique no botão Iniciar da DG no jogo"},
    {"nome": "REGIAO_CHECAGEM_DG_FINALIZADA", "tipo": "REGIAO", "desc": "Arraste na região de verificação de DG finalizada (OCR)"},
    {"nome": "BOTAO_ABA_INICIANTE", "tipo": "PONTO", "desc": "Clique na aba Iniciante"},
    {"nome": "BOTAO_ABA_INTERMEDIARIO", "tipo": "PONTO", "desc": "Clique na aba Intermediário"},
    {"nome": "BOTAO_ABA_AVANCADO", "tipo": "PONTO", "desc": "Clique na aba Avançado"},

    # --- 2. DGs INICIANTES (Aba 1) ---
    {"nome": "DG Iniciante L1: Estação Ruína", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L2: Cidadela Vulcânica", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L3: Templo Esquecido 1SS", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L4: Ilha Proibida", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L5: Altar de Siena 1SS", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L6: Castelo das Ilusões", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L7: Caverna do Pânico(Premium)", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L8: Locomotiva Louca(Premium)", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L9: Catacumba Gélida(Premium)", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L10: Morada das Chamas Infernais(Premium)", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L11: Morada das Chamas Infernais(Desperto)", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L12: Caverna do Pânico(Desperto)", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L13: Locomotiva Fantasma(Desperto)", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L14: Catacumba Gélida(Desperto)", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L15: Pandemônio", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L16: Moinho Sagrado", "tipo": "PONTO", "desc": "Clique na linha da DG"},
    {"nome": "DG Iniciante L17: Torre Gélida dos Mortos 1SS", "tipo": "PONTO", "desc": "Clique na linha da DG"},
]

indice_atual = 0
start_pos = None
resultados = {}
fila = list(ROTEIRO)
item_atual = None
tentativa_atual = None

def mostrar_proximo():
    global indice_atual
    if item_atual is not None:
        instrucao = "CLIQUE" if item_atual["tipo"] == "PONTO" else "ARRASTE E SOLTE"
        pos = len(ROTEIRO) - len(fila)
        print(f"\n[{pos + 1}/{len(ROTEIRO)}] 👉  Aguardando: {item_atual['nome']}")
        print(f"    Instrução: {instrucao} com BOTAO DIREITO ({item_atual['desc']})")
        print("    (Pressione o BOTÃO DO MEIO para confirmar, F2 para pular, ou ESC para encerrar)")
    else:
        print("\n🎉 TODOS OS ITENS FORAM MAPEADOS!")

def on_click(x, y, button, pressed):
    global start_pos, item_atual, tentativa_atual
    if item_atual is None:
        return

    if button == mouse.Button.right:
        if pressed:
            start_pos = (x, y)
        else:
            if start_pos:
                end_pos = (x, y)
                if item_atual["tipo"] == "REGIAO":
                    x1, x2 = min(start_pos[0], end_pos[0]), max(start_pos[0], end_pos[0])
                    y1, y2 = min(start_pos[1], end_pos[1]), max(start_pos[1], end_pos[1])
                    valor = (x1, y1, x2, y2)
                else:
                    valor = (x, y)
                tentativa_atual = valor
                print(f"  ✅ CAPTURADO {item_atual['nome']} = {valor}")
                print("  ▶ Agora confirme com o BOTAO DO MEIO (scroll) ou pressione F2 para pular este item.")
            start_pos = None
    elif button == mouse.Button.middle and not pressed:
        if tentativa_atual is not None:
            resultados[item_atual["nome"]] = tentativa_atual
            print(f"  ✅ CONFIRMADO {item_atual['nome']}")
            tentativa_atual = None
            avancar_item()

def avancar_item():
    global item_atual
    if fila:
        item_atual = fila.pop(0)
        mostrar_proximo()
    else:
        item_atual = None
        mostrar_proximo()


def on_press(key):
    global fila, item_atual, tentativa_atual
    try:
        if key == keyboard.Key.f2 and item_atual is not None:
            print(f"  ⚠️  PULADO: {item_atual['nome']}")
            tentativa_atual = None
            fila.append(item_atual)
            avancar_item()
        elif key == keyboard.Key.esc:
            print("\n[!] Finalizando captura...")
            return False
    except Exception as e:
        print(f"Erro: {e}")


import json
import os

# ==============================================================================
# TABELA DE EQUIVALÊNCIA DAS DGs (Qual DG fica em qual Linha da tela)
# ==============================================================================
MAPEAMENTO_EQUIVALENCIAS = {
    # --- LINHA 1 ---
    # "Nome da DG Intermediaria/Avançada": "DG Iniciante L1: Estação Ruína",

    # --- LINHA 2 ---
    # "Nome da DG Intermediaria/Avançada": "DG Iniciante L2: Cidadela Vulcânica",

    # --- LINHA 3 ---
    "Templo Esquecido 2SS": "DG Iniciante L3: Templo Esquecido 1SS",

    # --- LINHA 4 ---
    # "Ilha Proibida Desperta": "DG Iniciante L4: Ilha Proibida",

    # --- LINHA 5 ---
    "Altar de Siena 2SS": "DG Iniciante L5: Altar de Siena 1SS",

    # --- LINHA 6 ---
    "Posto Avançado de Máquinas": "DG Iniciante L6: Castelo das Ilusões",

    # --- LINHA 17 ---
    "Torre dos Mortos 2SS": "DG Iniciante L17: Torre Gélida dos Mortos 1SS",
    "Torre dos Mortos 3SS": "DG Iniciante L17: Torre Gélida dos Mortos 1SS",

    # Adicione aqui qualquer outra DG associando ao nome exato que está no seu ROTEIRO!
}

def salvar_resultados_em_arquivo(dados):
    try:
        # 1. Carrega as configurações atuais para garantir que temos o estado mais recente
        persistence.carregar_historico_json()
        
        # 2. Converte as tuplas do mapeamento para listas (formato aceito pelo JSON)
        novas_coordenadas = {k: list(v) for k, v in dados.items()}
        
        # 3. REPLICAÇÃO AUTOMÁTICA: Copia as coordenadas da linha Iniciante para as DGs equivalentes
        qtd_replicadas = 0
        for dg_destino, chave_origem in MAPEAMENTO_EQUIVALENCIAS.items():
            if chave_origem in novas_coordenadas:
                novas_coordenadas[dg_destino] = novas_coordenadas[chave_origem]
                qtd_replicadas += 1

        if qtd_replicadas > 0:
            print(f"  🔄 {qtd_replicadas} DGs Intermediárias/Avançadas foram replicadas automaticamente!")
        
        # 4. Atualiza o dicionário de mapeamento mantendo o que já tinha antes
        persistence.mapeamento_personalizado.update(novas_coordenadas)
        
        # 5. Usa a própria função do persistence para salvar tudo no JSON com segurança
        persistence.salvar_historico_json(
            saved_times={k: v["tempo_base"] for k, v in persistence.repositorio_dinamico.items()},
            ordem=persistence.fila_salva_ordem,
            senha=persistence.senha_salva,
            active=persistence.reconexao_ativa,
            multiplicadores=persistence.multiplicadores_salvos,
            historico=persistence.historico_execucoes,
            mapeamento_personalizado=persistence.mapeamento_personalizado
        )
        print("\n✅ Mapeamento completo salvo com sucesso no 'dungeon_helper_config.json' via Persistence!")
    except Exception as e:
        print(f"❌ Erro ao salvar via persistence: {e}")

def main():
    print("="*60)
    print("        MAPEADOR SEQUENCIAL - CABAL BOT        ")
    print("="*60)
    print("Como usar:")
    print("1. O script vai te dizer no console O QUE mapear agora.")
    print("2. Ponto: Dê um clique com o BOTÃO DIREITO.")
    print("3. Região: Clique, segure e arraste com o BOTÃO DIREITO.")
    print("4. Pressione o BOTÃO DO MEIO (scroll) para confirmar o valor capturado.")
    print("5. Tecla F2: Pula o item atual e tenta novamente depois.")
    print("6. Tecla ESC: Encerra e gera o relatório final.")
    print("="*60)

    avancar_item()

    mouse_listener = mouse.Listener(on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press)

    mouse_listener.start()
    keyboard_listener.start()

    keyboard_listener.join()
    mouse_listener.stop()

    print("\n" + "="*60)
    print("               RESUMO FINAL DOS DADOS                  ")
    print("="*60)
    for nome, valor in resultados.items():
        print(f'{nome} = {valor}')
    print("="*60)

    salvar_resultados_em_arquivo(resultados)

if __name__ == "__main__":
    main()