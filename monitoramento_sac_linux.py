#!/home/pi/virtualenvs/MonitoramentoSAC/env/bin/python3
# monitoramento_sac.py - Extrai dados da página do SAC com base em uma lista
# de ordens de serviço em uma planilha do Google Drive, atualizando em seguida
# a própria planilha com esses dados.

'''
A IMPLEMENTAR:
>> Corrigir captura de data de execução e agente quando há mais linhas na tabela do SACWEB
>> Lidar adequadamente com linhas em branco.
'''

import sys
import os
import socket
import requests
from bs4 import BeautifulSoup
import re
import json
import gspread
from oauth2client.client import SignedJwtAssertionCredentials
#from oauth2client.service_account import ServiceAccountCredentials
from operator import itemgetter
import datetime
import csv


def find_quarter(data, street, number):
    '''
    [0]: Logradouro
    [1]: Prefixo logradouro (rua, ave, etc)
    [2]: Número do imóvel
    [3]: Par ou Ímpar
    [4]: Bairro
    [5]: Quarteirão
    [6]: Código da AA
    [7]: Nome do CS
    '''
    not_found = ['', '???', '???', '???', '???', '???', '???', '???']
    
    if street == '':
        return not_found
    
    try:
        number_int = int(number)
    except:
        number_int = 0

    street = street.upper()
    number_str = str(number)
    max_rows = len(data)

    if (number_int % 2 == 0):
        type_number = 'P'
    else:
        type_number = 'I'

    for current_row in range(max_rows):
        if (street[0] == data[current_row][0][0] and street in data[current_row][0]):
            not_found[0] = data[current_row][0] #Logradouro
            not_found[1] = data[current_row][1] #Prefixo logradouro (rua, ave, etc)
            if type_number != data[current_row][3]:
                continue
            for subrow in range(current_row, max_rows):
                if number_str == data[subrow][2]: #Perfect match
                    return data[subrow]
                if (data[subrow][0] == data[subrow+1][0] and #Interpolação
                    number_int > int(data[subrow][2]) and
                    number_int < int(data[subrow+1][2]) and
                    subrow < max_rows and
                    type_number == data[subrow+1][3]):
                    not_found[2] = number_str #Número do imóvel
                    not_found[3] = type_number #Par ou Ímpar
                    for col in range(4,8):
                        if data[subrow][col] == data[subrow+1][col]:
                            not_found[col] = data[subrow][col]
                    return not_found
                if type_number != data[subrow][3]: #Termina se passar pra outra rua (de par pra ímpar)
                    return not_found
                if number_int < int(data[subrow][2]): #Termina se o número inicial for menor que o primeiro da lista
                    return not_found
                if subrow+1 >= max_rows: #Termina se chegar no fim do banco de dados
                    return not_found
    return not_found


def prazo_dez_dias(from_date_string):
    fmt = '%d/%m/%Y'
    business_days_to_add = 10
    current_date = datetime.datetime.strptime(from_date_string, fmt)
    while business_days_to_add > 0:
        current_date += datetime.timedelta(days=1)
        weekday = current_date.weekday()
        if weekday >= 5:
            continue
        business_days_to_add -= 1
    return datetime.datetime.strftime(current_date, fmt)


def resume_tipo(original):
    if 'ROEDORES' in original:
        return 'ROEDORES'
    elif 'PEÇONHENTOS' in original:
        return 'PEÇONHENTOS'
    elif 'DENGUE' in original:
        return 'DENGUE'
    elif 'VETORES' in original:
        return 'VETORES'
    else:
        return 'OUTROS'


def extrai_soup(item):
    if item is None:
        return 'Não encontrado'
    return item


def remove_prep(rua):
    preps = ('DO','DOS','DA','DAS','DE')
    wordList = rua.split()
    if wordList[0] in preps:
        result = ' '.join(wordList[1:])
    else:
        result = rua
    return(result) 


def buscar_no_sacweb(lista):
    csvFile = open('logradouros.csv', 'r', newline='\n', encoding="ISO8859-1")
    csvReader = csv.reader(csvFile, delimiter=',')
    csvData = list(csvReader)

    print('\nCOLETANDO DADOS DO SACWEB:')
    len_lista = len(lista)

    refaz_conexao = 0

    for index, item in enumerate(lista):
        codigo_sac = item[1]

        if refaz_conexao == 0:
            try:
                # Entra na página inicial do SAC
                s = requests.Session()
                s.get('http://www.pbh.gov.br/sac/')
            except:
                print('\nERRO: Não foi possivel acessar a página do SACWEB.')
                sys.exit()

            try:
                # Clica em 'Acompanhar serviço'
                s.get('http://portal6.pbh.gov.br/sacweb/work/Ctrl/CtrlSolicitacao?acao=6&visao=0')
            except:
                print('\nERRO: Não foi possível acessar a página de Acompanhamento de O.S.')
                sys.exit()

            # Seleciona no menu dropdown a pesquisa por 'Código da solicitação'
            pesquisa_por_codigo = {'acao': '6', 'tipoPesquisa': '1', 'visao': '0', 'tipoConsulta': '1'}
            s.post('http://portal6.pbh.gov.br/sacweb/work/Ctrl/CtrlSolicitacao?acao=6&visao=0', data = pesquisa_por_codigo)
            # Lança o número da O.S.
            numero_codigo = {'acao': '2', 'visao': '0', 'tipoConsulta': '1', 'parametro': codigo_sac}
            s.post('http://portal6.pbh.gov.br/sacweb/work/Ctrl/CtrlSolicitacao', data = numero_codigo)
        refaz_conexao += 1
        if refaz_conexao >= 5:
            refaz_conexao = 0

        # Entra na página da O.S.
        try:
            print('Pesquisando ordem %s (%s de %s)' % (codigo_sac, index+1, len_lista))
            url_sac = 'http://portal6.pbh.gov.br/sacweb/work/Ctrl/CtrlSolicitacao?acao=3&visao=0&codsolicita='
            response = s.get(url_sac + codigo_sac)
        except:
            print('ERRO: Falha ao pesquisar a ordem %s na página do SACWEB.' % (codigo_sac))

        # Cria a 'sopa' com os dados da página da O.S.
        soup = BeautifulSoup(response.text)

        # Extrai os dados que interessam
        #item[0] é o número da linha da planilha em que os dados da O.S. estão registrados
        #item[1] não precisa ser preenchido, pois é o código do SAC pelo qual os outros dados são localizados (codigo_sac)
        if item[2] == '':
            item[2] = extrai_soup(soup.find(text = 'Telefone:').find_next('td').string.strip()) #Regional
        strEndereco = " ".join(extrai_soup(soup.find(text = ' CEP:').find_next('p').string.split()))
        if strEndereco != 'Não encontrado':
            if item[6] == '':
                item[6] = remove_prep(re.search(r'([A-Z]+\b\s*[A-Z]*\s*[A-Z]*\s*[A-Z]*),\s*(\d+)', strEndereco).group(1)) #Logradouro
            if item[7] == '':
                item[7] = re.search(r'([A-Z]+\b\s*[A-Z]*\s*[A-Z]*\s*[A-Z]*),\s*(\d+)', strEndereco).group(2) #Número endereço
        else:
            item[6] = '' #Logradouro
            item[7] = '' #Número endereço
        localiza_edereco = find_quarter(csvData, item[6], item[7])
        if item[3] == '':
            item[3] = localiza_edereco[6] #Área de abrangência
        if item[4] == '':
            item[4] = localiza_edereco[4] #Bairro
        if item[5] == '':
            item[5] = localiza_edereco[5] #Quarteirão
        if item[8] == '':
            item[8] = resume_tipo(extrai_soup(soup.find(text = 'Serviço solicitado').find_next('p').string.strip())) #Tipo de serviço
        strPrazo = extrai_soup(soup.find(text = 'Data da Solicitação:').find_all_next('td')[1].string.strip())
        if re.search(r'\b\d?\d\/\d?\d\/\d+', strPrazo) != None:
            item[9] = re.search(r'\b\d?\d\/\d?\d\/\d+', strPrazo).group() #Data de solicitação
            item[10] = prazo_dez_dias(item[9]) #Prazo
        else:
            item[9] = ''
            item[10] = ''
        item[13] = extrai_soup(soup.find(text = 'Data da Solicitação:').find_next('p')).string.strip() #Status
        item[11] = ''
        item[12] = ''
        if 'Concluído' in item[13]:
            strDataCampo = extrai_soup(soup.find(text = 'Responsável pela Atividade:').parent.parent.parent).contents[-2].contents[-6].string.strip()
            if re.search(r'\b\d?\d\/\d?\d\/\d+', strDataCampo) != None:
                item[11] = extrai_soup(re.search(r'\b\d?\d\/\d?\d\/\d+', strDataCampo).group()) #Data de execução
            item[12] = extrai_soup(soup.find(text = 'Responsável pela Atividade:').parent.parent.parent).contents[-2].contents[-2].string.strip() #Agente
    return lista


def main():
    # os.system('cls')
    # Checa conexão com internet
    REMOTE_SERVER = "www.pbh.gov.br"
    print('Checando conexão com a internet... ', end='')
    sys.stdout.flush()
    try:
        host = socket.gethostbyname(REMOTE_SERVER)
        s = socket.create_connection((host, 80), 2)
        print('OK')
    except:
        print('\n\nERRO: Sem conexão com a internet.')
        sys.exit()

    # Abre planilha do Google Drive
    print('Autenticando acesso à planilha do Google Drive... ', end='')
    sys.stdout.flush()
    try:
        json_key = json.load(open(r'Monitoramento do SAC-e4a30cc8c7d7.json'))
        scope = ['https://spreadsheets.google.com/feeds']
        credentials = SignedJwtAssertionCredentials(json_key['client_email'], bytes(json_key['private_key'], 'utf-8'), scope)
        gc = gspread.authorize(credentials)
        wks = gc.open_by_key('1Z7Aa0jLfrwmNbTt0uzr1NDkDzdzBBBiY96euqyqAzAk')
        print('OK')
    except:
        print('\n\nERRO: Falha no acesso ao Google Drive.')
        sys.exit()

    # Coleta valores da planilha 'Em aberto'
    print('Checando os códigos das Ordens de Serviço a serem atualizadas... ', end='')
    sys.stdout.flush()
    try:
        planilha_de_ordens_em_aberto = wks.worksheet('Em aberto').get_all_values()
        print('OK')
    except:
        print('\n\nERRO: Falha no acesso ao Google Drive.')
        sys.exit()
    if len(planilha_de_ordens_em_aberto) <= 1:
        print('\n\nNada a atualizar.')
        sys.exit()

    # Cria listas com linhas a serem atualizadas ou transferidas para outra planilha
    ordens_concluidas = []
    ordens_a_atualizar = []
    for row, value in enumerate(planilha_de_ordens_em_aberto[1:], start = 2):
        value.insert(0, row)
        if 'Concluído' in value[13]:
            # Bota na lista de mandar pra planilha 'Concluidas'
            ordens_concluidas.append(value)
        else:
            # Bota na lista de atualizar
            ordens_a_atualizar.append(value)

    # Atualiza a lista 'ordens_a_atualizar'
    lista_atualizada_de_ordens = buscar_no_sacweb(ordens_a_atualizar)

    # Checa quais ordens constam como concluídas após atualização
    for item in lista_atualizada_de_ordens:
        if 'Concluído' in item[13]:
            ordens_concluidas.append(item)

    # Salva ordens concluídas na planilha 'Concluidas'
    ordens_concluidas_sorted = sorted(ordens_concluidas, key=itemgetter(1))
    last_row_concluidas = wks.worksheet('Concluidas').row_count
    wks.worksheet('Concluidas').add_rows(len(ordens_concluidas_sorted))
    cont = 1
    cell_list = []
    print('\nARQUIVANDO ORDENS CONCLUÍDAS:')
    for item in ordens_concluidas_sorted:
        print('Arquivando ordem %s (%s de %s)' % (item[1], cont, len(ordens_concluidas_sorted)))
        rowcount = last_row_concluidas + cont
        cont += 1
        cell_line = wks.worksheet('Concluidas').range("A%s:M%s" % (rowcount,rowcount))
        for colcount, cell in enumerate(cell_line, start = 1):
            cell.value = item[colcount]
        cell_list.extend(cell_line)
    if len(cell_list) > 0:
        print('Salvando alterações... ', end='')
        sys.stdout.flush()
        try:
            wks.worksheet('Concluidas').update_cells(cell_list)
            print('OK')
        except:
            print('\n\nERRO: Falha no acesso ao Google Drive.')
            sys.exit()

    # Grava as atualizações na planilha 'Em aberto'
    lista_apagada = []
    empty_rows = 0
    for item in lista_atualizada_de_ordens:
        if 'Concluído' in item[13]:
            empty_rows += 1
        else:
            lista_apagada.append(item[1:])
    lista_atualizada_sorted = sorted(lista_apagada, key=itemgetter(1))
    cont = 1
    cell_list = []
    print('\nATUALIZANDO ORDENS EM ABERTO:')
    for item in lista_atualizada_sorted:
        cell_line = wks.worksheet('Em aberto').range("A%s:M%s" % (cont+1,cont+1))
        print('Atualizando ordem %s (%s de %s)' % (item[0], cont, len(lista_atualizada_sorted)))
        for colcount, cell in enumerate(cell_line):
            cell.value = item[colcount]
        cell_list.extend(cell_line)
        cont += 1
    print('Limpando planilha de ordens em aberto... ', end='')
    sys.stdout.flush()
    for row_to_erase in range(empty_rows):
        cell_line = wks.worksheet('Em aberto').range("A%s:M%s" % (row_to_erase+cont+1,row_to_erase+cont+1))
        for colcount, cell in enumerate(cell_line):
            cell.value = ''
        cell_list.extend(cell_line)
    print('OK')
    if len(cell_list) > 0:
        print('Salvando alterações... ', end='')
        sys.stdout.flush()
        try:
            wks.worksheet('Em aberto').update_cells(cell_list)
            print('OK')
        except:
            print('\n\nERRO: Falha no acesso ao Google Drive.')
            sys.exit()
    
    wks.worksheet('LOG').append_row(['Última atualização: '+str(datetime.datetime.now())])
    #input("\nConcluído. Tecle ENTER para fechar.")


if __name__ == '__main__':
    sys.exit(main())
