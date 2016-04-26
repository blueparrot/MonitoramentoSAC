#! python3
# logradouros.py - Localiza endereço no arquivo 'logradouros.csv' endereço e
# informa o quarteirão, bairro e área de abrangência correspondente.
'''
Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
Back: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
Style: DIM, NORMAL, BRIGHT, RESET_ALL
'''
import os
import csv
import string
from colorama import init, Fore, Back, Style
init()

csvFile = open('logradouros.csv', 'r', newline='\n')
csvReader = csv.reader(csvFile, delimiter=',')
csvData = list(csvReader)

#logradouro = input('Nome do logradouro: ').lower()
#numero_imovel = input('Número do imóvel: ').lower()

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

os.system('cls')
print(Fore.BLACK + Back.YELLOW + '\n        PESQUISA DE ENDEREÇOS        \n\n')
sair = ''

while sair != 'S':
	print(Fore.YELLOW + Back.BLACK + Style.NORMAL + chr(27) + '[1A   Nome do logradouro: ', end='')
	logradouro = input(Style.BRIGHT + '').upper()
	print(Style.NORMAL + '   Número do imóvel: ', end='')
	numero = input(Style.BRIGHT + '').upper()
	resposta = find_quarter(csvData, logradouro, numero)
	print(Fore.CYAN + Style.NORMAL + '   Logradouro encontrado: ', end='')
	print(Style.BRIGHT + '%s %s' % (resposta[1], resposta[0]))
	print(Style.NORMAL + '   Quarteirão: ', end='')
	print(Style.BRIGHT + '%s' % (resposta[5]))
	print(Style.NORMAL + '   Bairro: ', end='')
	print(Style.BRIGHT + '%s' % (resposta[4]))
	print(Style.NORMAL + '   Área de abrangência: ', end='')
	print(Style.BRIGHT + '%s \n' % (resposta[6]))
	print(Fore.YELLOW + Style.BRIGHT + '   Sair? (S) ', end='')
	sair = input('').upper()
	print(chr(27)+'[1A                                                          ')