# -*- coding: utf-8 -*-

# A very simple setup script to create a single executable
#
# hello.py is a very simple 'Hello, world' type script which also displays the
# environment in which the script runs
#
# Run the build process by running the command 'python setup.py build'
#
# If everything works well you should find a subdirectory in the build
# subdirectory that contains the files needed to run the script without Python
#
# ************************ IMPORTANTE *****************************
# Se não incluir os arquivos cacert.pem e cacerts.txt dá pau.
# Ver instruções abaixo:
# http://stackoverflow.com/questions/33036459/cannot-make-work-exe-from-python-with-gspread

from cx_Freeze import setup, Executable

packs =['bs4', 'cffi', 'cryptography', 'gspread', 'httplib2', 'oauth2client', 'requests']
includefiles = ['Monitoramento do SAC-e4a30cc8c7d7.json', 'logradouros.csv']

executables = [
    Executable('monitoramento_sac.py')
]

setup(name='MonitoramentoSAC',
      version='0.1',
      author = "João Pedro C. Fonseca",
      description='Atualiza a planilha de Monitoramento do SAC no Google Drive.',
      executables=executables,
      options = {"build_exe": {"packages":packs, "include_files": includefiles}}
      )