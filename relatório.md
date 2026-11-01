# Googol - relatório (Meta 1) 

SD 2026/27 · Licenciatura em Eng. Informática · DEI-FCTUC

Grupo: Rodrigo Garcia (nº 2023230748) - Gabriel Matos (nº 2024203546)

## 1. Objetivo

O objetivo é desenvolver um sistema de URLs com indexação, pesquisa, backlinks, e estatísticas atualizadas em tempo real, apoiado por RCP/RMI, redundância, reliable multicast, consistência e processamento em paralelo.

## 2. Arquitetura
### 2.1 Componentes

- **Storage Barrels**: guardam o índice (invertido), as páginas e os backlinks (apenas os barrels podem guardar dados em disco). Sâo réplicas da queue, completas e sincronizadas entre si. Usam SQLite (para a BD da queue), lock e três tabelas em memória carregadas no arranque (index, pages e backlinks).
- **Cliente**: interface de utilizador. Permite pesquisar URLs, indexar, ver backlinks e obter estatísticas em tempo real. Apenas comunica com o gateway. É possível ter mais que um cliente
- **Downloader**: vai buscar URLs ao gateway, descarrega e analisa a página, envia-a para todos os Barrels e devolve ao Gateway os links encontrados. Podem existir vários em simultâneo e cada um gera um ID quando é criado (ou seja, não há dois downloaders iguais)
- **Gateway**: cérebro de toda a aplicação. Todos os outros componentes comunicam com a gateway, sendo esta a única forma de entrada no sistema. Encaminha pesquisas para um barrel, mantém a fila de URLs a indexar e calcula as estatísticas

### 2.2 Dados e persistência

Sempre que há uma escrita, é feito um commit antes de haver uma resposta (garante que está armazenado antes de ser dada uma resposta). Ao arrancar, cada barrel recarrega a base para a memória, permitindo que as pesquisas nunca sejam feitas pela base (entrega mais rapidez) e que os dados sobrevivam a restarts. A base do Gateway usa o modo WAL, que permite consultar a fila com o Gateway a correr.

### 2.3 Base de dados

| Nome | Tabela | Conteúdo |
|---|---|---|
| `barrelN.db` | `pages` | URL, título, citação (primeiros 150 caracteres do texto) |
| `barrelN.db` | `words` | pares (palavra, URL); chave composta |
| `barrelN.db` | `backlinks` | pares (link, URL que o contém); chave composta |
| `gateway.db` | `tasks` | URL (chave), status (`pending`/`processing`/`done`), hora em que o downloader levou o URL, ID do downloader, nº vezes que o URL foi entregue |

### 2.4 Pesquisa e stop words

Na pesquisa, as palavras usadas são convertidas em minúsculas para ficarem normalizadas da mesma forma que as palavras das páginas. Ao pesquisar, o resultado mostra as pesquisas que contenham todas as palavras inseridas. Cada página da pesquisa tem 10 resultados (existe um comando de teclado para avançar nas páginas ou então sair da pesquisa). Os resultados da pesquisa são ordenados por nº de backlinks, do maior para o menor.

As stop words, regidas por uma biblioteca python, são ignoradas na indexação e na pesquisa (p.e. uma pesquisa só com stop words não devolve resultados). São usadas as stop words das línguas PT e EN.

## 3. Replicação e reliable multicast

O multicast fiável é feito no downloader através de ACK com retransmissão.

O downloader repete até haver ACK (uma chamada com Exception dá "sem ACK"). Ao receber a mesma página várias vezes não duplica a informação. A ordem da informação também não importa, já que a união é comutativa e associativa (os dois barrels são réplicas iguais). Enquanto houver um barrel ativo, o sistema continua a indexar URLs (quando os outros barrels voltam, recuperam por retransmissão).

Para um barrel que esteve em baixo não perder páginas (as páginas que perdeu podem já não estar nos pendentes), carrega a sua própria base, chama get_estado para devolver as tabelas, junta-as às suas usando INSERT OR IGNORE (faz a união de toda a informação, sem deixar repetições) e só depois é que se regista no nameserver (só se regista depois para evitar deadlock com outros barrels).

## 4. RPC e failover
### 4.1 Pyro5

Tanto o gateway como os barrels registam-se no nameserver.

É criado um proxy por chamada, para evitar que se fique preso a uma ligação morta. Assim, quando um serviço volta a registar-se, substitui a entrada antiga.

O servidor atende cada ligação numa thread, o que garante que todas as estruturas estejam protegidas por locks.

Para evitar que algum serviço mais lento bloqueie outros, usam-se timeouts: 2 segundos nas chamadas de monitorização e callbacks e 5 segundos nas chamadas do cliente ao gateway.

### 4.2 Distribuição de URLs

A fila de URLs está no Gateway, na tabela `tasks`, e funciona como uma fila de trabalho com lease.

O get_url escolhe um URL marcado como pending (por menor número de attempts e depois por ordem de inserção) e marca-o como processing, guardando a hora e o ID do downloader (em claimed_at e worker_id). Antes de escolher, o get_url devolve a pending todos os URLs que estejam como processing há mais de 30 segundos.

O ack_url só tem efeito se o worker_id coincidir, por isso um downloader lento (cujo lease já expirou e cujo URL foi entregue a outro) não consegue marcar como concluído o trabalho do outro. Como a fila está em gateway.db, sobrevive a um reinício da gateway (os dados ficam sempre guardados). Uma página que falha sistematicamente (p.e. que dê erro 403 ou 404) volta à fila de cada vez que o lease expira. O ordenamento por attempts garante que as páginas novas passam à frente das que falham.

### 4.3 Callbacks de estatísticas

As estatísticas são entregues por callback ao cliente. Quando o utilizador abre a opção "Estatísticas" no menu, o cliente cria um servidor Pyro5 local, numa thread, com o objeto StatsCallback e envia o seu URI à gateway através de registar_callback. O cliente passa assim a ser servidor para esta interação

A Gateway guarda a lista de URIs registados. Uma thread monitor acorda no máximo de 2 em 2 segundos (ou assim que há uma pesquisa) e monta as estatísticas:
   - **Top 10 pesquisas**: por contagem, em minúsculas, apenas a página 0 de cada pesquisa;
   - **Barrels ativos**: os que respondem a get_stats() em 2 segundos, com o número de páginas e de palavras do índice;
   - **Tempo médio de resposta por barrel**: em décimas de segundo, medido à volta da chamada search ao barrel e apresentado na mesma linha dos barrels.

A gateway chama update_stats(stats) em cada URI só se as estatísticas mudaram desde o último envio. Se o callback falhar, é removido. O cliente põe o que recebe numa fila e o ecrã atualiza-se. Se o Gateway morrer, volta a registar o callback quando regressar. Se o cliente fizer CTRL+C, o servidor local fecha e o ecrã volta a mostrar o menu.

## 5. Métodos por componente

| Componente | Método | Descrição |
|---|---|---|
| Barrel | `__init__(db_path)` | Abre a base SQLite, cria as tabelas se não existirem, cria o lock e carrega os dados para memória |
| Barrel | `load_data()` | Lê as tabelas da base e reconstrói os dicionários em memória pages, index e backlinks |
| Barrel | `add_page(url, title, snippet, words, links)` | Guarda uma página no índice; devolve True depois do commit (é o ACK do multicast) |
| Barrel | `search(terms, page=0)` | Devolve as páginas que contêm todos os termos, ordenadas por número de backlinks, 10 por página |
| Barrel | `get_backlinks(url)` | Devolve a lista de páginas que apontam para url |
| Barrel | `get_estado()` | Devolve o conteúdo das tabelas pages, words e backlinks para outro Barrel se ressincronizar |
| Barrel | `sincronizar(outros)` | Pede o estado a cada um dos outros barrels, junta-o ao seu e recarrega a memória |
| Barrel | `get_stats()` | Devolve o número de páginas e de palavras do índice |
| Barrel | `main(name)` | Cria o barrel, sincroniza-o com os outros, abre o servidor Pyro, regista-o no name server e fica à espera de pedidos |
| Gateway | `__init__()` | Inicializa os contadores de estatísticas, os locks e o evento; abre gateway.db e cria a tabela tasks, apagando entradas vazias. |
| Gateway | `chamar_barrel(metodo, *args)` | Chama um método num barrel escolhido aleatoriamente; se falhar, tenta o seguinte; mede o tempo das pesquisas; se todos falharem, lança "Nenhum SB disponível" |
| Gateway | `registar_tempo(nome, decimas)` | Acumula o tempo de resposta de um barrel (em décimas de segundo) |
| Gateway | `search(terms, page=0)` | Conta a pesquisa, pede o resultado a um barrel e avisa o monitor de estatísticas |
| Gateway | `get_backlinks(url)` | Pede a um barrel vivo a lista de páginas que apontam para url |
| Gateway | `add_url(url)` | Insere o URL na fila como pending; ignora URLs que já existem; devolve `True` |
| Gateway | `get_url(worker_id)` | Devolve o próximo URL pending (menos tentado primeiro), marcando-o como processing com a hora e o downloader; antes, devolve a pending os que expiraram |
| Gateway | `ack_url(url, worker_id)` | Marca o URL como done, apenas se estava como processing para esse downloader |
| Gateway | `estado_barrels()` | Pergunta o tamanho do índice a cada barrel (timeout de 2 s) |
| Gateway | `montar_stats()` | Constrói as estatísticas |
| Gateway | `atualizar_stats()` | Se as estatísticas mudaram desde a última vez, envia-as a todos os clientes registados e remove os que falham |
| Gateway | `monitor()` | Ciclo numa thread: de 2 em 2 segundos (ou assim que há uma pesquisa) chama atualizar_stats |
| Gateway | `registar_callback(callback_uri)` | Guarda o URI do callback do cliente e envia-lhe logo as estatísticas atuais |
| Gateway | `ping()` | Permite ao cliente verificar se a gateway está viva |
| Gateway | `main()` | Cria a gateway, lança a thread do monitor, abre o servidor Pyro e regista-o no name server com o nome gateway |
| Downloader | `processar_pagina(url)` | Descarrega a página (timeout de 10 s), extrai título, palavras, citação (150 caracteres) e links absolutos; devolve None se falhar |
| Downloader | `enviar(nome, url, titulo, citacao, palavras, links)` | Envia a página a um Barrel e devolve o ACK; devolve False em caso de erro |
| Downloader | `enviar_aos_barrels(...)` | Envia a página a todos os barrels; os que não confirmam ficam em pendentes; devolve True se pelo menos um confirmou |
| Downloader | `reenviar_pendentes()` | Tenta reenviar as páginas pendentes e remove as que foram confirmadas |
| Downloader | `tratar_url(gateway, url)` | Processa a página, envia-a aos barrels e entrega os links encontrados à gateway |
| Downloader | `um_ciclo()` | Pede um URL à gateway; se há, trata-o e confirma-o; se não há, espera 1 s |
| Downloader | `main()` | Repete para sempre: reenvia pendentes e executa um ciclo; em caso de erro, imprime-o e espera 2 s |
| Cliente | `pesquisar()` | Lê os termos, mostra os resultados (título, URL, citação, backlinks) e permite passar às páginas seguintes |
| Cliente | `backlinks()` | Pede um URL e mostra as páginas que apontam para ele |
| Cliente | `indexar_url()` | Valida que o URL começa por http:// ou https:// e envia-o à gateway para a fila |
| Cliente | `StatsCallback` | A gateway chama update_stats que põe as estatísticas numa queue.Queue |
| Cliente | `mostrar(stats)` | Limpa o ecrã e apresenta o top 10 de pesquisas e os Barrels ativos (páginas, palavras e tempo médio) |
| Cliente | `estatisticas()` | Abre o servidor de callback, regista-o na gateway, mostra as estatísticas recebidas e volta a ligar-se se a gateway cair |
| Cliente | `chamar_gateway(metodo, *args)` | Chama um método da gateway; se este estiver indisponível, repete de 3 em 3 s até conseguir |
| Cliente | menu principal | Ciclo com as opções 1 a 5 (Pesquisar, Backlinks, Indexar URL, Estatísticas, Sair) |

## 6. Distribuição de tarefas

| Elemento | Tarefas |
|---|---|
| **Rodrigo** | Barrel (estrutura/funcionamento base) · Gateway (estrutura/funcionamento base; queue) · Downloader (estrutura/funcionamento base; correções) · Client (estrutura/funcionamento base; estatísticas) · Relatório+README+requirements |
| **Gabriel** | Barrel (persistência; replicação) · Gateway (queue) · Downloader (failover) · Client (estrutura/funcionamento base; estatísticas) |

## 7. Testes

| DESCRIÇÃO | OUTPUT ESPERADO | PASS/FAIL |
|---|---|---|
| Indexar um URL | Print "URL enviado" e o downloader vai buscar | `<PASS>` | 
| Pesquisar uma palavra do URL indexado | Print com título, URL e citação | `<PASS>` | 
| Pesquisa com 2 palavras | Só páginas que têm as duas | `<PASS>` | 
| Pesquisa sem resultados | Print “Sem resultados” (sem erro) | `<PASS>` | 
| Paginação no cliente | Todas as páginas funcionam | `<PASS>` | 
| Backlinks  | Lista das páginas que a referenciam | `<PASS>` | 
| Crawl recursivo | Os links da página indexada passam à fila e são indexados | `<PASS>` | 
| Mesmo URL indexado 2 vezes | Só uma entrada | `<PASS>` | 
| Indexar com os dois barrels vivos | Ambos iguais | `<PASS>` | 
| Matar o barrel2 - indexar - arrancar o barrel2 | Ressincroniza e fica igual ao barrel1 | `<PASS>` | 
| Matar o barrel1 e pesquisar | O gateway usa o barrel2 (sem erro) | `<PASS>` | 
| Matar os dois barrels e pesquisar | Print “Nenhum SB disponível” (sem erro) | `<PASS>` | 
| Arrancar os dois barrels ao mesmo tempo | Não bloqueiam e ficam prontos | `<PASS>` | 
| Matar um barrel durante o crawl | O downloader continua e ao voltar o barrel sincroniza | `<PASS>` | 
| Reiniciar o gateway com URLs ainda na fila | A fila mantém-se e o downloader retoma | `<PASS>` | 
| Reiniciar o gateway durante o crawl | Downloader e cliente voltam a ligar-se sozinhos | `<PASS>` | 
| Reiniciar um barrel | Os dados mantêm-se  | `<PASS>` | 
| Cliente a pesquisar enquanto o gateway está em baixo | Tenta de 3 em 3 s  | `<PASS>` | 
| Dois downloaders ao mesmo tempo | Cada URL é processado uma vez, sem duplicados | `<PASS>` | 
| Pesquisas python, Python, redes | Top 10 agrupa por minúsculas (python 2x) | `<PASS>` | 
| Avançar nas páginas de uma pesquisa | Não conta como nova pesquisa | `<PASS>` | 
| Barrels ativos com páginas e palavras | Valores corretos | `<PASS>` | 
| Tempo médio por barrel | Aparece nas estatísticas (depois de haver pesquisas) | `<PASS>` | 
| Ecrã aberto sem fazer nada | Não atualiza (só empurra quando muda) | `<PASS>` | 
| CTRL+C no ecrã de stats | Volta ao menu (sem erro) | `<PASS>` | 
| Opção inválida no menu | Ignora | `<PASS>` | 
| URL inválido/vazio em “Indexar URL” | Print "URL inválido ou vazio." (sem erro) | `<PASS>` | 
| Pesquisa só com stop words | Print “Sem resultados” (sem erro) | `<PASS>` | 
| Site que dá erro 403/404 (privado ou inexistente) | O downloader não crasha | `<PASS>` | 

## 8. Limitações

- Os URLs não estão normalizados (p.e. http://x/ e http://x contam como páginas diferentes);
- Os nomes dos barrels são fixos, pelo que para acrescentar barrels é preciso editar o código;
- Um barrel que fique "congelado" (ligado mas sem responder) atrasaria o Downloader.

## 9. Objetivos futuros

Na próxima meta iremos corrigir possíveis erros inesperados descobertos na defesa da meta atual, além de implementar uma interface WEB (principal objetivo da próxima meta).