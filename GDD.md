# Bem-te-vi — Ciclo de Vida
*Documento de design do jogo (GDD) · v0.1 · outubro/2026*

## 1. Conceito

Você é um bem-te-vi (*Pitangus sulphuratus*) vivendo uma **estação reprodutiva completa**: conquistar
um parceiro, construir o ninho, chocar os ovos, alimentar e defender os filhotes até o primeiro voo.
No fim, um dos filhotes vira o protagonista da próxima estação — o ciclo recomeça.

- **Plataforma:** Android (retrato, toque com um dedo), sessões curtas de 2–4 min por etapa.
- **Visual:** 3D low-poly. Todo o jogo acontece numa **praça de cidade brasileira**, cercada por casas e prédios.
- **Público:** casual / família, com camada educativa leve (fatos reais desbloqueáveis).
- **Tom:** colorido e corajoso — o bem-te-vi é pequeno, mas enfrenta gavião.

### O cenário: a praça
| Elemento | Papel no jogo |
|---|---|
| Árvore do ninho (com forquilha e galho do dueto) | Etapas 2 e 3 acontecem nela; também pode ser o ponto do dueto |
| Chafariz com peixinhos | Fonte de peixe (comida valiosa); no futuro, banho para recuperar energia |
| Pitangueira | Frutas fáceis de pegar |
| Canteiros de grama | Gravetos, capim, musgo e insetos |
| Lixeiras e banca de jornal | Plástico e barbante (lixo urbano) |
| Postes de luz | Poleiro do parceiro |
| Fiação da rua, encosto dos bancos, teto da banca, teto de carro, borda do chafariz | Onde as bem-te-vis esperam na etapa 1 (sorteado a cada partida) |
| Coreto, ipês amarelo e rosa, orelhões, ponto de ônibus | Ambientação e pontos de pouso |
| Telhados e prédios ao redor | De onde chegam o tucano e o bem-te-vi-pirata |

### Controles
- **Tocar** num ponto da praça: o bem-te-vi voa até lá (pousa se for chão, galho ou telhado).
- **Tocar** num material, inseto, peixe, fruta ou predador: o pássaro persegue o alvo.
- **Arrastar**: gira a câmera em volta do pássaro.
- Botões de atalho no rodapé: **Soltar** e **Levar ao ninho** (quando carrega algo) e **Atacar** (quando há predador).
- Carregando algo, tocar em outro material ou comida faz o pássaro ir até lá e **trocar** (o item antigo cai no chão).

### Pilares
1. **Cada etapa = uma fase real da vida da ave.** Nada de mecânica sem justificativa biológica (ou licença criativa declarada).
2. **Decisões ecoam.** O que você faz numa etapa muda a próxima (ex.: plástico no ninho → filhotes com mais frio e fome).
3. **O casal joga junto.** O parceiro é uma IA que ajuda a construir, alimentar e defender.
4. **Ciclo infinito.** Cada estação termina gerando a próxima, com herança e novos desafios.

## 2. Ciclo de vida real × mecânicas

| Fase real | O que acontece na natureza | Mecânica no jogo |
|---|---|---|
| Território | Casal monogâmico, defende o território com agressividade o ano todo; canta em postes, fios e topo de árvores; um dos primeiros a cantar de madrugada | **Etapa 0:** escolher o território (cidade, beira-rio, fazenda) e expulsar rivais com o canto |
| Cortejo | Ergue a crista amarela da coroa no cortejo e em ameaças; exibição de "asas para cima" | **Etapa 1:** dueto de canto (repetir a sequência *bem-te-vi*) + erguer a crista no momento certo |
| Ninho | Macho e fêmea constroem juntos um ninho **esférico com entrada lateral**, de capim, gravetos e musgo, forrado com penas; na cidade usa papel, plástico e barbante | **Etapa 2:** voar coletando material; estrutura → cúpula → forro; lixo urbano acelera, mas piora a qualidade |
| Postura | 2–4 ovos creme com pintas marrom-avermelhadas | Nº de ovos depende do sucesso no cortejo |
| Incubação | ~17 dias (varia por região) | **Etapa 3:** manter os ovos aquecidos × sair para comer (barra de energia), chuva e sol forte |
| Filhotes | Nascem sem penas e de olhos fechados (altriciais); os dois pais alimentam | **Etapa 4:** caçar insetos no ar, mergulhar por peixes e girinos, pegar frutas; dividir comida entre os filhotes |
| Defesa | Enfrenta gaviões e até urubus que entram no território | **Etapa 4:** afastar predadores com investidas; o parceiro ajuda no ataque |
| Primeiro voo | Filhotes deixam o ninho e seguem os pais por um tempo | **Etapa 5:** guiar os filhotes até poleiros seguros e ensinar a caçar |
| Independência | Jovens ganham território próprio; adulto pode viver ~7 anos | **Etapa 6:** escolher um filhote herdeiro → nova estação com traços herdados |

## 3. Etapas em detalhe

### Etapa 0 — Conquistar o território *(nova)*
- Mapa com 3 biomas: **Cidade** (postes, fios, antenas, chafariz, gatos, ração de pet), **Beira-rio** (peixes, girinos, cobras), **Fazenda/cerrado** (gado com carrapatos, gafanhotos, carcará).
- Rivais pousam no seu território: vença em um "duelo de canto" (ritmo) ou com investidas.
- Território melhor = mais comida, porém mais disputado.

### Etapa 1 — Procurar uma parceira ✅ *(no protótipo)*
- **Busca em voo:** três bem-te-vis pousam em pontos sorteados da praça (galho, fio, banco, banca, carro, chafariz) e cantam de tempos em tempos. O canto soa mais alto de perto e, fora da tela, vira uma seta amarela. O botão **Cantar** faz todas responderem.
- Duas já têm par: ao chegar perto, o macho dela aparece e o casal canta em dueto de crista erguida ("já tem par"). A que está sozinha responde e o dueto começa ali mesmo. Depois de 45 s sem achar, a seta passa a apontar a parceira.
- **Dueto:** a candidata canta uma sequência de notas **BEM · TE · VI**; você repete (estilo "Genius").
- Após cada acerto, um evento rápido: **erguer a crista** quando o marcador passar pela faixa dourada.
- Afinidade enche a barra de coração. Erros custam vidas; vidas restantes = **número de ovos (2–4)**.
- Ideia futura: exibição de "asas para cima" como golpe especial; dueto do casal todo dia de manhã recarrega energia.

### Etapa 2 — Construir o ninho ✅ *(no protótipo)*
- Toque na tela para voar. Material é coletado ao passar por cima e entregue ao encostar no ninho.
- Cada material tem um feixe de luz e um anel pulsando: **amarelo** = estrutura (gravetos, capim), **azul** = forro (penas, musgo), **vermelho** = lixo. O brilho fica mais forte no que o ninho precisa agora, e os mais próximos ganham etiqueta com o nome.
- **Estrutura** (capim, gravetos, barbante, plástico) e **forro** (penas, musgo, paina).
- Barbante e plástico contam para a estrutura, mas reduzem a **qualidade** (risco real de enroscar filhotes).
- O parceiro traz material sozinho de tempos em tempos.
- **Ladrão de ninho:** um "bem-te-vi-pirata" pousa e arranca material até ser expulso.
  *(Licença criativa: o bem-te-vi-pirata, *Legatus leucophaius*, rouba ninhos fechados de outros tiranídeos;
  não encontramos registro com o bem-te-vi como vítima.)*
- Ideia futura: escolher o local (forquilha alta, poste, palmeira) — trade-off sombra × vento × acesso de predadores; o casal pode **mudar o ninho de árvore reaproveitando o material** (comportamento já observado).

### Etapa 3 — Postura e incubação *(nova)*
- Segure para chocar (temperatura sobe) e solte para caçar (energia sobe). Ovos frios demais ou quentes demais por muito tempo não eclodem.
- Eventos: chuva forte (precisa ficar), calor do meio-dia (sombra), predador noturno (coruja jacurutu).
- O parceiro traz comida enquanto você choca — se o cortejo foi bom, ele traz mais.

### Etapa 4 — Alimentar e proteger os filhotes ✅ *(no protótipo)*
- Cada filhote tem **fome** e **crescimento**. Filhotes famintos piam e abrem o bico.
- Fontes de comida (valor nutricional diferente): insetos em voo (rápido, pouco), peixe no lago (mergulho no tempo certo, muito), frutas (fácil, pouco).
- Predadores: **tucano** (vem dos telhados, rouba ovos/filhotes), **gavião** (circula alto e mergulha), **gato doméstico** (atravessa a rua e sobe pelo tronco; na praça ele substitui a cobra). Acerte investidas para expulsar; o parceiro ajuda.
- Ninho de baixa qualidade → filhotes perdem calor e sentem fome mais rápido.
- Ideia futura: **cobra-coral** — o bem-te-vi evita instintivamente o padrão coral; atacar dá penalidade (ensina o fato real).

### Etapa 5 — Primeiro voo *(nova)*
- Filhotes saem do ninho voando mal: guie-os em sequência de poleiros, evitando gatos e fios.
- Mini-tutoriais: o filhote copia sua técnica de caça (pegar inseto do poleiro, mergulho, carrapato no gado).

### Etapa 6 — Nova geração *(nova)*
- Escolha o filhote herdeiro. Cada um tem um traço sorteado (asas fortes, canto potente, olho de pescador).
- A estação seguinte começa com esse traço + o território herdado (ou um novo).

## 4. Sistemas transversais
- **Energia do adulto:** voar e atacar gastam; comer recupera. Força escolhas (comer você × alimentar filhotes).
- **Calendário:** temporada reprodutiva no Brasil ≈ julho a dezembro. Cada dia de jogo = alguns segundos; incubação ~17 dias.
- **Dia e noite:** de dia caça e defesa; à noite predadores noturnos (coruja, gambá) e o ninho precisa estar fechado.
- **Clima:** chuva aumenta insetos depois que para, mas esfria os ovos; seca reduz o lago.
- **Diário do naturalista:** cada fato real descoberto vira uma página colecionável (camada educativa).
- **Consequências entre etapas:** cortejo → nº de ovos; ninho → qualidade/temperatura; alimentação → traços dos filhotes.

## 5. Ameaças e rivais

| Ameaça | Onde | Comportamento no jogo |
|---|---|---|
| Tucano (tucanuçu) | Árvores | Lento, insistente, mira ovos e filhotes |
| Gavião | Céu aberto | Circula e mergulha rápido; precisa de interceptação |
| Cobra | Tronco | Sobe devagar; mais resistente |
| Coruja jacurutu | Noite | Ataca adultos distraídos fora do ninho |
| Gato doméstico | Cidade | Espreita filhotes no primeiro voo |
| Bem-te-vi-pirata *(licença criativa)* | Ninho pronto | Rouba o ninho/material |
| Rival bem-te-vi | Território | Duelo de canto |

## 6. Mais ideias tiradas da biologia
- **Pescador:** mergulha do poleiro atrás de peixes e girinos, como um martim-pescador → mini-game de mergulho.
- **Faxineiro do gado:** pousa em bois e cavalos para comer carrapatos → bônus de comida na fazenda.
- **Esperto da cidade:** rouba ração do pote do cachorro → comida fácil, mas arriscada.
- **Banho no chafariz:** recupera energia e limpa parasitas.
- **Canto do amanhecer:** quem canta primeiro de manhã ganha bônus de território.
- **Ninho de lixo:** campanha educativa — recolher lixo plástico do mapa dá pontos extras.

## 7. Escopo do protótipo atual (`src/jogo.html` → `www/index.html`)
Jogável no navegador do celular e já empacotado como APK:
1. Etapa 1 — busca em voo pelas bem-te-vis da praça, depois dueto de canto + crista onde a parceira estiver
2. Etapa 2 — voo livre pela praça coletando material natural × lixo, com ladrão de ninho
3. Interlúdio — postura (nº de ovos herdado da etapa 1) e incubação
4. Etapa 3 — alimentar (insetos, peixes do chafariz, pitangas) e defender (tucano, gavião, gato) por 18 dias
5. Tela final com resumo do ciclo e estrelas

Aves esculpidas em código: corpo e cabeça com plumagem pintada (coroa preta com faixa amarela, sobrancelha branca, máscara, garganta branca, barriga amarela, asa com bordas ferrugem), bico de duas partes que abre ao cantar, olhos com brilho, crista que sobe, asas com penas abertas no voo, cauda em leque e pés com dedos. Pousado, o bem-te-vi fica ereto e olha em volta. Tucano-toco, gavião-carijó (peito barrado) e bem-te-vi-pirata (peito estriado) seguem o mesmo método. Sons sintetizados — sem arquivos de som externos.

**Cenário modelado no Blender** (`arte/modelar_praca.py` → `praca.glb`): prédios com lojas, toldos listrados, letreiros, varandas, ar-condicionado e caixa-d'água; sobrados com frontão; casas coloniais com venezianas e telhado de telha; árvore do ninho com os galhos nas medidas do jogo; ipês floridos com flores caídas no chão; pitangueira; postes coloniais; bancos de ripas; coreto com guarda-corpo e lambrequim; banca de jornal; postes de concreto com fiação e transformador; carros; chafariz com azulejo; orelhões, ponto de ônibus, placas de rua e meios-fios. **Gramado e flores** (`arte/modelar_flores.py` → `flores.glb`): tufos de capim, capim alto rente ao meio-fio e em volta dos troncos, margaridas, maria-sem-vergonha vermelha e rosa, cravo-de-defunto e sálvia azul. O jogo planta cópias só dentro dos quatro canteiros (fora da calçada em ondas, do chafariz, do coreto, da banca e dos troncos), em manchas de uma espécie só, e elas balançam com o vento. A grama tem folhinhas desenhadas, faixas suaves de cortador, manchas mais claras e amareladas e borda mais escura junto ao meio-fio. O chão (pedra, calçada portuguesa em ondas), a água e o céu continuam no código.

## 8. Tecnologia
- **Agora:** Three.js (WebGL) + JavaScript → empacotado com **Capacitor 7** como app Android (APK de debug gerado).
- **Aves modeladas no Blender** por scripts (`arte/`): bem-te-vi, bem-te-vi-pirata, filhote, tucanuçu e gavião-carijó, exportados em `.glb` com nós articulados (cabeça, bico, crista, asas, cauda, garras) que o jogo anima. O gato ainda é desenhado em código.
- **Cenário no Blender:** ~150 mil triângulos em 14 malhas, cor por vértice e sombreamento facetado. As peças antigas desenhadas em código continuam na cena só como colisão invisível (para tocar e pousar); se o `.glb` não carregar, elas voltam a aparecer.
- **Se o projeto crescer** (física, muitas fases, loja): migrar para **Godot 4** ou Unity, reaproveitando os modelos `.glb`.

## 9. Fontes
- [Prefeitura de São Paulo — Espécies da cidade: bem-te-vi](https://prefeitura.sp.gov.br/web/meio_ambiente/w/servicos/fauna/especies_da_cidade/11315)
- [WikiAves — Great Kiskadee](https://en.wikiaves.com.br/wiki/en:great-kiskadee)
- [Animal Diversity Web — *Pitangus sulphuratus*](https://animaldiversity.org/accounts/Pitangus_sulphuratus)
- [Texas Breeding Bird Atlas — Great Kiskadee](https://txtbba.tamu.edu/?p=656)
- [Petz — Pássaro bem-te-vi](https://www.petz.com.br/blog/?p=2455647)
- [Ornitología Neotropical / Kerwa — usurpação de ninhos pelo *Legatus leucophaius*](https://kerwa.ucr.ac.cr/handle/10669/79071?show=full)
