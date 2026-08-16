"""
Script: Clique alternado entre 2 regiões usando F2
---------------------------------------------------
Captura das regiões:
    - Posicione o mouse onde quer e clique com o BOTÃO DIREITO
      para marcar a posição candidata.
    - Clique com o BOTÃO DO MEIO (scroll) para CONFIRMAR a captura
      daquela posição.
    - Repita para a região 2.

Depois de capturar as 2 regiões:
    - Pressione F2 para INICIAR o loop de cliques
      (clica na região 1, espera, clica na região 2, espera, repete...)
    - Pressione F2 de novo para PARAR o loop.
    - Pressione ESC a qualquer momento para encerrar o programa.

Requisitos:
    pip install pyautogui keyboard mouse --break-system-packages
    (no Windows normalmente sem o --break-system-packages)

OBS: no Windows, rode o terminal como Administrador para o "keyboard"
e o "mouse" conseguirem capturar as teclas/cliques globalmente.
"""

import pyautogui
import keyboard
import mouse
import time
import threading

# Intervalo (em segundos) entre cada clique do loop
INTERVALO = 0.3

rodando = False
parar_tudo = False


def capturar_posicao(nome):
    print(f"\n>> Clique com o BOTÃO DIREITO para marcar a {nome}...")

    candidata = {"pos": None}
    confirmado = threading.Event()

    def handler(event):
        if not isinstance(event, mouse.ButtonEvent):
            return
        if event.event_type != "down":
            return

        if event.button == "right":
            candidata["pos"] = mouse.get_position()
            print(f"   Posição candidata marcada: {candidata['pos']} "
                  f"-> clique no BOTÃO DO MEIO (scroll) para confirmar.")
        elif event.button == "middle":
            if candidata["pos"] is not None:
                confirmado.set()

    mouse.hook(handler)
    confirmado.wait()
    mouse.unhook(handler)

    print(f"{nome} CONFIRMADA em: {candidata['pos']}")
    return candidata["pos"]


def loop_cliques(pos1, pos2):
    global rodando
    alvo = pos1
    while True:
        if parar_tudo:
            return
        if rodando:
            pyautogui.click(alvo)
            print(f"Clique em {alvo}")
            alvo = pos2 if alvo == pos1 else pos1
            time.sleep(INTERVALO)
        else:
            time.sleep(0.05)


def alternar_estado():
    global rodando
    rodando = not rodando
    print("\n[LOOP INICIADO]" if rodando else "\n[LOOP PARADO]")


def encerrar():
    global parar_tudo
    parar_tudo = True
    print("\nEncerrando programa...")
    keyboard.unhook_all()
    mouse.unhook_all()
    exit(0)


def main():
    print("=== Captura de Regiões ===")
    pos1 = capturar_posicao("REGIÃO 1")
    pos2 = capturar_posicao("REGIÃO 2")

    print("\nPronto! Pressione F2 para iniciar/parar o loop de cliques.")
    print("Pressione ESC para sair do programa.\n")

    keyboard.add_hotkey("f2", alternar_estado)
    keyboard.add_hotkey("esc", encerrar)

    thread = threading.Thread(target=loop_cliques, args=(pos1, pos2), daemon=True)
    thread.start()

    keyboard.wait("esc")


if __name__ == "__main__":
    main()