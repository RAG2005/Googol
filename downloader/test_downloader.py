from downloader import processar_pagina

resultado = processar_pagina("https://excel.cloud.microsoft/")
if resultado:
    titulo, citacao, palavras, links = resultado
    print(titulo)
    print(len(palavras))
    print(len(links))
    print(links[:5])
else:
    print("erro")