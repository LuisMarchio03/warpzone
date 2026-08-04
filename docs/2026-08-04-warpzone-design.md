# warpzone — mini-browser desktop no padrão Caelestia

**Data:** 2026-08-04
**Responsável:** Luis Gabriel Marchio Batista
**Status:** desenho aprovado, pendente implementação

## Problema

O claude-cockpit roda em `http://127.0.0.1:5173` (unit `claude-cockpit-frontend.service`) e hoje só é
acessível dentro de um navegador completo — abas, barra de endereço, extensões, ruído. O objetivo é
usá-lo como se fosse um app desktop: uma janela limpa, só o conteúdo. Como o mesmo problema vale para
outras URLs internas (Grafana, Jira, Outline, GitLab, Jenkins), a solução é um mini-browser genérico
com uma tela inicial onde se digita a URL, e não um wrapper dedicado ao cockpit.

Restrições descobertas no ambiente:

- Não há Chromium nem Electron instalados (só Firefox e Zen), então `--app=URL` não é opção.
- `webkit2gtk-4.1` (2.52.5) e `python-gobject` (3.56.3) já estão instalados — dependências novas: zero.
- Hyprland está com blur ligado (`$blurEnabled = true`, `$blurSize = 8`, `$blurPasses = 2`), então
  uma janela com canal alfa ganha blur real do compositor.
- Python do sistema é 3.14 externally-managed; `gi` é pacote de sistema e não existe num venv comum.

## Decisões tomadas

| Decisão | Escolha | Por quê |
|---|---|---|
| Toolkit | PyGObject + GTK3 + WebKit2GTK 4.1 | único stack de webview já instalado; `firefox --kiosk` não dá tela de launcher nem controle de UI; Tauri/Electron traria toolchain inteira sem ganho |
| Chrome da UI | nenhum — só atalhos de teclado | pedido explícito: "só o cockpit rodando", sem informação de navegador na tela |
| Launcher | input de URL + grid de cards fixos | acesso rápido aos destinos recorrentes sem virar gerenciador de favoritos |
| Boot | sem argumento abre o launcher; `warpzone <URL>` vai direto | o `.desktop` do cockpit passa a URL e abre direto no app |
| Cores | lidas do `scheme.json` do Caelestia em runtime | tema segue o wallpaper do usuário sem recompilar nada |

## Arquitetura

Quatro módulos, cada um testável isoladamente. A regra que separa eles: **tudo que é lógica pura
mora fora do `app.py`**, para que a suíte de testes rode sem abrir janela.

```
warpzone/
├── warpzone/
│   ├── app.py          # janela GTK + WebView + atalhos + ponte JS  (impuro, smoke manual)
│   ├── scheme.py       # scheme.json do Caelestia -> CSS custom properties
│   ├── urls.py         # normalização de entrada do usuário -> URL navegável
│   ├── bookmarks.py    # CRUD do bookmarks.json + seed inicial
│   └── launcher/
│       ├── index.html  # tela de launcher (placeholders substituídos no boot)
│       ├── style.css   # glassmorphism, grid de cards
│       ├── app.js      # input, filtro, ponte postMessage
│       └── error.html  # página de falha de carregamento
├── tests/
├── packaging/
│   ├── warpzone.desktop
│   └── warpzone        # wrapper executável para o ~/.local/bin
└── docs/
```

### `app.py` — a janela

- `Gtk.Window` com `set_decorated(False)` e visual RGBA do screen, para que o alfa chegue ao compositor.
- `WebKit2.WebView` com `set_background_color(RGBA(0,0,0,0))` — sem isso o WebKit pinta branco por baixo
  do CSS e o blur do Hyprland não aparece.
- `set_wmclass`/app-id `warpzone`, para regra de janela no Hyprland se necessário.
- `WebKit2.WebsiteDataManager` apontando para `~/.local/share/warpzone/` — cookies e localStorage
  persistem, senão todo site logado pede login a cada abertura.
- Dois estados na mesma janela e no mesmo WebView: **launcher** (HTML local) e **site** (URL remota).
  Não há segunda janela nem abas.

### `scheme.py` — cores do Caelestia

Lê `~/.local/state/caelestia/scheme.json` (120 chaves M3: `background`, `surfaceContainerHigh`,
`primary`, `error`, …), converte cada chave camelCase em `--m3-kebab-case` com valor `#rrggbb`, e
devolve um bloco `:root{…}` injetado no `index.html` antes do `load_html`. Também expõe os hex
individualmente para o Python montar a página de erro.

Ausência ou JSON corrompido do arquivo não pode derrubar o app: cai num dicionário de fallback com o
esquema escuro atual embutido.

### `urls.py` — normalização

Regras, na ordem:

1. String já com esquema (`http://`, `https://`, `file://`) passa direto.
2. `localhost`/`127.0.0.1`/`0.0.0.0` com ou sem porta → prefixo `http://`.
3. Qualquer coisa com ponto no meio e sem espaço (`grafana.exemplo.dev`, `wiki.exemplo.com/doc/x`)
   → prefixo `https://`.
4. Sobrou → não é URL; o launcher exibe estado inválido no input e não navega. (Não há busca web:
   isso é um mini-browser de destinos internos, não um navegador geral.)

### `bookmarks.py` — cards

`~/.config/warpzone/bookmarks.json`, lista de `{nome, url, icone}` onde `icone` é o nome de um
glifo do Material Symbols Rounded. Seed na primeira execução:

| Nome | URL | Ícone |
|---|---|---|
| Cockpit | http://127.0.0.1:5173 | dashboard |
| Cockpit API | http://127.0.0.1:8765/docs | api |
| Grafana | https://grafana.exemplo.dev | monitoring |
| Jira | https://jira.exemplo.com.br | task_alt |
| Outline | https://wiki.exemplo.com | menu_book |
| GitLab | https://gitlab.exemplo.dev | merge |
| Jenkins | https://jenkins.exemplo.dev | build |

Arquivo ilegível → volta ao seed sem apagar o original (renomeia para `.bak`).

### Ponte JS → Python

`window.webkit.messageHandlers.<handler>.postMessage(payload)`, três handlers:

- `nav` — string com o que o usuário digitou ou o card clicado; Python normaliza e navega.
- `bookmarkAdd` / `bookmarkRemove` — `{nome, url}`; Python grava e devolve a lista atualizada
  chamando `evaluate_javascript` com `window.__cockpitSetBookmarks(...)`.

Direção contrária só existe para atualizar a lista de cards. Nenhum handler recebe caminho de arquivo
nem executa comando — a superfície fica fechada mesmo com uma página remota carregada.

## Design visual

Padrão Caelestia: Material 3 dinâmico + vidro. Fontes já instaladas e confirmadas —
`Rubik` (texto), `Material Symbols Rounded` (ícones), `CaskaydiaCove NF` (URL/mono).

- Fundo da janela transparente (`rgba` do `--m3-surface` a ~72%) sobre o blur real do Hyprland.
- Cartão central do input: superfície `--m3-surface-container` a ~55%, borda `1px` em
  `--m3-outline-variant` a 40%, raio 28px, sombra difusa baixa.
- Grid responsivo de cards (`repeat(auto-fill, minmax(150px, 1fr))`), cada card com ícone grande em
  `--m3-primary`, hover elevando 2px e clareando para `--m3-surface-container-high`.
- Digitar filtra os cards ao vivo; Enter navega para o que estiver no input.
- Transições de 150–200ms com `cubic-bezier(0.2, 0, 0, 1)` (curva padrão M3 expressiva).

## Atalhos

| Tecla | Ação |
|---|---|
| `Ctrl+L` | volta ao launcher (e foca o input) |
| `Ctrl+R` | recarrega |
| `Ctrl+D` | fixa a página atual como card |
| `Alt+←` / `Alt+→` | histórico do WebView |
| `F11` | fullscreen |
| `Ctrl+Shift+I` | devtools |
| `Ctrl+Q` | fecha |
| `Esc` (no launcher) | limpa o input / restaura os cards |

## Tratamento de erro

`load-failed` do WebView carrega `error.html` já com as cores do scheme: título, host que falhou,
botão "tentar de novo" e "voltar ao launcher". Quando o host é `127.0.0.1:5173` ou `:8765`, o Python
consulta `systemctl --user is-active claude-cockpit-frontend.service` (respectivamente `-backend`) e,
se estiver parado, a página mostra o comando exato de subir. Falha do `systemctl` é engolida — a
dica some, o erro genérico permanece.

## Entrega

- `packaging/warpzone` copiado para `~/.local/bin/warpzone` (`python3 -m warpzone "$@"`).
- `warpzone.desktop` em `~/.local/share/applications/`, nome "Warpzone", `Exec` com a URL do
  cockpit, `StartupWMClass=warpzone`.
- Keybind no Hyprland fica de fora por padrão; o `.desktop` já cobre o lançamento pelo launcher do
  Caelestia. Se depois quiser tecla dedicada, é uma linha no `hypr-user.conf`.

## Testes

`uv venv --system-site-packages` para que o `gi` do sistema continue visível, pytest dentro dele.

- `urls.py`: cada regra de normalização, incluindo entradas que devem ser rejeitadas.
- `bookmarks.py`: seed na primeira execução, add/remove idempotente, arquivo corrompido → `.bak` + seed.
- `scheme.py`: conversão camelCase→kebab, hex com `#`, arquivo ausente → fallback, JSON inválido → fallback.
- `app.py`: sem teste automatizado. Validação é smoke manual — abrir a janela, carregar o cockpit,
  exercitar cada atalho, matar a unit do frontend e conferir a página de erro.

## Fora de escopo

Abas, downloads, gerenciador de histórico, múltiplas janelas simultâneas, busca web no input, modo
claro forçado (segue o `mode` do scheme), sincronização de bookmarks.

## Riscos conhecidos

- **Blur pode não aparecer** se o Hyprland não aplicar blur em janelas transparentes sem regra
  explícita. Mitigação: o CSS tem gradiente próprio sob o vidro, então a tela continua bonita sem
  blur do compositor; se preciso, adiciona-se `windowrulev2 = blur, class:^(warpzone)$`.
- **WebKit2GTK 4.1 é GTK3.** Se um dia o webkitgtk-6.0 (GTK4) entrar no repo, a migração é do `app.py`
  apenas — `scheme.py`, `urls.py` e `bookmarks.py` não mudam.
