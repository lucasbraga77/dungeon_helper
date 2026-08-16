"""
Versão atual do Dungeon Helper.

Este arquivo é a fonte única de verdade da versão do app.
- O updater.py lê APP_VERSION para comparar com o GitHub Release.
- O build.py pode ler/escrever aqui para bumpar a versão antes de compilar.
- A UI pode importar APP_VERSION para exibir na janela/título.

Formato: MAJOR.MINOR.PATCH  (Semantic Versioning)
"""

APP_VERSION = "1.0.0"
