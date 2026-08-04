<div align="center">

<img src="packaging/warpzone.svg" width="96" alt="">

# Warpzone

**Pula o navegador inteiro e cai direto no site que você quer.**

Transforma qualquer URL num app desktop de verdade — sem abas, sem barra de endereço,
sem extensão, sem "restaurar sessão". Só o conteúdo, numa janela de vidro que segue
o tema do seu desktop.

[![Linux](https://img.shields.io/badge/Linux-Wayland%20%7C%20X11-4c566a?style=flat-square&logo=linux&logoColor=white)](#requisitos)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white)](#requisitos)
[![WebKitGTK](https://img.shields.io/badge/WebKitGTK-4.1-1d99f3?style=flat-square)](#como-funciona)
[![Dependências](https://img.shields.io/badge/depend%C3%AAncias-zero-3fb950?style=flat-square)](#requisitos)
[![Testes](https://img.shields.io/badge/testes-65%20passing-3fb950?style=flat-square)](#testes)

<img src="docs/launcher.png" alt="Launcher do Warpzone: campo de URL e grade de favoritos em vidro sobre o wallpaper borrado" width="720">

</div>

---

## O nome

No Super Mario Bros, a Warp Zone é o cano que pula o jogo inteiro e te larga
exatamente no mundo que você queria. É isso que este app faz com uma URL: nada de
atravessar abas, favoritos e sessão restaurada pra chegar num painel que roda em
`localhost`. Você entra no cano e já está lá.

## Por que isso existe

Você roda um painel em `localhost:5173`. Abrir ele num navegador significa carregar
uma janela com 40 abas, um gerenciador de senhas pedindo atenção, e a sua sessão de
trabalho misturada com a do YouTube.

O Warpzone abre esse painel como se fosse um aplicativo instalado: entrada no menu,
ícone próprio, janela limpa. E como ele não é amarrado a nenhum site específico,
serve pra qualquer URL que você queira tratar como app.

## Destaques

| | |
|---|---|
| 🪟 **Zero cromo** | Sem abas, sem barra de endereço, sem menu. A janela inteira é o site. |
| 🔮 **Vidro de verdade** | A janela tem canal alfa e quem borra o fundo é o compositor — não é `backdrop-filter` fingindo profundidade. |
| 🎨 **Tema vivo** | As cores saem do [Caelestia](https://github.com/caelestia-dots/shell) em tempo de execução. Trocou o wallpaper, o app acompanha. |
| ⭐ **Favoritos seus** | Começa vazio. Você adiciona, edita e remove pela própria tela, com seletor de ícone. |
| ⌨️ **Só teclado** | Filtro ao vivo, `Enter` abre, `Ctrl+D` favorita, `Ctrl+L` volta. |
| 📦 **Dependência zero** | Nada de `pip install`, nada de Electron. Usa o que já vem no sistema. |

## Instalar

```sh
git clone git@github.com:LuisMarchio03/warpzone.git
cd warpzone
sh packaging/install.sh
```

Isso cria `~/.local/bin/warpzone` e a entrada **Warpzone** no menu de aplicativos.
Não usa `sudo` e não escreve nada fora da sua `$HOME`.

> O instalador **não copia o código** — ele aponta pro repositório onde você clonou.
> Mexeu no CSS? Fecha e abre o app, a mudança já está lá.

Pra remover: `sh packaging/uninstall.sh` (seus favoritos ficam; `--tudo` apaga eles também).

## Usar

```sh
warpzone                          # abre o launcher
warpzone localhost:5173           # vai direto, completando o http://
warpzone grafana.exemplo.dev      # completa o https://
```

Ou simplesmente procure **Warpzone** no launcher do seu desktop.

### Atalhos

| Tecla | O que faz |
|:---|:---|
| `Ctrl` `L` | volta ao launcher |
| `Ctrl` `R` | recarrega (no launcher, redesenha) |
| `Ctrl` `D` | favorita a página atual |
| `Alt` `←` / `Alt` `→` | histórico — do launcher, retoma o último site |
| `F11` | tela cheia |
| `Ctrl` `Shift` `I` | inspetor do WebKit |
| `Ctrl` `Q` | sair |
| `Esc` | limpa o filtro / fecha o formulário |

No launcher, digitar filtra os favoritos ao vivo. `Enter` abre o primeiro
resultado — ou navega direto, se o que você digitou parecer uma URL.

### Favoritos

<img src="docs/favoritos.png" alt="Formulário de favorito com campos nome, URL e seletor de ícone" width="420" align="right">

Clique em **+ novo favorito** para abrir o formulário. Você escolhe:

- **nome** — o rótulo do card
- **URL** — pode omitir o esquema; `localhost:3000` vira `http://localhost:3000`
- **ícone** — qualquer glifo do [Material Symbols Rounded](https://fonts.google.com/icons), com 24 sugestões clicáveis e preview ao vivo

O lápis no card edita, o × remove. Tudo grava na hora em
`~/.config/warpzone/bookmarks.json`, que também dá pra editar na mão:

```json
[
  { "nome": "Painel", "url": "http://127.0.0.1:5173", "icone": "dashboard" }
]
```

<br clear="right">

## Requisitos

Tudo vem dos repositórios da distro — **nenhum pacote Python é instalado**.

```sh
# Arch / CachyOS
sudo pacman -S --needed python-gobject gtk3 webkit2gtk-4.1

# Debian / Ubuntu
sudo apt install python3-gi gir1.2-webkit2-4.1
```

O `install.sh` confere isso antes de instalar e avisa o que falta.

**Opcionais:** fontes `Rubik`, `Material Symbols Rounded` e `CaskaydiaCove NF`
(o app cai em fontes do sistema sem elas, mas os ícones viram texto). O blur é do
compositor — em Hyprland, KWin ou Hyprland-likes ele aparece sozinho; em ambientes
sem blur o app continua funcionando, só mais opaco.

## Como funciona

Uma janela GTK3 sem decoração com **um único `WebKit2.WebView`**, que alterna entre
dois estados: o *launcher* (HTML local, injetado por `load_html`) e o *site* (URL
remota). O JavaScript fala com o Python por `window.webkit.messageHandlers`.

```
warpzone/
├── app.py             janela, atalhos, ponte JS↔Python
├── __main__.py        entrada CLI
├── urls.py            texto digitado → URL navegável
├── scheme.py          scheme.json do Caelestia → CSS custom properties
├── bookmarks.py       CRUD dos favoritos
├── services.py        detecta serviço systemd parado numa falha local
├── launcher_page.py   costura HTML + CSS + JS + dados numa página só
└── launcher/          index.html · style.css · app.js · error.html
```

A regra de ouro do projeto: **toda lógica pura vive fora do `app.py`**, então a
suíte de testes roda inteira sem abrir uma janela.

Três detalhes que custaram descoberta e estão documentados no código:

1. `load_html()` **apaga o histórico** do WebView — por isso `Ctrl+R` e `Alt+←` usam
   estado próprio em vez de delegar ao WebKit.
2. Sem `set_background_color(alpha=0)` o WebKit pinta um fundo branco **por baixo**
   do CSS, e o vidro nunca aparece.
3. O véu translúcido precisa ficar em torno de 55% — acima disso o blur do
   compositor some visualmente.

### Onde ficam as coisas

| Caminho | O quê |
|:---|:---|
| `~/.config/warpzone/bookmarks.json` | seus favoritos |
| `~/.local/share/warpzone/` | cookies e localStorage do WebKit |
| `~/.local/state/caelestia/scheme.json` | fonte das cores (somente leitura) |

## Testes

```sh
uv venv --python /usr/bin/python3 --system-site-packages .venv
uv pip install --python .venv/bin/python pytest
.venv/bin/pytest
```

> O `--python /usr/bin/python3` é obrigatório: sem ele o `uv` cria o venv com um
> CPython próprio e o `gi` — que é pacote de sistema — fica invisível.

`app.py` não tem teste automatizado; é GTK puro, validado por smoke manual. Pra
exercitar os atalhos sem tocar no teclado:

```sh
hyprctl dispatch sendshortcut "CTRL,L,class:^(warpzone)$"
```

## Licença

MIT — veja [LICENSE](LICENSE).
