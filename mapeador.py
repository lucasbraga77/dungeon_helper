import threading
from pynput import mouse, keyboard

import capturardg

# Tabela de correspondência das 17 linhas para réplica automática nas abas Intermediária e Avançada
LINHAS_DGS = {
    1: ["Estação Ruína", "Templo Esquecido 2SS", "Cidade Abandonada"],
    2: ["Cidadela Vulcânica", "Altar de Siena 2SS", "Templo Esquecido 3SS"],
    3: ["Templo Esquecido 1SS", "Posto Avançado de Máquinas", "Ilha da Miragem"],
    4: ["Ilha Proibida", "Torre dos Mortos 3SS", "Solo Flamejante"],
    5: ["Altar de Siena 1SS", "Templo Esquecido 2SS (Desperto)", "Tumba Ancestral"],
    6: ["Castelo das Ilusões", "Vale Tempestuoso (Desperto)", "Desfiladeiro Congelado"],
    7: ["Caverna do Pânico(Premium)", "Torre dos Mortos 3SS (Parte 2)", "Terminus Machina"],
    8: ["Locomotiva Louca(Premium)", "Castelo das Ilusões (Apócrifos)", "Celestia"],
    9: ["Catacumba Gélida(Premium)", "Salão Radiante do Castelo (Apócrifos)"],
    10: ["Morada das Chamas Infernais(Premium)", "Crista Ilusória"],
    11: ["Morada das Chamas Infernais(Desperto)", "Arena Acheron"],
    12: ["Caverna do Pânico(Desperto)", "Torre Diabólica"],
    13: ["Locomotiva Fantasma(Desperto)", "Torre Diabólica (Parte 2)"],
    14: ["Catacumba Gélida(Desperto)", "Keldrasil Sagrado"],
    15: ["Pandemônio", "Salão Radiante do Castelo"],
    16: ["Moinho Sagrado"],
    17: ["Torre Gélida dos Mortos 1SS"]
}


class Mapeador:
    def __init__(self, status_callback=None, tipo_callback=None, finished_callback=None):
        self.status_callback = status_callback or (lambda texto: None)
        self.tipo_callback = tipo_callback or (lambda tipo: None)
        self.finished_callback = finished_callback or (lambda resultados: None)
        self.resultados = {}
        self.fila = list(capturardg.ROTEIRO)
        self.item_atual = None
        self.start_pos = None
        self.tentativa_atual = None
        self.tipo_override = None
        self.mouse_listener = None
        self.keyboard_listener = None
        self.thread = None

    def iniciar(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self._finalizar()

    def _run(self):
        self._atualizar_status("Mapeamento iniciado. Veja as instruções no aplicativo e use o botão do meio para confirmar.")
        self.avancar_item()
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press)
        self.mouse_listener.start()
        self.keyboard_listener.start()
        self.keyboard_listener.join()
        self.mouse_listener.stop()
        self._finalizar()

    def _atualizar_status(self, texto):
        self.status_callback(texto)

    def _finalizar(self):
        # Dicionário tratado que vai para o callback final / salvamento JSON
        resultados_tratados = {}

        # 1. Copia primeiro os botões/regiões normais de sistema (LOGIN, CANAL, BOTOES DE ABA, etc.)
        for chave, valor in self.resultados.items():
            if not chave.startswith("DG Iniciante L"):
                resultados_tratados[chave] = valor

        # 2. Replica as coordenadas da Linha X para todas as DGs dessa mesma linha
        for num_linha, nomes_dgs in LINHAS_DGS.items():
            coord_linha = None
            
            # Busca a coordenada capturada para 'DG Iniciante LX: ...'
            for chave, valor in self.resultados.items():
                if chave.startswith(f"DG Iniciante L{num_linha}:"):
                    coord_linha = valor
                    break

            # Se encontrou a coordenada, atribui para todos os nomes limpos de DGs daquela linha
            if coord_linha:
                for nome_dg in nomes_dgs:
                    resultados_tratados[nome_dg] = coord_linha

        # Envia o dicionário limpo e totalmente espelhado
        self.finished_callback(resultados_tratados)

    def mostrar_proximo(self):
        if self.item_atual is None:
            self._atualizar_status("✅ Mapeamento concluído. Feche a janela ou clique em Salvar.")
            self.tipo_callback(None)
            return

        tipo = self.tipo_override or self.item_atual["tipo"]
        instrucao = "CLIQUE" if tipo == "PONTO" else "ARRASTE E SOLTE"
        mensagem = (
            f"[{len(self.resultados) + 1}/{len(capturardg.ROTEIRO)}] {self.item_atual['nome']}\n"
            f"Tipo selecionado: {tipo}. Use BOTÃO DIREITO para {instrucao.lower()}. \n"
            "Confirme com o BOTÃO DO MEIO. F2 pula, ESC encerra."
        )
        self._atualizar_status(mensagem)
        self.tipo_callback(tipo)

    def on_click(self, x, y, button, pressed):
        if self.item_atual is None:
            return

        if button == mouse.Button.right:
            if pressed:
                self.start_pos = (x, y)
                return

            if self.start_pos is None:
                return

            tipo = self.tipo_override or self.item_atual["tipo"]
            if tipo == "REGIAO":
                x1, y1 = self.start_pos
                x2, y2 = x, y
                valor = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            else:
                valor = (x, y)

            self.tentativa_atual = valor
            self._atualizar_status(
                f"Capturado {self.item_atual['nome']}: {valor} \n" \
                "Confirme com o botão do meio ou pule com F2."
            )
            self.start_pos = None

        elif button == mouse.Button.middle and not pressed:
            if self.tentativa_atual is None:
                self._atualizar_status("Nenhuma captura disponível. Use o botão direito primeiro.")
                return
            self.resultados[self.item_atual["nome"]] = self.tentativa_atual
            self._atualizar_status(f"Confirmado {self.item_atual['nome']}: {self.tentativa_atual}")
            self.tentativa_atual = None
            self.avancar_item()

    def on_press(self, key):
        try:
            if key == keyboard.Key.f2 and self.item_atual is not None:
                self._atualizar_status(f"Pulando {self.item_atual['nome']} e seguindo para o próximo.")
                self.tentativa_atual = None
                self.avancar_item()
            elif key == keyboard.Key.esc:
                self._atualizar_status("Mapeamento interrompido pelo usuário.")
                return False
        except Exception:
            pass

    def set_tipo_override(self, tipo):
        self.tipo_override = tipo
        if self.item_atual is not None:
            self.mostrar_proximo()

    def avancar_item(self):
        if self.fila:
            self.item_atual = self.fila.pop(0)
        else:
            self.item_atual = None
        self.mostrar_proximo()