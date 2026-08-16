import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import subprocess

import connection
import updater
from admin_utils import ensure_admin_launch
from ui import CabalDungeonHelperUI

def checar_atualizacoes(root):
    def _verificar():
        tem_update, versao = updater.verificar_updates()
        if tem_update:
            # Mostra o popup na thread principal
            root.after(0, lambda: _perguntar_update(root, versao))
            
    threading.Thread(target=_verificar, daemon=True).start()

def _perguntar_update(root, versao):
    if messagebox.askyesno("Atualização disponível", f"Nova versão {versao} disponível. Atualizar agora?"):
        # Abre o updater em processo separado
        subprocess.Popen(["python", "updater_exec.py"])
        root.destroy()
        sys.exit()

if __name__ == "__main__":
    executable = os.path.abspath(sys.argv[0]) if len(sys.argv) > 0 else os.path.abspath("dungeon_helper.exe")
    ensure_admin_launch(executable)

    app = tk.Tk()
    
    # Esconde a janela principal enquanto checa (opcional) ou deixa ela aparecer
    checar_atualizacoes(app)

    interface = CabalDungeonHelperUI(app)
    threading.Thread(target=connection.thread_monitoramento_conexao, daemon=True).start()

    app.mainloop()