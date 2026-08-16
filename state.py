"""
Objetos de threading compartilhados entre a interface, o motor do macro
e a thread de reconexão. Ficam num módulo à parte porque Lock e Event são
objetos (não são reatribuídos), então dá pra importar esse módulo em
qualquer lugar (`import state`) e usar `state.lock_tela`, sem risco do
valor "congelar" como aconteceria com `from state import lock_tela`.
"""
import threading

# Garante que só uma thread por vez esteja clicando na tela do jogo
# (evita a thread de reconexão e o motor do macro colidindo).
lock_tela = threading.Lock()

# Sinaliza que uma reconexão está em andamento; o motor do macro pausa
# a contagem de tempo enquanto esse evento estiver setado.
evento_reconectando = threading.Event()

# Setado pelo botão "Pular DG atual" da interface. O motor do macro
# checa esse evento a cada segundo durante a espera e interrompe o
# ciclo atual assim que ele for setado (depois se limpa sozinho).
evento_pular_dg = threading.Event()

# Setado/limpo pelo botão "Pausar / Retomar" da interface. Enquanto
# estiver setado, o motor do macro NÃO consome tempo de espera e NÃO
# dispara cliques novos — fica só esperando até ser retomado.
evento_pausado = threading.Event()

# Setado pelo botão "Resetar" quando clicado DURANTE uma execução — pede
# pra abortar a sequência inteira o quanto antes. O motor do macro para
# de processar a fila assim que perceber. A interface limpa a seleção
# de DGs somente depois que o motor confirma que realmente parou.
evento_abortar = threading.Event()

# Setado enquanto a fila de DGs está em execução (do clique em "Iniciar"
# até finalizar/abortar). A thread de reconexão só valida desconexão se
# isso estiver setado — evita ficar checando com o app parado.
evento_fila_rodando = threading.Event()