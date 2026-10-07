"""Número de versão do Monitor — escrito num só sítio.

É aqui que se muda a versão sempre que o código muda. O resto vê este valor:
  - a documentação da API (FastAPI) usa-o;
  - o endereço /api/versao devolve-o;
  - os rodapés do site e a barra lateral da aplicação mostram-no (static/versao.js);
  - o executável de secretária (.exe) vai buscá-lo ao site e escreve-o no título
    da janela, por isso o .exe nunca fica com um número diferente do online.
"""
VERSAO = "2.0.1"
