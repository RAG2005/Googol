# Googol - motor de pesquisa de páginas WEB (Meta 1) 


## Introdução 

O Googol é um sistema distribuído de indexação e pesquisa de URL's desenvolvido em Python, usando Pyro5 na comunicação entre componentes.

## Autores

- Rodrigo Amaral Garcia, estudante nº 2023230748
- Gabriel Marques Matos, estudante nº 2024203546

## Estrutura

```text
Googol/
│
├─ barrel/
├─ client/
├─ downloader/
├─ gateway/
├─ arquitetura.png
├─ program.bat
├─ requirements.txt
├─ README.md
└─ relatorio.md
```

## Requisitos

- Python (de preferência uma versão recente)
- Dependências em requirements.txt

## Instalação

```bash
pip install -r requirements.txt
```

## Execução 

Para inciar todos os componentes em simultâneo:
```bash
program.bat
```
O ficheiro .bat abre 6 tabs:
- Pyro5
- Gateway
- Barrel 1
- Barrel 2
- Downloader
- Client

Para abrir componentes adicionais (p.e. mais downloaders) ou abrir manualmente cada um, é necessário estar no path da pasta (estando na pasta do projeto, executar "cd nome_componente") desse componente e depois executar "python nome_componente.py"

## Funcionalidades

- Pesquisa por palavras chave
- Indexação automática de URL's
- Comunicação distribuída através de Pyro5
- Armazenamento distribuído dos índices
- Execução concorrente de múltiplos componentes

## Limitações

- O número de barrels é configurado manualmente
- O sistema foi desenvolvido e testado em ambiente Windows, pelo que nao é garantido que funcione em outros ambientes
- Todos os comandos bash descritos acima funcionama em ambiente Windows
