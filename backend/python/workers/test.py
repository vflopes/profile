text = 'Avalia\\u00e7\\u00f5es de clientes'
fixed_text = text.encode('utf-8').decode('unicode-escape')
print(fixed_text)  # Saída: Avaliações de clientes