"""
Interface gráfica. Só lida com widgets e delega toda a lógica de negócio
pros outros módulos (persistence, macro_engine, state).
"""
import time
import re
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import config
import state
import persistence
import macro_engine
import telegram_notifier
import mapeador


class CabalDungeonHelperUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Dungeon Helper - Painel de Controle")
        self.root.geometry("1320x610")
        self.root.resizable(False, False)
        self.root.configure(bg=config.COLOR_BG)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TCombobox", padding=1)

        persistence.carregar_historico_json()

        self.ordem_selecao = list(persistence.fila_salva_ordem)
        self.widgets_dg = {}
        self.macro_rodando = False
        self._abortar_solicitado = False
        self.log_deteccoes_buffer = []
        self.janela_terminal = None
        self.janela_historico = None
        self.janela_mapeamento = None
        self._periodo_historico_dias = 7

        # ---------------- Barra de topo ----------------
        top_bar = tk.Frame(root, bg=config.COLOR_HEADER_BG)
        top_bar.pack(fill="x", side="top")
        tk.Label(top_bar, text="🗡️ Dungeon Helper — Painel de Controle",
                 font=("Segoe UI", 13, "bold"), bg=config.COLOR_HEADER_BG, fg="white").pack(side="left", padx=15, pady=12)


        tk.Button(top_bar, text="🖥️ Terminal", font=config.FONT_BASE, relief="flat",
                  bg="#34495e", fg="white", activebackground="#2c3e50", activeforeground="white",
                  command=self.abrir_ou_focar_terminal).pack(side="left", padx=(0, 8), pady=12)

        tk.Button(top_bar, text="📊 Histórico", font=config.FONT_BASE, relief="flat",
                  bg="#34495e", fg="white", activebackground="#2c3e50", activeforeground="white",
                  command=self.abrir_ou_focar_historico).pack(side="left", padx=(0, 15), pady=12)

        busca_frame = tk.Frame(top_bar, bg=config.COLOR_HEADER_BG)
        busca_frame.pack(side="right", padx=15)
        tk.Label(busca_frame, text="🔍", bg=config.COLOR_HEADER_BG, fg="white").pack(side="left")
        self.ent_busca = tk.Entry(busca_frame, width=24)
        self.ent_busca.pack(side="left", padx=5)
        self.ent_busca.bind("<KeyRelease>", self.filtrar_dgs)

        # ---------------- Quadro dedicado da Fila de Execução ----------------
        fila_panel = tk.LabelFrame(root, text=" Fila de Execução ", bg=config.COLOR_BG,
                                    font=config.FONT_BOLD, fg="#2c3e50")
        fila_panel.pack(fill="x", side="top", padx=10, pady=(8, 0))
        self.lbl_fila = tk.Label(fila_panel, text="Nenhuma DG selecionada ainda.", font=config.FONT_BASE,
                                  fg="gray", bg=config.COLOR_BG, anchor="w", justify="left", wraplength=1280)
        self.lbl_fila.pack(fill="x", padx=10, pady=6)

        # ---------------- Colunas de categorias ----------------
        main_container = tk.Frame(root, bg=config.COLOR_BG)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        categorias = [("Iniciante", "iniciante"), ("Intermediário", "intermediario"), ("Avançado", "avancado")]

        for label_pt, id_cat in categorias:
            col_frame = tk.LabelFrame(main_container, text=f" {label_pt} ", padx=5, pady=5,
                                       bg=config.COLOR_BG, font=config.FONT_BOLD, fg="#2c3e50")
            col_frame.pack(side="left", fill="both", expand=True, padx=5)

            header_row = tk.Frame(col_frame, bg=config.COLOR_BG)
            header_row.pack(fill="x", padx=2, pady=(0, 5))
            tk.Button(header_row, text="Marcar tudo", font=config.FONT_TINY, relief="flat", bg="#dfe6e9",
                      command=lambda c=id_cat: self.selecionar_todas_categoria(c, True)).pack(side="left")
            tk.Button(header_row, text="Limpar", font=config.FONT_TINY, relief="flat", bg="#dfe6e9",
                      command=lambda c=id_cat: self.selecionar_todas_categoria(c, False)).pack(side="left", padx=(4, 0))
            tk.Label(header_row, text="min   x   histórico", font=config.FONT_TINY_BOLD,
                     fg=config.COLOR_MUTED, bg=config.COLOR_BG).pack(side="right")

            canvas = tk.Canvas(col_frame, highlightthickness=0, bg=config.COLOR_BG)
            scrollbar = ttk.Scrollbar(col_frame, orient="vertical", command=canvas.yview)
            scroll_content = tk.Frame(canvas, bg=config.COLOR_BG)

            scroll_content.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
            canvas.create_window((0, 0), window=scroll_content, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            self._habilitar_scroll_mouse(canvas)

            dgs_filtradas = {k: v for k, v in persistence.repositorio_dinamico.items() if v["categoria"] == id_cat}

            row_idx = 0
            for nome_dg, dados in dgs_filtradas.items():
                pre_selecionada = nome_dg in self.ordem_selecao
                bg_inicial = config.COLOR_SELECTED if pre_selecionada else config.COLOR_BG

                dg_row = tk.Frame(scroll_content, bg=bg_inicial, pady=2)
                dg_row.grid(row=row_idx, column=0, sticky="ew", padx=2, pady=1)
                scroll_content.grid_columnconfigure(0, weight=1)
                row_idx += 1

                var_check = tk.BooleanVar(value=pre_selecionada)
                chk = tk.Checkbutton(dg_row, variable=var_check, bg=bg_inicial,
                                      command=lambda n=nome_dg: self.registrar_clique_checkbox(n))
                chk.pack(side="left")

                lbl_name = tk.Label(dg_row, text=nome_dg, font=config.FONT_BASE, width=21, anchor="w", bg=bg_inicial)
                lbl_name.pack(side="left", padx=2)

                hist_lbl = tk.Label(dg_row, text=persistence.formatar_historico(nome_dg), font=config.FONT_TINY,
                                     fg=config.COLOR_MUTED, bg=bg_inicial, width=11, anchor="e")
                hist_lbl.pack(side="right", padx=(4, 2))

                combo_mult = ttk.Combobox(dg_row, values=[str(i) for i in range(21)], width=3, state="readonly")
                combo_mult.set(str(persistence.multiplicadores_salvos.get(nome_dg, 20)))
                combo_mult.pack(side="right", padx=2)
                combo_mult.bind("<<ComboboxSelected>>", lambda e: self.atualizar_estimativa_total())

                tk.Label(dg_row, text="x", font=config.FONT_TINY, bg=bg_inicial).pack(side="right")

                ent_time = tk.Entry(dg_row, width=5, justify="center")
                ent_time.insert(0, str(dados["tempo_base"]))
                ent_time.pack(side="right", padx=4)
                ent_time.bind("<KeyRelease>", lambda e: self.atualizar_estimativa_total())

                self.widgets_dg[nome_dg] = {
                    "check_var": var_check, "check_widget": chk,
                    "entry_widget": ent_time, "combo_widget": combo_mult,
                    "hist_label": hist_lbl, "row_frame": dg_row, "lbl_widget": lbl_name,
                    "categoria": id_cat,
                }

        # ---------------- Painel inferior ----------------
        bottom_panel = tk.Frame(root, bd=0, bg=config.COLOR_BOTTOM_BG)
        bottom_panel.pack(fill="x", side="bottom")

        info_frame = tk.Frame(bottom_panel, bg=config.COLOR_BOTTOM_BG)
        info_frame.pack(side="left", padx=15, pady=8, fill="x", expand=True)

        self.lbl_status = tk.Label(info_frame, text="Aguardando seleção de DGs...",
                                    font=("Segoe UI", 9, "italic"), fg="gray", bg=config.COLOR_BOTTOM_BG, anchor="w")
        self.lbl_status.pack(anchor="w")

        sub_info = tk.Frame(info_frame, bg=config.COLOR_BOTTOM_BG)
        sub_info.pack(anchor="w", pady=(2, 0))
        self.lbl_estimativa = tk.Label(sub_info, text="⏳ Estimativa total: 0min", font=config.FONT_TINY,
                                        fg="#555", bg=config.COLOR_BOTTOM_BG)
        self.lbl_estimativa.pack(side="left")
        tk.Label(sub_info, text="   |   ", font=config.FONT_TINY, fg="#999", bg=config.COLOR_BOTTOM_BG).pack(side="left")
        self.lbl_timer = tk.Label(sub_info, text="⏱️ Tempo em execução: 00:00:00",
                                   font=("Segoe UI", 8, "bold"), fg="#333", bg=config.COLOR_BOTTOM_BG)
        self.lbl_timer.pack(side="left")

        btn_frame = tk.Frame(bottom_panel, bg=config.COLOR_BOTTOM_BG)
        btn_frame.pack(side="right", padx=10, pady=8)

        self.btn_iniciar = tk.Button(btn_frame, text="▶ Iniciar Sequência", font=config.FONT_BOLD,
                                      bg=config.COLOR_ACCENT, fg="white", relief="flat", padx=8,
                                      activebackground="#1f618d", activeforeground="white",
                                      command=self.coletar_e_disparar)
        self.btn_iniciar.pack(side="right", padx=4)

        self.btn_pular = tk.Button(btn_frame, text="⏭ Pular DG atual", font=config.FONT_BASE, relief="flat",
                                    bg=config.COLOR_SKIP, fg="white", activebackground="#d68910",
                                    activeforeground="white", state="disabled",
                                    command=self.pular_dg_atual)
        self.btn_pular.pack(side="right", padx=4)

        self.btn_pausar = tk.Button(btn_frame, text="⏸ Pausar", font=config.FONT_BASE, relief="flat",
                                     bg="#8e44ad", fg="white", activebackground="#6c3483",
                                     activeforeground="white", state="disabled",
                                     command=self.alternar_pausa)
        self.btn_pausar.pack(side="right", padx=4)

        self.btn_config = tk.Button(btn_frame, text="⚙ Configurações", font=config.FONT_BASE, relief="flat",
                                     bg="#dfe6e9", command=self.abrir_tela_config)
        self.btn_config.pack(side="right", padx=4)

        self.btn_mapeador = tk.Button(btn_frame, text="🧭 Mapear coordenadas", font=config.FONT_BASE, relief="flat",
                                      bg="#dfe6e9", command=self.abrir_tela_mapeamento)
        self.btn_mapeador.pack(side="right", padx=4)

        self.btn_salvar = tk.Button(btn_frame, text="💾 Salvar", font=config.FONT_BASE, relief="flat",
                                     bg="#dfe6e9", command=self.salvar_alteracoes)
        self.btn_salvar.pack(side="right", padx=4)

        self.btn_atualizar_base = tk.Button(btn_frame, text="🔄 Atualizar Base", font=config.FONT_BASE, relief="flat",
                                             bg="#dfe6e9", command=self.atualizar_base_historico)
        self.btn_atualizar_base.pack(side="right", padx=4)

        self.btn_resetar = tk.Button(btn_frame, text="🗑 Resetar", font=config.FONT_BASE, relief="flat",
                                      bg="#dfe6e9", command=self.resetar_selecoes)
        self.btn_resetar.pack(side="right", padx=4)

        # Estado para agendamento de horário (agora configurado na janela de Configurações)
        self.var_agendar = tk.BooleanVar(value=False)
        self.horario_agendado_val = "00:00"

        self.atualizar_badges_ordem()
        self.atualizar_estimativa_total()
        self._atualizar_status_fila()

    # -------------------- Scroll com mouse --------------------
    def _habilitar_scroll_mouse(self, canvas):
        def _entrar(_e):
            canvas.bind_all("<MouseWheel>", lambda ev: canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units"))
        def _sair(_e):
            canvas.unbind_all("<MouseWheel>")
        canvas.bind("<Enter>", _entrar)
        canvas.bind("<Leave>", _sair)

    # -------------------- Busca / filtro --------------------
    def filtrar_dgs(self, _event=None):
        texto = self.ent_busca.get().lower().strip()
        for comp in self.widgets_dg.values():
            nome_dg_lower = comp["lbl_widget"].cget("text").lstrip("#0123456789 ").lower()
            if texto == "" or texto in nome_dg_lower:
                comp["row_frame"].grid()
            else:
                comp["row_frame"].grid_remove()

    # -------------------- Seleção / checkboxes --------------------
    def registrar_clique_checkbox(self, nome_dg):
        marcado = self.widgets_dg[nome_dg]["check_var"].get()
        self._aplicar_estado_checkbox(nome_dg, marcado)
        self.atualizar_badges_ordem()
        self.atualizar_estimativa_total()
        self._atualizar_status_fila()

    def _aplicar_estado_checkbox(self, nome_dg, marcado):
        comp = self.widgets_dg[nome_dg]
        if marcado:
            if nome_dg not in self.ordem_selecao:
                self.ordem_selecao.append(nome_dg)
        else:
            if nome_dg in self.ordem_selecao:
                self.ordem_selecao.remove(nome_dg)
        bg = config.COLOR_SELECTED if marcado else config.COLOR_BG
        comp["row_frame"].configure(bg=bg)
        comp["lbl_widget"].configure(bg=bg)
        comp["hist_label"].configure(bg=bg)
        comp["check_widget"].configure(bg=bg)

    def selecionar_todas_categoria(self, id_cat, marcar):
        if self.macro_rodando:
            return
        for nome_dg, comp in self.widgets_dg.items():
            if comp["categoria"] != id_cat:
                continue
            comp["check_var"].set(marcar)
            self._aplicar_estado_checkbox(nome_dg, marcar)
        self.atualizar_badges_ordem()
        self.atualizar_estimativa_total()
        self._atualizar_status_fila()

    def atualizar_badges_ordem(self):
        for nome_dg, comp in self.widgets_dg.items():
            if nome_dg in self.ordem_selecao:
                posicao = self.ordem_selecao.index(nome_dg) + 1
                comp["lbl_widget"].config(text=f"#{posicao}  {nome_dg}")
            else:
                comp["lbl_widget"].config(text=nome_dg)

    def _atualizar_status_fila(self):
        if self.ordem_selecao:
            self.lbl_fila.config(text=" ➔ ".join(self.ordem_selecao), fg="black")
        else:
            self.lbl_fila.config(text="Nenhuma DG selecionada ainda.", fg="gray")

    # -------------------- Estimativa de tempo total --------------------
    def atualizar_estimativa_total(self, _event=None):
        total_min = 0.0
        for nome_dg in self.ordem_selecao:
            comp = self.widgets_dg[nome_dg]
            try:
                t = float(comp["entry_widget"].get().replace(",", "."))
            except ValueError:
                t = 0.0
            try:
                mult = int(comp["combo_widget"].get())
            except ValueError:
                mult = 0
            total_min += t * mult
        horas = int(total_min // 60)
        minutos = int(round(total_min % 60))
        texto = f"⏳ Estimativa total: {horas}h {minutos}min" if horas > 0 else f"⏳ Estimativa total: {minutos}min"
        self.lbl_estimativa.config(text=texto)

    # -------------------- Coleta / validação de valores --------------------
    def coletar_valores_atuais(self):
        tempos = {}
        multiplicadores = {}
        invalidos = []
        for nome_dg, comp in self.widgets_dg.items():
            raw = comp["entry_widget"].get().replace(",", ".")
            try:
                valor = float(raw)
                if valor < 0:
                    raise ValueError
                tempos[nome_dg] = valor
            except ValueError:
                invalidos.append(nome_dg)
                tempos[nome_dg] = persistence.repositorio_dinamico[nome_dg]["tempo_base"]
            try:
                multiplicadores[nome_dg] = int(comp["combo_widget"].get())
            except ValueError:
                multiplicadores[nome_dg] = 20
        return tempos, multiplicadores, invalidos

    # -------------------- Botão Salvar --------------------
    def salvar_alteracoes(self):
        tempos, multiplicadores, invalidos = self.coletar_valores_atuais()
        persistence.salvar_historico_json(tempos, self.ordem_selecao, persistence.senha_salva,
                                           persistence.reconexao_ativa, multiplicadores,
                                           persistence.historico_execucoes,
                                           persistence.deteccao_automatica_ativa,
                                           persistence.telegram_ativo,
                                           persistence.telegram_chat_id,
                                           persistence.resolucao_calibrada,
                                           persistence.telegram_nome,
                                           persistence.telegram_username,
                                           persistence.telegram_ultimo_update_id)
        if invalidos:
            messagebox.showwarning(
                "Alguns valores inválidos",
                "Os tempos abaixo estavam com texto inválido e NÃO foram alterados:\n\n" + "\n".join(invalidos)
            )
        self.lbl_status.config(text="💾 Alterações salvas com sucesso!", fg=config.COLOR_SUCCESS)

    # -------------------- Botão Resetar --------------------
    def resetar_selecoes(self):
        if self.macro_rodando:
            if not messagebox.askyesno(
                "Cancelar execução",
                "Isso vai PARAR a sequência atual e limpar toda a fila.\n"
                "Você vai precisar selecionar as DGs de novo antes de iniciar.\n\n"
                "Continuar?"
            ):
                return
            self._abortar_solicitado = True
            state.evento_abortar.set()
            state.evento_pausado.clear()
            self.btn_resetar.config(state="disabled")
            self.lbl_status.config(text="⏹ Cancelando execução, aguarde...", fg=config.COLOR_DANGER)
            return
        if not self.ordem_selecao:
            return
        if not messagebox.askyesno("Confirmar reset", "Isso vai desmarcar todas as DGs selecionadas. Continuar?"):
            return
        self._limpar_selecoes_ui()

    def _limpar_selecoes_ui(self):
        for nome_dg in list(self.ordem_selecao):
            self.widgets_dg[nome_dg]["check_var"].set(False)
            self._aplicar_estado_checkbox(nome_dg, False)
        self.atualizar_badges_ordem()
        self.atualizar_estimativa_total()
        self._atualizar_status_fila()

    # -------------------- Botão Pular DG atual --------------------
    def pular_dg_atual(self):
        if not self.macro_rodando:
            return
        if not messagebox.askyesno("Pular DG", "Tem certeza que quer pular a espera da DG atual e ir pra próxima?"):
            return
        messagebox.showinfo(
            "Pular DG",
            "Depois de clicar OK, clique UMA VEZ dentro da tela do jogo (Cabal)\n"
            "para focar nela de novo.\n\n"
            "O bot só consegue continuar clicando na próxima DG depois desse clique\n"
            "(o Windows exige isso porque você acabou de clicar num botão do app)."
        )
        state.evento_pular_dg.set()
        self.lbl_status.config(text="⏭ Pulando — clique na tela do jogo pra continuar...", fg=config.COLOR_SKIP)

    # -------------------- Botão Pausar / Retomar --------------------
    def alternar_pausa(self):
        if not self.macro_rodando:
            return
        if state.evento_pausado.is_set():
            state.evento_pausado.clear()
            self.btn_pausar.config(text="⏸ Pausar")
            messagebox.showinfo(
                "Retomando",
                "Depois de clicar OK, clique UMA VEZ dentro da tela do jogo (Cabal)\n"
                "para focar nela de novo, antes do bot continuar clicando."
            )
            self.lbl_status.config(text="▶ Retomando — clique na tela do jogo pra continuar...", fg=config.COLOR_ACCENT)
        else:
            state.evento_pausado.set()
            self.btn_pausar.config(text="▶ Retomar")
            self.lbl_status.config(text="⏸ Pausado — clique em Retomar quando terminar o ajuste.", fg=config.COLOR_SKIP)

    # -------------------- Tela de Histórico --------------------
    def abrir_ou_focar_historico(self):
        if self.janela_historico is not None and self.janela_historico.winfo_exists():
            self.janela_historico.deiconify()
            self.janela_historico.lift()
            self.janela_historico.focus_force()
            self._atualizar_tabela_historico()
            return

        self.janela_historico = tk.Toplevel(self.root)
        self.janela_historico.title("Histórico de Tempos por DG")
        self.janela_historico.geometry("740x480")
        self.janela_historico.configure(bg=config.COLOR_BG)

        tk.Label(self.janela_historico, text="📊 Histórico de tempos reais por DG",
                 font=config.FONT_BOLD, bg=config.COLOR_BG, fg="#2c3e50").pack(anchor="w", padx=12, pady=(12, 2))
        tk.Label(self.janela_historico,
                 text="Baseado nas detecções automáticas confirmadas (deteccoes_dg.txt). O tempo já vem "
                      "normalizado POR EXECUÇÃO (dividido pelo multiplicador usado em cada detecção) — é "
                      "diretamente comparável ao campo de tempo da tela principal. Detecções antigas, "
                      "gravadas antes dessa correção, não entram na conta.",
                 font=config.FONT_TINY, fg=config.COLOR_MUTED, bg=config.COLOR_BG,
                 wraplength=700, justify="left").pack(anchor="w", padx=12, pady=(0, 8))

        filtro_frame = tk.Frame(self.janela_historico, bg=config.COLOR_BG)
        filtro_frame.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(filtro_frame, text="Período:", font=config.FONT_BASE, bg=config.COLOR_BG).pack(side="left", padx=(0, 6))

        botoes_periodo = []

        def _selecionar_periodo(dias, botao_clicado):
            self._periodo_historico_dias = dias
            for b in botoes_periodo:
                b.config(bg="#dfe6e9", fg="black")
            botao_clicado.config(bg=config.COLOR_ACCENT, fg="white")
            self._atualizar_tabela_historico()

        for texto, dias in [("1 dia", 1), ("3 dias", 3), ("7 dias", 7), ("30 dias", 30), ("Tudo", None)]:
            ativo = (dias == self._periodo_historico_dias)
            btn = tk.Button(filtro_frame, text=texto, font=config.FONT_TINY, relief="flat",
                             bg=config.COLOR_ACCENT if ativo else "#dfe6e9",
                             fg="white" if ativo else "black")
            btn.config(command=lambda d=dias, b=btn: _selecionar_periodo(d, b))
            btn.pack(side="left", padx=3)
            botoes_periodo.append(btn)

        tabela_frame = tk.Frame(self.janela_historico, bg=config.COLOR_BG)
        tabela_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        colunas = ("dg", "execucoes", "media_real", "estimado_atual", "diferenca")
        self.tree_historico = ttk.Treeview(tabela_frame, columns=colunas, show="headings", height=16)
        larguras = {"dg": 240, "execucoes": 80, "media_real": 160, "estimado_atual": 160, "diferenca": 110}
        titulos = {"dg": "DG", "execucoes": "Execuções", "media_real": "Tempo real/execução",
                   "estimado_atual": "Tempo configurado hoje", "diferenca": "Diferença"}
        for col in colunas:
            self.tree_historico.heading(col, text=titulos[col])
            self.tree_historico.column(col, width=larguras[col], anchor="center" if col != "dg" else "w")

        scrollbar_hist = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tree_historico.yview)
        self.tree_historico.configure(yscrollcommand=scrollbar_hist.set)
        self.tree_historico.pack(side="left", fill="both", expand=True)
        scrollbar_hist.pack(side="right", fill="y")

        self._atualizar_tabela_historico()

    def _atualizar_tabela_historico(self):
        if not (self.janela_historico and self.janela_historico.winfo_exists()):
            return
        for item in self.tree_historico.get_children():
            self.tree_historico.delete(item)

        medias = persistence.calcular_medias_por_dg(dias=self._periodo_historico_dias)
        if not medias:
            self.tree_historico.insert("", "end", values=("(sem detecções registradas nesse período)", "", "", "", ""))
            return

        for nome_dg, stats in sorted(medias.items(), key=lambda item: -item[1]["count"]):
            tempo_atual = None
            if nome_dg in self.widgets_dg:
                try:
                    tempo_atual = float(self.widgets_dg[nome_dg]["entry_widget"].get().replace(",", "."))
                except ValueError:
                    tempo_atual = None
            diferenca_txt = "—"
            if tempo_atual is not None:
                diferenca_txt = f"{tempo_atual - stats['media_tempo_base']:+.1f} min"
            self.tree_historico.insert("", "end", values=(
                nome_dg,
                stats["count"],
                f"{stats['media_tempo_base']:.1f} min",
                f"{tempo_atual:.1f} min" if tempo_atual is not None else "—",
                diferenca_txt,
            ))

    def _escolher_janela_dias(self, callback, titulo="Período", pergunta="Escolha o período:"):
        win = tk.Toplevel(self.root)
        win.title(titulo)
        win.geometry("340x150")
        win.resizable(False, False)
        win.grab_set()
        tk.Label(win, text=pergunta, font=config.FONT_BASE, wraplength=300).pack(pady=(18, 12))
        frame_botoes = tk.Frame(win)
        frame_botoes.pack()
        for texto, dias in [("1 dia", 1), ("3 dias", 3), ("7 dias", 7), ("30 dias", 30), ("Tudo", None)]:
            def _escolher(d=dias):
                win.destroy()
                callback(d)
            tk.Button(frame_botoes, text=texto, font=config.FONT_TINY, relief="flat",
                      bg="#dfe6e9", command=_escolher, width=8).pack(side="left", padx=3, pady=10)

    # -------------------- Botão Atualizar Base --------------------
    def atualizar_base_historico(self):
        if self.macro_rodando:
            messagebox.showwarning("Aviso", "Não é possível atualizar enquanto uma sequência está em execução.")
            return

        def _aplicar(dias):
            medias = persistence.calcular_medias_por_dg(dias=dias)
            if not medias:
                messagebox.showinfo("Atualizar Base", "Ainda não há histórico de detecções suficiente nesse período.")
                return
            atualizados = []
            for nome_dg, stats in medias.items():
                if nome_dg not in self.widgets_dg:
                    continue
                novo_tempo = round(stats["media_tempo_base"], 1)
                comp = self.widgets_dg[nome_dg]
                comp["entry_widget"].delete(0, "end")
                comp["entry_widget"].insert(0, str(novo_tempo))
                atualizados.append(f"• {nome_dg}: {novo_tempo} min/execução ({stats['count']}x)")

            self.atualizar_estimativa_total()
            if self.janela_historico and self.janela_historico.winfo_exists():
                self._atualizar_tabela_historico()

            resumo = "\n".join(atualizados[:20])
            if len(atualizados) > 20:
                resumo += f"\n... e mais {len(atualizados) - 20}."
            messagebox.showinfo(
                "Atualizar Base",
                f"{len(atualizados)} DG(s) tiveram o tempo atualizado com base na média real "
                f"do histórico:\n\n{resumo}\n\nClique em 'Salvar' pra gravar essas mudanças de vez."
            )

        self._escolher_janela_dias(
            _aplicar, titulo="Atualizar Base",
            pergunta="Considerar histórico de quantos dias pra recalcular o tempo de cada DG?"
        )

    # -------------------- Painel Terminal --------------------
    def abrir_ou_focar_terminal(self):
        if self.janela_terminal is not None and self.janela_terminal.winfo_exists():
            self.janela_terminal.deiconify()
            self.janela_terminal.lift()
            self.janela_terminal.focus_force()
            return

        self.janela_terminal = tk.Toplevel(self.root)
        self.janela_terminal.title("Terminal — Detecções de Fim de DG")
        self.janela_terminal.geometry("640x380")
        self.janela_terminal.configure(bg=config.COLOR_BG)

        tk.Label(self.janela_terminal, text="🖥️ Log de detecções automáticas",
                 font=config.FONT_BOLD, bg=config.COLOR_BG, fg="#2c3e50").pack(anchor="w", padx=12, pady=(12, 2))
        tk.Label(self.janela_terminal,
                 text="Cada linha aqui é uma DG que a detecção automática confirmou de verdade,\n"
                      "comparando o tempo que ela realmente levou com o tempo que você programou.",
                 font=config.FONT_TINY, fg=config.COLOR_MUTED, bg=config.COLOR_BG,
                 justify="left", anchor="w").pack(anchor="w", padx=12, pady=(0, 8))

        frame_texto = tk.Frame(self.janela_terminal, bg=config.COLOR_BG)
        frame_texto.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        scrollbar = ttk.Scrollbar(frame_texto, orient="vertical")
        self.txt_terminal = tk.Text(frame_texto, wrap="word", font=("Consolas", 9),
                                     bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4",
                                     state="disabled", yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.txt_terminal.yview)
        self.txt_terminal.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        rodape = tk.Frame(self.janela_terminal, bg=config.COLOR_BG)
        rodape.pack(fill="x", padx=12, pady=(0, 12))
        tk.Label(rodape, text=f"Também salvo em: {config.LOG_DETECCOES_FILE}",
                 font=config.FONT_TINY, fg=config.COLOR_MUTED, bg=config.COLOR_BG).pack(side="left")
        tk.Button(rodape, text="Limpar", font=config.FONT_TINY, relief="flat", bg="#dfe6e9",
                  command=self._limpar_terminal).pack(side="right")

        self._preencher_terminal()

    def _preencher_terminal(self):
        if not (self.janela_terminal and self.janela_terminal.winfo_exists()):
            return
        self.txt_terminal.config(state="normal")
        self.txt_terminal.delete("1.0", "end")
        if not self.log_deteccoes_buffer:
            self.txt_terminal.insert("end", "(nenhuma detecção registrada ainda nesta sessão)\n")
        for linha in self.log_deteccoes_buffer:
            self.txt_terminal.insert("end", linha + "\n")
        self.txt_terminal.see("end")
        self.txt_terminal.config(state="disabled")

    def _adicionar_linha_terminal(self, linha):
        self.log_deteccoes_buffer.append(linha)
        if self.janela_terminal and self.janela_terminal.winfo_exists():
            self.txt_terminal.config(state="normal")
            self.txt_terminal.insert("end", linha + "\n")
            self.txt_terminal.see("end")
            self.txt_terminal.config(state="disabled")

    def _limpar_terminal(self):
        self.log_deteccoes_buffer.clear()
        self._preencher_terminal()

   

    # -------------------- Mapeador de coordenadas --------------------
    def abrir_tela_mapeamento(self):
        if self.janela_mapeamento is not None and self.janela_mapeamento.winfo_exists():
            self.janela_mapeamento.deiconify()
            self.janela_mapeamento.lift()
            self.janela_mapeamento.focus_force()
            return

        self.janela_mapeamento = tk.Toplevel(self.root)
        self.janela_mapeamento.title("Mapeador de Coordenadas")
        self.janela_mapeamento.geometry("420x330")
        self.janela_mapeamento.resizable(False, False)
        self.janela_mapeamento.grab_set()
        self.janela_mapeamento.configure(bg=config.COLOR_BG)

        tk.Label(self.janela_mapeamento, text="🧭 Mapeador de Coordenadas", font=("Segoe UI", 12, "bold"),
                 bg=config.COLOR_BG, fg="#3c3c3c").pack(padx=20, pady=(15, 8), anchor="w")

        tk.Label(self.janela_mapeamento,
                 text=("Use BOTÃO DIREITO para capturar o ponto ou arrastar a região. "
                       "Depois confirme com o BOTÃO DO MEIO (scroll).\n\n"
                       "Atalhos: F2 pula o item atual e ESC encerra o mapeamento."),
                 font=config.FONT_TINY, fg=config.COLOR_MUTED, bg=config.COLOR_BG,
                 wraplength=380, justify="left").pack(padx=20, pady=(0, 12), anchor="w")

        self.lbl_mapeamento_status = tk.Label(self.janela_mapeamento,
                                              text="Pronto para mapear. Clique em Iniciar para começar.",
                                              font=config.FONT_BASE, fg="black", bg=config.COLOR_BG,
                                              wraplength=380, justify="left")
        self.lbl_mapeamento_status.pack(padx=20, pady=(0, 8), anchor="w")

        tipo_frame = tk.Frame(self.janela_mapeamento, bg=config.COLOR_BG)
        tipo_frame.pack(fill="x", padx=20, pady=(0, 8))
        tk.Label(tipo_frame, text="Tipo de captura:", font=config.FONT_BASE, fg="#3c3c3c", bg=config.COLOR_BG).pack(side="left")
        self.combo_tipo_mapeamento = ttk.Combobox(tipo_frame, values=["AUTO", "PONTO", "REGIAO"],
                                                 state="readonly", width=10)
        self.combo_tipo_mapeamento.set("AUTO")
        self.combo_tipo_mapeamento.pack(side="right")
        self.combo_tipo_mapeamento.bind("<<ComboboxSelected>>", self._on_tipo_mapeamento_change)

        controle_frame = tk.Frame(self.janela_mapeamento, bg=config.COLOR_BG)
        controle_frame.pack(fill="x", padx=20, pady=(5, 0))

        self.btn_iniciar_mapeamento = tk.Button(controle_frame, text="▶ Iniciar mapeamento",
                                                font=config.FONT_BASE, relief="flat", bg="#27ae60",
                                                fg="white", command=self._iniciar_mapeamento)
        self.btn_iniciar_mapeamento.pack(side="left", expand=True, fill="x")

        self.btn_parar_mapeamento = tk.Button(controle_frame, text="⏹ Parar",
                                              font=config.FONT_BASE, relief="flat", bg="#e74c3c",
                                              fg="white", state="disabled", command=self._parar_mapeamento)
        self.btn_parar_mapeamento.pack(side="left", expand=True, fill="x", padx=(8, 0))

        self.btn_salvar_mapeamento = tk.Button(self.janela_mapeamento, text="Salvar mapeamento atual",
                                               font=config.FONT_BASE, relief="flat", bg="#dfe6e9",
                                               command=self._salvar_mapeamento_atual, state="disabled")
        self.btn_salvar_mapeamento.pack(fill="x", padx=20, pady=14)

        self._atualizar_status_mapeamento()

    def _set_mapeamento_status(self, texto):
        if self.janela_mapeamento and self.janela_mapeamento.winfo_exists():
            self.janela_mapeamento.after(0, lambda: self.lbl_mapeamento_status.config(text=texto))

    def _on_tipo_mapeamento_change(self, _event=None):
        if hasattr(self, "mapeador") and self.mapeador:
            tipo = self.combo_tipo_mapeamento.get()
            if tipo == "AUTO":
                tipo = None
            self.mapeador.set_tipo_override(tipo)

    def _atualizar_status_mapeamento(self):
        texto = "Nenhum mapeamento personalizado carregado." if not persistence.mapeamento_personalizado else (
            "Mapeamento personalizado carregado. Clique em Salvar para persistir." )
        self.lbl_mapeamento_status.config(text=texto)
        self.btn_salvar_mapeamento.config(state="normal" if persistence.mapeamento_personalizado else "disabled")

    def _iniciar_mapeamento(self):
        self.btn_iniciar_mapeamento.config(state="disabled")
        self.btn_parar_mapeamento.config(state="normal")
        self.btn_salvar_mapeamento.config(state="disabled")
        self.mapeador = mapeador.Mapeador(status_callback=self._set_mapeamento_status,
                                          finished_callback=self._finalizar_mapeamento)
        self.mapeador.iniciar()

    def _parar_mapeamento(self):
        if hasattr(self, "mapeador") and self.mapeador:
            self.mapeador.stop()
        self.btn_iniciar_mapeamento.config(state="normal")
        self.btn_parar_mapeamento.config(state="disabled")

    def _finalizar_mapeamento(self, resultados):
        persistence.mapeamento_personalizado = resultados
        config.aplicar_mapeamento_personalizado(resultados)
        tempos, multiplicadores, invalidos = self.coletar_valores_atuais()
        persistence.salvar_historico_json(
            tempos,
            self.ordem_selecao,
            persistence.senha_salva,
            persistence.reconexao_ativa,
            multiplicadores,
            persistence.historico_execucoes,
            persistence.deteccao_automatica_ativa,
            persistence.telegram_ativo,
            persistence.telegram_chat_id,
            persistence.resolucao_calibrada,
            persistence.telegram_nome,
            persistence.telegram_username,
            persistence.telegram_ultimo_update_id,
            mapeamento_personalizado=resultados,
        )
        if self.janela_mapeamento and self.janela_mapeamento.winfo_exists():
            self.janela_mapeamento.after(0, self._atualizar_status_mapeamento)
            self.btn_iniciar_mapeamento.config(state="normal")
            self.btn_parar_mapeamento.config(state="disabled")
        self._set_mapeamento_status("Mapeamento concluído e salvo. Feche essa janela ou inicie novamente se quiser mapear outra vez.")

    def _salvar_mapeamento_atual(self):
        if not persistence.mapeamento_personalizado:
            messagebox.showwarning("Aviso", "Nenhum mapeamento personalizado carregado para salvar.")
            return
        tempos, multiplicadores, invalidos = self.coletar_valores_atuais()
        persistence.salvar_historico_json(
            tempos,
            self.ordem_selecao,
            persistence.senha_salva,
            persistence.reconexao_ativa,
            multiplicadores,
            persistence.historico_execucoes,
            persistence.deteccao_automatica_ativa,
            persistence.telegram_ativo,
            persistence.telegram_chat_id,
            persistence.resolucao_calibrada,
            persistence.telegram_nome,
            persistence.telegram_username,
            persistence.telegram_ultimo_update_id,
            mapeamento_personalizado=persistence.mapeamento_personalizado,
        )
        messagebox.showinfo("Sucesso", "Mapeamento personalizado salvo no arquivo de configurações.")
        self._atualizar_status_mapeamento()

# -------------------- Modal de Conexão Telegram (OTP) --------------------
    def _abrir_modal_conectar_telegram(self, on_sucesso_callback):
        # 🛑 TRAVA: Se o usuário já estiver conectado, bloqueia e avisa na tela
        if persistence.telegram_ativo and persistence.telegram_chat_id:
            usuario = f"@{persistence.telegram_username}" if persistence.telegram_username else persistence.telegram_nome
            messagebox.showinfo(
                "Telegram Já Conectado",
                f"Sua conta já está vinculada!\n\n"
                f"👤 Usuário: {usuario}\n"
                f"🆔 Chat ID: {persistence.telegram_chat_id}\n\n"
                "Para vincular outra conta, você precisa desvincular primeiro."
            )
            return

        win_tg = tk.Toplevel(self.root)
        win_tg.title("Conectar Telegram")
        win_tg.geometry("420x280")
        win_tg.resizable(False, False)
        win_tg.grab_set()

        codigo = telegram_notifier.gerar_codigo()

        tk.Label(win_tg, text="📲 Vincular sua conta do Telegram", font=("Segoe UI", 11, "bold"), fg="#2c3e50").pack(pady=(15, 5))
        
        instrucoes = (
            f"1. Abra o Telegram e procure por {getattr(config, 'TELEGRAM_BOT_USERNAME', 'Bot')}\n"
            f"2. Envie exatamente o código abaixo para o Bot:"
        )
        tk.Label(win_tg, text=instrucoes, font=config.FONT_BASE, justify="left").pack(padx=20, pady=5)

        lbl_codigo = tk.Label(win_tg, text=codigo, font=("Consolas", 18, "bold"), fg="#2980b9", bg="#ecf0f1", padx=15, pady=5)
        lbl_codigo.pack(pady=10)

        lbl_status_tg = tk.Label(win_tg, text="⏳ Aguardando envio do código no Telegram...", font=config.FONT_TINY, fg="gray")
        lbl_status_tg.pack(pady=5)

        cancelar_event = threading.Event()

        def _fechar():
            cancelar_event.set()
            win_tg.destroy()

        win_tg.protocol("WM_DELETE_WINDOW", _fechar)
        tk.Button(win_tg, text="Cancelar", font=config.FONT_TINY, command=_fechar).pack(pady=5)

        def callback_status_ui(texto):
            if win_tg.winfo_exists():
                lbl_status_tg.config(text=texto)

        def _worker_polling():
            # Executa o conectar_usuario (retorna tupla: ok, resultado_ou_erro)
            sucesso, res = telegram_notifier.conectar_usuario(
                codigo, 
                timeout_segundos=300, 
                callback_status=callback_status_ui
            )

            if sucesso and not cancelar_event.is_set():
                # 💾 Grava a alteração do Telegram no JSON
                tempos, multiplicadores, _ = self.coletar_valores_atuais()
                persistence.salvar_historico_json(
                    tempos,
                    self.ordem_selecao,
                    persistence.senha_salva,
                    persistence.reconexao_ativa,
                    multiplicadores,
                    persistence.historico_execucoes,
                    persistence.deteccao_automatica_ativa,
                    persistence.telegram_ativo,
                    persistence.telegram_chat_id,
                    persistence.resolucao_calibrada,
                    persistence.telegram_nome,
                    persistence.telegram_username,
                    persistence.telegram_ultimo_update_id,
                    mapeamento_personalizado=persistence.mapeamento_personalizado,
                )

                def _sucesso():
                    if win_tg.winfo_exists():
                        win_tg.destroy()
                    messagebox.showinfo("Telegram Conectado", f"Sucesso! Conta vinculada a {res.get('nome', 'Usuário')}.")
                    on_sucesso_callback()

                self.root.after(0, _sucesso)

            elif not cancelar_event.is_set():
                def _falha():
                    if win_tg.winfo_exists():
                        mensagem_erro = res if isinstance(res, str) else "Tempo esgotado ou código não encontrado."
                        lbl_status_tg.config(text=f"❌ {mensagem_erro}", fg=config.COLOR_DANGER)

                self.root.after(0, _falha)

        threading.Thread(target=_worker_polling, daemon=True).start()

    # -------------------- Configurações --------------------
    def abrir_tela_config(self):
        config_win = tk.Toplevel(self.root)
        config_win.title("Parâmetros do Sistema")
        config_win.geometry("420x580")
        config_win.resizable(False, False)
        config_win.grab_set()

        # --- Credenciais e Resolução ---
        tk.Label(
            config_win,
            text="Nome do personagem:",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=20, pady=(15, 2))

        ent_nome = tk.Entry(config_win, width=32)
        ent_nome.insert(0, persistence.nome_personagem)
        ent_nome.pack(anchor="w", padx=20, pady=2)

        tk.Label(config_win, text="Senha da Conta:", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(15, 2))
        ent_senha = tk.Entry(config_win, width=32, show="*")
        ent_senha.insert(0, persistence.senha_salva)
        ent_senha.pack(anchor="w", padx=20, pady=2)



        # --- Agendamento de Horário Desejado ---
        tk.Frame(config_win, height=1, bg="#dcdde1").pack(fill="x", padx=20, pady=10)
        tk.Label(config_win, text="Horário Agendado:", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20)
        
        agenda_frame = tk.Frame(config_win)
        agenda_frame.pack(anchor="w", padx=20, pady=4)

        chk_agendar_config = tk.Checkbutton(
            agenda_frame, text="Agendar horário de início:", variable=self.var_agendar, font=("Segoe UI", 9),
            command=lambda: ent_horario_config.config(state="normal" if self.var_agendar.get() else "disabled")
        )
        chk_agendar_config.pack(side="left")

        ent_horario_config = tk.Entry(agenda_frame, width=6, justify="center")
        ent_horario_config.insert(0, self.horario_agendado_val)
        ent_horario_config.config(state="normal" if self.var_agendar.get() else "disabled")
        ent_horario_config.pack(side="left", padx=(5, 0))

        # --- Opções de Sistema ---
        var_active = tk.BooleanVar(value=persistence.reconexao_ativa)
        tk.Checkbutton(config_win, text="Ativar Auto-Reconnect em caso de quedas", variable=var_active, font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=(6, 2))

        var_deteccao = tk.BooleanVar(value=persistence.deteccao_automatica_ativa)
        tk.Checkbutton(config_win, text="Detecção automática de fim de DG (experimental)", variable=var_deteccao, font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=2)

        # --- Telegram ---
        tk.Frame(config_win, height=1, bg="#dcdde1").pack(fill="x", padx=20, pady=10)
        tk.Label(config_win, text="Notificações no Telegram:", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20)

        var_tg_ativo = tk.BooleanVar(value=persistence.telegram_ativo)
        tk.Checkbutton(config_win, text="Ativar notificações", variable=var_tg_ativo, font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=(2, 4))

        frame_tg_info = tk.Frame(config_win)
        frame_tg_info.pack(anchor="w", padx=20, pady=2)

        lbl_tg_status = tk.Label(frame_tg_info, text="", font=config.FONT_BASE)
        lbl_tg_status.pack(anchor="w")

        def _atualizar_status_tg_ui():
            if persistence.telegram_chat_id:
                nome = persistence.telegram_nome or "Conectado"
                user = f" (@{persistence.telegram_username})" if persistence.telegram_username else ""
                lbl_tg_status.config(text=f"🟢 Conectado: {nome}{user}", fg=config.COLOR_SUCCESS)
            else:
                lbl_tg_status.config(text="🔴 Não conectado", fg=config.COLOR_DANGER)

        _atualizar_status_tg_ui()

        btn_frame_tg = tk.Frame(config_win)
        btn_frame_tg.pack(anchor="w", padx=20, pady=6)

        def _iniciar_conexao_tg():
            self._abrir_modal_conectar_telegram(on_sucesso_callback=lambda: [_atualizar_status_tg_ui(), salvar_e_persistir_tudo(fechar_janela=False)])

        tk.Button(btn_frame_tg, text="📲 Conectar Telegram", font=config.FONT_TINY, bg="#3498db", fg="white", relief="flat", command=_iniciar_conexao_tg).pack(side="left", padx=(0, 6))

        def testar_telegram():
            if not persistence.telegram_chat_id:
                messagebox.showerror("Telegram", "Nenhum Telegram conectado ainda. Clique em 'Conectar Telegram'.")
                return
            
            def _enviar():
                sucesso, detalhe = telegram_notifier.enviar_mensagem("✅ Teste do Dungeon Helper — Conexão OK!")
                cor = config.COLOR_SUCCESS if sucesso else config.COLOR_DANGER
                self.root.after(0, lambda: messagebox.showinfo("Teste Telegram", detalhe) if sucesso else messagebox.showerror("Teste Telegram", detalhe))

            threading.Thread(target=_enviar, daemon=True).start()

        tk.Button(btn_frame_tg, text="🧪 Testar Notificação", font=config.FONT_TINY, bg="#dfe6e9", relief="flat", command=testar_telegram).pack(side="left", padx=(6, 0))

        def desvincular_telegram():
            if not persistence.telegram_chat_id:
                messagebox.showinfo("Telegram", "Nenhuma conta vinculada no momento.")
                return
            if not messagebox.askyesno(
                "Desvincular Telegram",
                "Isso vai remover a vinculação atual e parar de enviar notificações.\n"
                "Você pode vincular outra conta depois. Continuar?"
            ):
                return
            sucesso, msg = telegram_notifier.desconectar_usuario()
            if sucesso:
                _atualizar_status_tg_ui()
                var_tg_ativo.set(False)
                messagebox.showinfo("Telegram", "Conta desvinculada com sucesso.")
            else:
                messagebox.showerror("Telegram", f"Falha ao desvincular: {msg}")

        tk.Button(btn_frame_tg, text="🔌 Desvincular", font=config.FONT_TINY, bg="#e74c3c", fg="white",
                  relief="flat", command=desvincular_telegram).pack(side="left", padx=(6, 0))

        # --- Salvar Tudo ---
        def salvar_e_persistir_tudo(fechar_janela=True):
            persistence.nome_personagem = ent_nome.get().strip()
            persistence.senha_salva = ent_senha.get()
            persistence.reconexao_ativa = var_active.get()
            persistence.deteccao_automatica_ativa = var_deteccao.get()
            persistence.telegram_ativo = var_tg_ativo.get()

            if self.var_agendar.get():
                self.horario_agendado_val = ent_horario_config.get().strip()

            tempos, multiplicadores, _ = self.coletar_valores_atuais()
            persistence.salvar_historico_json(
                tempos, self.ordem_selecao, persistence.senha_salva,
                persistence.reconexao_ativa, multiplicadores,
                persistence.historico_execucoes,
                persistence.deteccao_automatica_ativa,
                persistence.telegram_ativo,
                persistence.telegram_chat_id,
                persistence.telegram_nome,
                persistence.telegram_username,
                persistence.telegram_ultimo_update_id
            )
            if fechar_janela:
                config_win.destroy()
                messagebox.showinfo("Sucesso", "Definições salvas com sucesso!")

        tk.Button(config_win, text="💾 Salvar Configurações", font=("Segoe UI", 9, "bold"), bg=config.COLOR_ACCENT, fg="white", relief="flat", command=lambda: salvar_e_persistir_tudo(fechar_janela=True), width=22).pack(pady=15)

    # -------------------- Estado habilitado/desabilitado --------------------
    def definir_estado_execucao(self, rodando):
        self.macro_rodando = rodando
        estado_botoes = "disabled" if rodando else "normal"
        self.btn_iniciar.config(state=estado_botoes)
        self.btn_salvar.config(state=estado_botoes)
        self.btn_atualizar_base.config(state=estado_botoes)
        self.btn_resetar.config(state="normal")
        self.btn_pular.config(state="normal" if rodando else "disabled")
        self.btn_pausar.config(state="normal" if rodando else "disabled")
        if not rodando:
            self.btn_pausar.config(text="⏸ Pausar")
        for comp in self.widgets_dg.values():
            comp["check_widget"].config(state=estado_botoes)
            comp["entry_widget"].config(state=estado_botoes)
            comp["combo_widget"].config(state="disabled" if rodando else "readonly")

    # -------------------- Callbacks vindos da thread de execução --------------------
    def _callback_inicio(self, nome_dg, idx, total):
        self.root.after(0, lambda: self._on_dg_iniciada_ui(nome_dg, idx, total))

    def _on_dg_iniciada_ui(self, nome_dg, idx, total):
        self.lbl_status.config(text=f"▶ Executando {idx}/{total}: {nome_dg}", fg=config.COLOR_ACCENT)
        comp = self.widgets_dg.get(nome_dg)
        if comp:
            comp["row_frame"].configure(bg=config.COLOR_RUNNING)
            comp["lbl_widget"].configure(bg=config.COLOR_RUNNING)
            comp["hist_label"].configure(bg=config.COLOR_RUNNING)
            comp["check_widget"].configure(bg=config.COLOR_RUNNING)

    def _callback_fim(self, nome_dg, idx, total):
        persistence.registrar_execucao_no_historico(nome_dg)
        self.root.after(0, lambda: self._on_dg_concluida_ui(nome_dg))

    def _callback_deteccao(self, nome_dg, tempo_estimado_min, tempo_real_min, diferenca_min, percentual):
        self.root.after(0, lambda: self._on_dg_detectada_ui(
            nome_dg, tempo_estimado_min, tempo_real_min, diferenca_min, percentual
        ))

    def _on_dg_detectada_ui(self, nome_dg, tempo_estimado_min, tempo_real_min, diferenca_min, percentual):
        self.lbl_status.config(
            text=f"🔍 Detecção automática: '{nome_dg}' finalizou em {tempo_real_min:.1f} min! Indo para a próxima...",
            fg=config.COLOR_SUCCESS
        )
        comp = self.widgets_dg.get(nome_dg)
        if comp:
            comp["hist_label"].configure(text="🔍 detectado agora")

        hora_atual = time.strftime("%H:%M:%S")
        linha = (
            f"[{hora_atual}] 🔍 '{nome_dg}' finalizada em {tempo_real_min:.1f} min "
            f"(estimado: {tempo_estimado_min:.1f} min — {percentual:.0f}% de folga no tempo programado)"
        )
        self._adicionar_linha_terminal(linha)

    def _callback_aguardando_horario(self, alvo, restante):
        self.root.after(0, lambda: self._atualizar_status_agendamento(alvo, restante))

    def _atualizar_status_agendamento(self, alvo, restante):
        total_seg = max(0, int(restante.total_seconds()))
        h, resto = divmod(total_seg, 3600)
        m, s = divmod(resto, 60)
        self.lbl_status.config(
            text=f"🕐 Agendado — aguardando início às {alvo.strftime('%H:%M')} (faltam {h:02d}:{m:02d}:{s:02d})",
            fg=config.COLOR_ACCENT
        )

    def _on_dg_concluida_ui(self, nome_dg):
        comp = self.widgets_dg.get(nome_dg)
        if comp:
            bg = config.COLOR_SELECTED
            comp["row_frame"].configure(bg=bg)
            comp["lbl_widget"].configure(bg=bg)
            comp["hist_label"].configure(bg=bg, text=persistence.formatar_historico(nome_dg))
            comp["check_widget"].configure(bg=bg)

    # -------------------- Cronômetro --------------------
    def atualizar_timer(self, inicio_tempo):
        if self.macro_rodando:
            decorrido = int(time.time() - inicio_tempo)
            h, m, s = decorrido // 3600, (decorrido % 3600) // 60, decorrido % 60
            self.lbl_timer.config(text=f"⏱️ Tempo em execução: {h:02d}:{m:02d}:{s:02d}")
            self.root.after(1000, lambda: self.atualizar_timer(inicio_tempo))

    # -------------------- Botão Iniciar --------------------
    def coletar_e_disparar(self):
        if self.macro_rodando:
            messagebox.showwarning("Aviso", "Uma sequência já está em execução!")
            return
        if not self.ordem_selecao:
            messagebox.showerror("Erro de Seleção", "Sua lista de execução está vazia! Marque o checkbox das DGs desejadas.")
            return

        horario_agendado = None
        if self.var_agendar.get():
            texto_hora = self.horario_agendado_val.strip()
            if not re.match(r'^([01]\d|2[0-3]):[0-5]\d$', texto_hora):
                messagebox.showerror(
                    "Horário inválido",
                    "Ajuste o horário no formato HH:MM (ex: 14:30) nas Configurações ⚙ antes de iniciar."
                )
                return
            horario_agendado = texto_hora

        tempos, multiplicadores, _ = self.coletar_valores_atuais()

        lista_final_envio = []
        erros_selecionadas = []
        for nome_dg in self.ordem_selecao:
            raw = self.widgets_dg[nome_dg]["entry_widget"].get().replace(",", ".")
            try:
                t = float(raw)
                if t <= 0:
                    raise ValueError
            except ValueError:
                erros_selecionadas.append(nome_dg)
                continue
            mult = multiplicadores[nome_dg]
            lista_final_envio.append((nome_dg, t, mult))

        if erros_selecionadas:
            messagebox.showerror(
                "Erro de Digitação",
                "As DGs abaixo, que estão na fila, têm tempo inválido:\n\n" + "\n".join(erros_selecionadas) +
                "\n\nCorrija antes de iniciar."
            )
            return

        persistence.salvar_historico_json(
            tempos, self.ordem_selecao, persistence.senha_salva,
            persistence.reconexao_ativa, multiplicadores,
            persistence.historico_execucoes,
            persistence.deteccao_automatica_ativa,
            persistence.telegram_ativo,
            persistence.telegram_chat_id,
            persistence.resolucao_calibrada,
            persistence.telegram_nome,
            persistence.telegram_username,
            persistence.telegram_ultimo_update_id
        )

        state.evento_pular_dg.clear()
        state.evento_pausado.clear()
        state.evento_abortar.clear()
        self._abortar_solicitado = False
        self.definir_estado_execucao(True)
        self.lbl_status.config(text="▶ Sequência iniciada...", fg="green")

        messagebox.showinfo(
            "Antes de começar",
            "Depois de clicar OK, clique UMA VEZ dentro da tela do jogo (Cabal)\n"
            "para focar o mouse nela.\n\n"
            + (f"A sequência foi agendada pra começar às {horario_agendado}. Depois\n"
               "desse clique, o bot só fica esperando o horário chegar."
               if horario_agendado else
               "A sequência só começa a rodar depois desse clique.")
        )

        inicio_tempo = time.time()
        self.atualizar_timer(inicio_tempo)

        def rodar_async():
            try:
                macro_engine.rodar_macro_sequencial(
                    lista_final_envio,
                    persistence.repositorio_dinamico,
                    callback_inicio=self._callback_inicio,
                    callback_fim=self._callback_fim,
                    callback_deteccao=self._callback_deteccao,
                    horario_agendado=horario_agendado,
                    callback_aguardando_horario=self._callback_aguardando_horario,
                )
            except Exception as e:
                erro_str = str(e)
                print(f"[ERRO] A execução foi interrompida por um erro inesperado: {erro_str}")
                self.root.after(0, lambda msg=erro_str: self._erro_na_execucao(msg))
                return
            self.root.after(0, self._finalizar_execucao)

        threading.Thread(target=rodar_async, daemon=True).start()

    def _erro_na_execucao(self, erro_msg):
        self.definir_estado_execucao(False)
        self.lbl_timer.config(text="⏱️ Tempo em execução: 00:00:00")
        self.lbl_status.config(text="❌ Execução interrompida por erro (veja o popup).", fg=config.COLOR_DANGER)

        telegram_notifier.enviar_mensagem_async(
            f"🚨 O Dungeon Helper travou com um erro inesperado e parou de rodar:\n{erro_msg}"
        )

        mensagem = erro_msg
        if "fail-safe" in erro_msg.lower():
            mensagem = (
                "O PyAutoGUI tem uma trava de segurança: se o mouse encostar em\n"
                "QUALQUER canto da tela no exato momento em que o bot tenta clicar,\n"
                "ele interrompe tudo na hora (proteção de fábrica contra o bot\n"
                "'descontrolar').\n\n"
                "Provavelmente seu mouse estava parado num canto (ex: depois de um\n"
                "alt-tab) bem na hora que o bot foi clicar.\n\n"
                "A fila continua selecionada — é só evitar deixar o mouse em algum\n"
                "canto da tela e clicar em 'Iniciar Sequência' de novo."
            )
        messagebox.showerror("Erro na execução", mensagem)

    def _finalizar_execucao(self):
        self.definir_estado_execucao(False)
        if getattr(self, "_abortar_solicitado", False):
            self._abortar_solicitado = False
            state.evento_abortar.clear()
            self._limpar_selecoes_ui()
            self.lbl_status.config(text="⏹ Execução cancelada. Selecione as DGs novamente.", fg=config.COLOR_DANGER)
        else:
            self.lbl_status.config(text="✅ Sequência concluída com sucesso!", fg=config.COLOR_SUCCESS)
        self.lbl_timer.config(text="⏱️ Tempo em execução: 00:00:00")