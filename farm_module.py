import json
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

DEFAULT_CATALOG = [
    {"name": "Jóia Amarela Enfraquecida", "value": 40000000},
    {"name": "Jóia Azul Enfraquecida", "value": 120000000},
    {"name": "Jóia Laranja Enfraquecida", "value": 20000000},
    {"name": "Jóia Verde Enfraquecida", "value": 80000000},
    {"name": "Jóia Vermelha Enfraquecida", "value": 12000000},
    {"name": "Jóia Violeta Enfraquecida", "value": 180000000},
    {"name": "Núcleo Arcano (Altíssimo)", "value": 200000},
    {"name": "Núcleo Arcano (Alto)", "value": 950000},
    {"name": "Núcleo Arcano (Médio)", "value": 700000},
    {"name": "Set de Núcleo de Aprimoramento (Altíssimo)", "value": 1000000},
    {"name": "Set de Núcleo de Aprimoramento (Alto)", "value": 200000},
    {"name": "Set de Núcleo de Aprimoramento (Baixo)", "value": 250000},
    {"name": "Set de Núcleo de Aprimoramento (Extremo)", "value": 1100000},
    {"name": "Set de Núcleo de Aprimoramento (Médio)", "value": 1200000}
]

class FarmModuleTab(ttk.Frame):
    def __init__(self, parent, persistence):
        """
        :param parent: Container (ttk.Notebook)
        :param persistence: Instância do seu gerenciador de persistência JSON
        """
        super().__init__(parent)
        self.persistence = persistence
        
        # Carrega dados do JSON ou inicializa com o catálogo padrão
        self.catalog = []
        self.drops = []
        self._carregar_dados_persistence()

        self._setup_ui()
        self.render()

    def _carregar_dados_persistence(self):
        """Lê os dados da chave 'farm' do JSON através do gerenciador de persistência."""
        # Tenta carregar dados existentes do gerenciador de persistência
        dados_farm = getattr(self.persistence, "farm", {})
        
        # Se não houver catálogo no JSON, popula com a lista default
        if not dados_farm.get("catalogo"):
            self.catalog = list(DEFAULT_CATALOG)
        else:
            self.catalog = dados_farm.get("catalogo", [])

        self.drops = dados_farm.get("drops", [])
        self._salvar_dados_persistence()

    def _salvar_dados_persistence(self):
        """Atualiza a chave 'farm' no objeto e grava no arquivo JSON."""
        self.persistence.farm = {
            "catalogo": self.catalog,
            "drops": self.drops
        }
        # Executa o método de salvamento padrão do app
        if hasattr(self.persistence, "salvar_historico_json"):
            self.persistence.salvar_historico_json()
        elif hasattr(self.persistence, "salvar"):
            self.persistence.salvar()

    def _setup_ui(self):
        # Header / Ações
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header, text="CABAL ONLINE / FARM TRACKER", font=("Helvetica", 8, "bold")).pack(anchor=tk.W)
        ttk.Label(header, text="Resumo do seu farm", font=("Helvetica", 14, "bold")).pack(anchor=tk.W)
        
        btn_box = ttk.Frame(header)
        btn_box.pack(anchor=tk.E, side=tk.RIGHT, pady=5)
        ttk.Button(btn_box, text="Importar Drops", command=self.import_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_box, text="Gerenciar Catálogo", command=self.open_catalog_dialog).pack(side=tk.LEFT, padx=5)

        # Filtros
        filters_frame = ttk.LabelFrame(self, text="Filtros")
        filters_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(filters_frame, text="Período:").pack(side=tk.LEFT, padx=5)
        self.combo_periodo = ttk.Combobox(filters_frame, values=["Todo o período", "Hoje", "Últimos 7 dias", "Últimos 30 dias"], state="readonly")
        self.combo_periodo.current(0)
        self.combo_periodo.pack(side=tk.LEFT, padx=5)
        self.combo_periodo.bind("<<ComboboxSelected>>", lambda e: self.render())

        ttk.Label(filters_frame, text="Ordenar por:").pack(side=tk.LEFT, padx=5)
        self.combo_ordem = ttk.Combobox(filters_frame, values=["Maior valor", "Mais farmados", "Nome do item"], state="readonly")
        self.combo_ordem.current(0)
        self.combo_ordem.pack(side=tk.LEFT, padx=5)
        self.combo_ordem.bind("<<ComboboxSelected>>", lambda e: self.render())

        # Cards com Resumo
        cards_frame = ttk.Frame(self)
        cards_frame.pack(fill=tk.X, padx=10, pady=10)

        self.lbl_val_total = self._create_card(cards_frame, "Valor total farmado", "0 Alz")
        self.lbl_total_drops = self._create_card(cards_frame, "Itens recebidos", "0")
        self.lbl_unique_items = self._create_card(cards_frame, "Itens diferentes", "0")
        self.lbl_best_drop = self._create_card(cards_frame, "Melhor drop", "—")

        # Tabela Detalhada
        table_frame = ttk.LabelFrame(self, text="Itens Farmados")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("item", "quantidade", "val_unit", "val_total", "data")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("item", text="Item")
        self.tree.heading("quantidade", text="Quantidade")
        self.tree.heading("val_unit", text="Valor Unitário")
        self.tree.heading("val_total", text="Valor Total")
        self.tree.heading("data", text="Último Drop")
        
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_card(self, parent, title, val_def):
        f = ttk.Frame(parent, relief=tk.GROOVE, borderwidth=1)
        f.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5)
        ttk.Label(f, text=title, font=("Helvetica", 8)).pack(anchor=tk.W, padx=5, pady=2)
        lbl = ttk.Label(f, text=val_def, font=("Helvetica", 11, "bold"))
        lbl.pack(anchor=tk.W, padx=5, pady=2)
        return lbl

    def _normalize(self, text):
        return str(text).lower().strip()

    def get_item_value(self, name):
        norm = self._normalize(name)
        for x in self.catalog:
            if self._normalize(x["name"]) == norm:
                return x["value"]
        return 0

    def aggregate_drops(self):
        result = {}
        for d in self.drops:
            val = self.get_item_value(d["item"])
            if val == 0:
                continue
            
            key = self._normalize(d["item"])
            if key not in result:
                result[key] = {
                    "item": d["item"],
                    "quantity": 0,
                    "last": d["date"],
                    "value": val
                }
            result[key]["quantity"] += int(d.get("quantity", 1))
            if d["date"] > result[key]["last"]:
                result[key]["last"] = d["date"]
            result[key]["total"] = result[key]["quantity"] * val

        rows = list(result.values())
        
        ordem = self.combo_ordem.get()
        if ordem == "Nome do item":
            rows.sort(key=lambda x: x["item"])
        elif ordem == "Mais farmados":
            rows.sort(key=lambda x: x["quantity"], reverse=True)
        else:
            rows.sort(key=lambda x: x["total"], reverse=True)

        return rows

    def render(self):
        rows = self.aggregate_drops()
        total_val = sum(x["total"] for x in rows)
        total_qty = sum(x["quantity"] for x in rows)
        best = max(rows, key=lambda x: x["total"]) if rows else None

        self.lbl_val_total.config(text=f"{total_val:,.0f} Alz".replace(",", "."))
        self.lbl_total_drops.config(text=f"{total_qty:,}".replace(",", "."))
        self.lbl_unique_items.config(text=str(len(rows)))
        self.lbl_best_drop.config(text=f"{best['item']} ({best['total']:,.0f} Alz)" if best else "—")

        for item in self.tree.get_children():
            self.tree.delete(item)

        for x in rows:
            self.tree.insert("", tk.END, values=(
                x["item"],
                f"{x['quantity']:,}".replace(",", "."),
                f"{x['value']:,.0f} Alz".replace(",", "."),
                f"{x['total']:,.0f} Alz".replace(",", "."),
                x["last"]
            ))

    def import_file(self):
        path = filedialog.askopenfilename(filetypes=[("Arquivos válidos", "*.json;*.csv;*.txt")])
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.endswith(".json"):
                    data = json.load(f)
                else:
                    data = []
                    for line in f:
                        parts = line.strip().split(",")
                        if len(parts) >= 3:
                            data.append({"date": parts[0], "item": parts[1], "quantity": parts[2]})

                for d in data:
                    self.drops.append({
                        "date": d.get("date", str(datetime.date.today())),
                        "item": d.get("item", "Desconhecido"),
                        "quantity": int(d.get("quantity", 1))
                    })
            self._salvar_dados_persistence()
            self.render()
            messagebox.showinfo("Sucesso", "Drops importados e salvos com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler arquivo: {str(e)}")

    def open_catalog_dialog(self):
        """Abre a janela modal para gerenciamento do catálogo e salva diretamente no JSON."""
        modal = tk.Toplevel(self)
        modal.title("Catálogo de Itens - Base de Valores")
        modal.geometry("500x400")
        modal.transient(self)
        modal.grab_set()

        tree_frame = ttk.Frame(modal)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("name", "value")
        cat_tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        cat_tree.heading("name", text="Nome do Item")
        cat_tree.heading("value", text="Valor em Alz")
        cat_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=cat_tree.yview)
        cat_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def atualizar_lista():
            for item in cat_tree.get_children():
                cat_tree.delete(item)
            for idx, i in enumerate(self.catalog):
                cat_tree.insert("", tk.END, iid=str(idx), values=(i["name"], f"{i['value']:,.0f} Alz".replace(",", ".")))

        atualizar_lista()

        # Frame de adição
        add_frame = ttk.LabelFrame(modal, text="Adicionar / Editar Item")
        add_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(add_frame, text="Item:").grid(row=0, column=0, padx=5, pady=5)
        txt_nome = ttk.Entry(add_frame)
        txt_nome.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(add_frame, text="Valor (Alz):").grid(row=0, column=2, padx=5, pady=5)
        txt_val = ttk.Entry(add_frame)
        txt_val.grid(row=0, column=3, padx=5, pady=5)

        def salvar_item():
            nome = txt_nome.get().strip()
            try:
                val = float(txt_val.get().replace(".", "").replace(",", "."))
            except ValueError:
                messagebox.showerror("Erro", "Valor em Alz inválido.", parent=modal)
                return

            if not nome:
                messagebox.showerror("Erro", "Informe o nome do item.", parent=modal)
                return

            # Atualiza se já existir ou adiciona novo
            norm = self._normalize(nome)
            encontrado = False
            for item in self.catalog:
                if self._normalize(item["name"]) == norm:
                    item["value"] = val
                    encontrado = True
                    break
            if not encontrado:
                self.catalog.append({"name": nome, "value": val})

            self._salvar_dados_persistence()
            atualizar_lista()
            self.render()
            txt_nome.delete(0, tk.END)
            txt_val.delete(0, tk.END)

        def remover_item():
            sel = cat_tree.selection()
            if not sel:
                return
            idx = int(sel[0])
            del self.catalog[idx]
            self._salvar_dados_persistence()
            atualizar_lista()
            self.render()

        ttk.Button(add_frame, text="Salvar", command=salvar_item).grid(row=0, column=4, padx=5, pady=5)
        ttk.Button(modal, text="Remover Item Selecionado", command=remover_item).pack(pady=5)