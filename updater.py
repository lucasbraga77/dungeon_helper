import urllib.request
import config

# A URL deve ser o link "Raw" do seu Gist (aquela que começa com gist.githubusercontent.com)
URL_VERSAO = "COLOQUE_AKI_A_URL_RAW_DO_SEU_GIST"

def verificar_updates():
    """
    Verifica se a versão remota é diferente da versão local.
    Retorna (True, versao_nova) se existir update, ou (False, None) se não existir ou houver erro.
    """
    try:
        # Aumentamos o timeout para garantir que ele não trave o app em conexões ruins
        req = urllib.request.Request(URL_VERSAO, headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=5) as response:
            versao_remota = response.read().decode('utf-8').strip()
        
        # Compara a versão remota com a que definiremos no config.py
        if versao_remota != config.VERSAO_ATUAL:
            return True, versao_remota
        return False, None
    except Exception as e:
        # Em caso de erro (ex: sem internet), apenas ignoramos para não derrubar o app
        return False, None