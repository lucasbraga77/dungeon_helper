import os
import zipfile
import subprocess
import shutil

def atualizar():
    ZIP_PATH = "dungeon_helper.zip"
    CONFIG_NAME = "dungeon_helper_config.json"
    
    # 1. Descompacta
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        for file in zip_ref.namelist():
            # PULA se for o arquivo de configuração para não sobrescrever
            if file == CONFIG_NAME:
                continue
            zip_ref.extract(file)
            
    # 2. Limpa o zip
    os.remove(ZIP_PATH)
    
    # 3. Reabre o programa
    os.startfile("dungeon_helper.exe") 

if __name__ == "__main__":
    atualizar()