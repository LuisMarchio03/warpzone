# warpzone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um mini-browser desktop sem cromo que abre o claude-cockpit (e qualquer outra URL) numa janela limpa, com tela de launcher em glassmorphism seguindo o tema dinâmico do Caelestia.

**Architecture:** Uma janela GTK3 sem decoração contendo um único `WebKit2.WebView` que alterna entre dois estados — launcher (HTML local, injetado com `load_html`) e site (URL remota). Toda a lógica pura (normalização de URL, leitura do scheme, bookmarks, dica de systemd, renderização da página) vive em módulos sem GTK e é coberta por pytest; `app.py` só faz janela, atalhos e a ponte JS↔Python.

**Tech Stack:** Python 3.14 do sistema, PyGObject 3.56.3, GTK 3.24.52, WebKit2GTK 4.1 (2.52.5), pytest em venv `--system-site-packages`, uv.

## Global Constraints

- **Sem git neste projeto** (decisão do usuário em 2026-08-04, mesma convenção da aloy). Todo passo
  "Commit" e o `git init` da Task 1 estão **cancelados** — ignorar onde aparecerem abaixo. O
  `.gitignore` também não é necessário.
- **Zero dependências novas em runtime.** Só stdlib + `gi` (pacote de sistema). Qualquer `pip install` de runtime é violação do design.
- **Roda no `/usr/bin/python3`**, não num venv comum — `gi` é pacote de sistema. O venv de teste existe só pro pytest e é criado com `uv venv --system-site-packages`.
- **Raiz do projeto:** `~/Projects/warpzone`. Todos os caminhos relativos partem daí.
- **Versões da API já verificadas nesta máquina** (não improvisar variação):
  - `gi.require_version("Gtk", "3.0")` e `gi.require_version("WebKit2", "4.1")`.
  - `UserContentManager.register_script_message_handler(name)` recebe **1 argumento**.
  - O sinal `script-message-received` entrega um `WebKitJavascriptResult` → use `.get_js_value().to_string()`.
  - `WebView.evaluate_javascript(script, length, ...)` exige o `length`; passar `-1`.
  - `WebContext.new_with_website_data_manager(dm)` existe.
- **Nenhum `innerHTML` com dado de bookmark.** Nome de bookmark vem de `<title>` de página remota; montar DOM com `createElement` + `textContent`.
- **Cores nunca hardcoded no CSS.** Todo valor sai de `var(--m3-*)` gerado do `scheme.json`. Exceção única: os fallbacks dentro de `scheme.py`.
- **Idioma:** UI e comentários em pt-BR; nomes de código em inglês, exceto as chaves do `bookmarks.json` (`nome`, `url`, `icone`) que são pt-BR por serem contrato de arquivo do usuário.
- **Fontes** (confirmadas instaladas): `Rubik` (texto), `Material Symbols Rounded` (ícones), `CaskaydiaCove NF` (mono).

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `warpzone/urls.py` | texto digitado → URL navegável ou `None` |
| `warpzone/scheme.py` | `scheme.json` do Caelestia → CSS custom properties (hex + triplet RGB) |
| `warpzone/bookmarks.py` | CRUD do `bookmarks.json` + seed |
| `warpzone/services.py` | dica de `systemctl` quando um host local do cockpit não responde |
| `warpzone/launcher_page.py` | monta o HTML final do launcher e da página de erro (inline de CSS/JS) |
| `warpzone/launcher/index.html` | estrutura da tela de launcher |
| `warpzone/launcher/style.css` | glassmorphism, grid de cards |
| `warpzone/launcher/app.js` | input, filtro ao vivo, ponte `postMessage` |
| `warpzone/launcher/error.html` | página de falha de carregamento |
| `warpzone/app.py` | janela GTK, WebView, atalhos, handlers da ponte |
| `warpzone/__main__.py` | entrada CLI |
| `packaging/` | `.desktop`, ícone SVG, `install.sh` |
| `tests/` | pytest dos módulos puros |

---

### Task 1: Esqueleto do projeto e normalização de URL

**Files:**
- Create: `warpzone/__init__.py`
- Create: `warpzone/urls.py`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Test: `tests/test_urls.py`

**Interfaces:**
- Consumes: nada.
- Produces: `urls.normalize(raw: str) -> str | None` — devolve URL navegável ou `None` quando a entrada não é endereço.

- [ ] **Step 1: Criar o repositório e o esqueleto**

```bash
cd ~/Projects/warpzone
git init
mkdir -p warpzone/launcher packaging tests
touch warpzone/__init__.py
```

`.gitignore`:

```gitignore
__pycache__/
*.pyc
.venv/
.pytest_cache/
```

`pyproject.toml`:

```toml
[project]
name = "warpzone"
version = "0.1.0"
description = "Mini-browser desktop para o claude-cockpit, no padrão Caelestia"
requires-python = ">=3.11"
dependencies = []

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 2: Criar o venv de teste**

```bash
uv venv --python /usr/bin/python3 --system-site-packages .venv
uv pip install --python .venv/bin/python pytest
.venv/bin/python -c "import gi; print('gi visivel no venv:', gi.__version__)"
```

Expected: imprime `3.56.3` — se falhar, o `gi` não está visível e nada mais funciona.

**`--python /usr/bin/python3` é obrigatório.** Sem ele o uv cria o venv com um CPython próprio
(3.12) em vez do Python do sistema (3.14.6), e `--system-site-packages` aponta para um
site-packages que não tem `gi`.

- [ ] **Step 3: Escrever o teste que falha**

`tests/test_urls.py`:

```python
"""Normalização do que o usuário digita no launcher."""

import pytest

from warpzone.urls import normalize


@pytest.mark.parametrize(
    "raw, esperado",
    [
        # já tem esquema: passa direto
        ("http://127.0.0.1:5173", "http://127.0.0.1:5173"),
        ("https://grafana.exemplo.dev/d/abc", "https://grafana.exemplo.dev/d/abc"),
        ("file:///tmp/x.html", "file:///tmp/x.html"),
        # host local: http
        ("localhost:5173", "http://localhost:5173"),
        ("127.0.0.1:8765/docs", "http://127.0.0.1:8765/docs"),
        ("localhost", "http://localhost"),
        ("0.0.0.0:3000", "http://0.0.0.0:3000"),
        # domínio: https
        ("grafana.exemplo.dev", "https://grafana.exemplo.dev"),
        ("wiki.exemplo.com/doc/abc", "https://wiki.exemplo.com/doc/abc"),
        ("jira.exemplo.com.br:8443/browse/PM-1", "https://jira.exemplo.com.br:8443/browse/PM-1"),
        # espaço em volta é aparado
        ("  localhost:5173  ", "http://localhost:5173"),
    ],
)
def test_normaliza_entradas_validas(raw, esperado):
    assert normalize(raw) == esperado


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "cockpit",             # palavra solta não é URL
        "abrir o grafana",     # frase com espaço
        "pm 18090",
        ".",
        ".com",
        "grafana.",
    ],
)
def test_rejeita_entradas_que_nao_sao_url(raw):
    assert normalize(raw) is None
```

- [ ] **Step 4: Rodar o teste e confirmar que falha**

Run: `.venv/bin/pytest tests/test_urls.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'warpzone.urls'`

- [ ] **Step 5: Implementar**

`warpzone/urls.py`:

```python
"""Converte o que o usuário digita numa URL navegável."""

from __future__ import annotations

import re

# esquema já presente (http://, https://, file://, ...)
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0"})


def normalize(raw: str) -> str | None:
    """Devolve a URL a navegar, ou None quando a entrada não é um endereço.

    Não há busca web: este é um browser de destinos internos, então tudo que
    não se parece com endereço é rejeitado em vez de virar consulta.
    """
    text = raw.strip()
    if not text or any(char.isspace() for char in text):
        return None

    if _SCHEME_RE.match(text):
        return text

    # host = tudo antes da primeira barra, interrogação ou cerquilha
    host = re.split(r"[/?#]", text, maxsplit=1)[0]
    hostname = host.split(":", 1)[0]

    if hostname in _LOCAL_HOSTS:
        return f"http://{text}"

    if "." in hostname and not hostname.startswith(".") and not hostname.endswith("."):
        return f"https://{text}"

    return None
```

- [ ] **Step 6: Rodar o teste e confirmar que passa**

Run: `.venv/bin/pytest tests/test_urls.py -v`
Expected: PASS — 19 passed (11 válidas + 8 rejeitadas).

- [ ] **Step 7: Commit**

```bash
git add .gitignore pyproject.toml warpzone/__init__.py warpzone/urls.py tests/test_urls.py
git commit -m "feat: esqueleto do projeto e normalizacao de URL"
```

---

### Task 2: Cores do Caelestia como CSS custom properties

**Files:**
- Create: `warpzone/scheme.py`
- Test: `tests/test_scheme.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `scheme.load_scheme(path: Path | None = None) -> dict` — `{"mode": "dark"|"light", "colours": {nomeCamelCase: "#rrggbb"}}`. Nunca levanta exceção.
  - `scheme.css_block(data: dict) -> str` — bloco `:root { ... }` com `--m3-<kebab>` e `--m3-<kebab>-rgb`.
  - `scheme.to_css_var(name: str) -> str`
  - `scheme.SCHEME_PATH: Path`

**Contexto:** o arquivo real tem 120 chaves, camelCase (`surfaceContainerHigh`), valores hex **sem** `#`, e uma chave `mode`. As variantes `-rgb` existem porque o CSS precisa de `rgba(var(--x-rgb), .55)` para o vidro — `color-mix()` seria mais elegante mas depende de suporte que não vale arriscar.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_scheme.py`:

```python
"""Leitura do scheme dinâmico do Caelestia e geração das CSS vars."""

import json

from warpzone import scheme


def _escrever(tmp_path, payload):
    caminho = tmp_path / "scheme.json"
    caminho.write_text(json.dumps(payload), encoding="utf-8")
    return caminho


def test_le_cores_e_prefixa_hex(tmp_path):
    caminho = _escrever(tmp_path, {"mode": "dark", "colours": {"primary": "c3c3ee"}})
    dados = scheme.load_scheme(caminho)
    assert dados["colours"]["primary"] == "#c3c3ee"
    assert dados["mode"] == "dark"


def test_preserva_hex_que_ja_tem_cerquilha(tmp_path):
    caminho = _escrever(tmp_path, {"colours": {"primary": "#abcdef"}})
    assert scheme.load_scheme(caminho)["colours"]["primary"] == "#abcdef"


def test_modo_desconhecido_vira_dark(tmp_path):
    caminho = _escrever(tmp_path, {"mode": "sepia", "colours": {"primary": "aabbcc"}})
    assert scheme.load_scheme(caminho)["mode"] == "dark"


def test_modo_light_e_preservado(tmp_path):
    caminho = _escrever(tmp_path, {"mode": "light", "colours": {"primary": "aabbcc"}})
    assert scheme.load_scheme(caminho)["mode"] == "light"


def test_arquivo_ausente_cai_no_fallback(tmp_path):
    dados = scheme.load_scheme(tmp_path / "nao-existe.json")
    assert dados["colours"]["primary"] == "#" + scheme.FALLBACK["primary"]
    assert dados["mode"] == "dark"


def test_json_invalido_cai_no_fallback(tmp_path):
    caminho = tmp_path / "scheme.json"
    caminho.write_text("{isso nao e json", encoding="utf-8")
    assert scheme.load_scheme(caminho)["colours"]["surface"] == "#" + scheme.FALLBACK["surface"]


def test_colours_vazio_cai_no_fallback(tmp_path):
    caminho = _escrever(tmp_path, {"mode": "dark", "colours": {}})
    assert scheme.load_scheme(caminho)["colours"]["primary"] == "#" + scheme.FALLBACK["primary"]


def test_camel_case_vira_kebab():
    assert scheme.to_css_var("surfaceContainerHigh") == "--m3-surface-container-high"
    assert scheme.to_css_var("primary") == "--m3-primary"
    assert scheme.to_css_var("onPrimaryFixedVariant") == "--m3-on-primary-fixed-variant"
    assert scheme.to_css_var("primary_paletteKeyColor") == "--m3-primary-palette-key-color"


def test_css_block_tem_hex_e_triplet():
    bloco = scheme.css_block({"mode": "dark", "colours": {"primary": "#c3c3ee"}})
    assert "--m3-primary: #c3c3ee;" in bloco
    assert "--m3-primary-rgb: 195, 195, 238;" in bloco
    assert bloco.startswith(":root {")
    assert "color-scheme: dark;" in bloco
    assert bloco.rstrip().endswith("}")


def test_css_block_ignora_triplet_de_hex_malformado():
    bloco = scheme.css_block({"mode": "dark", "colours": {"estranho": "#xyz"}})
    assert "--m3-estranho: #xyz;" in bloco
    assert "--m3-estranho-rgb" not in bloco


def test_scheme_real_da_maquina_carrega():
    """O arquivo do Caelestia existe nesta máquina; o parser tem que engolir ele."""
    if not scheme.SCHEME_PATH.exists():
        return
    dados = scheme.load_scheme()
    assert len(dados["colours"]) > 50
    assert dados["colours"]["primary"].startswith("#")
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/test_scheme.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'warpzone.scheme'`

- [ ] **Step 3: Implementar**

`warpzone/scheme.py`:

```python
"""Lê o esquema de cores dinâmico do Caelestia e o traduz para CSS."""

from __future__ import annotations

import json
import re
from pathlib import Path

SCHEME_PATH = Path.home() / ".local/state/caelestia/scheme.json"

# Usado quando o Caelestia não está instalado ou o arquivo está ilegível.
# Snapshot do esquema escuro em uso quando o app foi escrito.
FALLBACK: dict[str, str] = {
    "background": "0e0e12",
    "onBackground": "e7e4f0",
    "surface": "0e0e12",
    "surfaceContainerLow": "131318",
    "surfaceContainer": "191920",
    "surfaceContainerHigh": "1f1f26",
    "surfaceContainerHighest": "25252e",
    "onSurface": "e7e4f0",
    "onSurfaceVariant": "acaab5",
    "outline": "76747f",
    "outlineVariant": "484750",
    "primary": "c3c3ee",
    "onPrimary": "3c3d61",
    "primaryContainer": "4e4f74",
    "onPrimaryContainer": "e2e0ff",
    "secondary": "c6c4dd",
    "tertiary": "ffe2ff",
    "error": "ffb4ab",
    "onError": "690005",
    "errorContainer": "93000a",
    "onErrorContainer": "ffdad6",
    "shadow": "000000",
}

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def load_scheme(path: Path | None = None) -> dict:
    """Devolve {"mode": "dark"|"light", "colours": {...}}. Nunca levanta."""
    origem = path or SCHEME_PATH
    try:
        bruto = json.loads(origem.read_text(encoding="utf-8"))
        cores = bruto["colours"]
        if not isinstance(cores, dict) or not cores:
            raise ValueError("colours vazio ou não é objeto")
        modo = bruto.get("mode", "dark")
    except Exception:  # arquivo ausente, JSON quebrado, chave faltando
        cores, modo = FALLBACK, "dark"

    return {
        "mode": "light" if modo == "light" else "dark",
        "colours": {
            nome: _com_cerquilha(valor)
            for nome, valor in cores.items()
            if isinstance(valor, str)
        },
    }


def to_css_var(nome: str) -> str:
    """surfaceContainerHigh -> --m3-surface-container-high"""
    kebab = _CAMEL_BOUNDARY.sub("-", nome).lower().replace("_", "-")
    return f"--m3-{kebab}"


def css_block(dados: dict) -> str:
    """Bloco :root com cada cor em hex e, quando possível, em triplet RGB.

    O triplet existe para o CSS poder fazer rgba(var(--x-rgb), .55) sem
    depender de color-mix().
    """
    linhas = [f"  color-scheme: {dados['mode']};"]
    for nome, valor in sorted(dados["colours"].items()):
        var = to_css_var(nome)
        linhas.append(f"  {var}: {valor};")
        triplet = _triplet(valor)
        if triplet:
            linhas.append(f"  {var}-rgb: {triplet};")
    return ":root {\n" + "\n".join(linhas) + "\n}\n"


def _com_cerquilha(valor: str) -> str:
    return valor if valor.startswith("#") else f"#{valor}"


def _triplet(valor: str) -> str | None:
    corpo = valor.lstrip("#")
    if len(corpo) != 6:
        return None
    try:
        r, g, b = (int(corpo[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None
    return f"{r}, {g}, {b}"
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/test_scheme.py -v`
Expected: PASS — 11 passed.

- [ ] **Step 5: Conferir a saída real com os olhos**

Run:

```bash
.venv/bin/python -c "
from warpzone import scheme
d = scheme.load_scheme()
b = scheme.css_block(d)
print(b[:400]); print('...'); print('linhas:', b.count(chr(10)))
"
```

Expected: `color-scheme: dark;` seguido de pares `--m3-*` / `--m3-*-rgb`, mais de 200 linhas.

- [ ] **Step 6: Commit**

```bash
git add warpzone/scheme.py tests/test_scheme.py
git commit -m "feat: traduz o scheme do caelestia em CSS custom properties"
```

---

### Task 3: Bookmarks persistidos

**Files:**
- Create: `warpzone/bookmarks.py`
- Test: `tests/test_bookmarks.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `bookmarks.load(path: Path | None = None) -> list[dict]`
  - `bookmarks.save(itens: list[dict], path: Path | None = None) -> None`
  - `bookmarks.add(nome: str, url: str, path: Path | None = None, icone: str = "bookmark") -> list[dict]`
  - `bookmarks.remove(url: str, path: Path | None = None) -> list[dict]`
  - `bookmarks.SEED: list[dict]`, `bookmarks.CONFIG_PATH: Path`

Cada item é `{"nome": str, "url": str, "icone": str}`. `icone` é o nome de um glifo do Material Symbols Rounded.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_bookmarks.py`:

```python
"""CRUD do bookmarks.json."""

import json

from warpzone import bookmarks


def test_primeira_execucao_grava_o_seed(tmp_path):
    caminho = tmp_path / "sub" / "bookmarks.json"
    itens = bookmarks.load(caminho)
    assert itens == bookmarks.SEED
    assert caminho.exists()
    assert json.loads(caminho.read_text(encoding="utf-8")) == bookmarks.SEED


def test_seed_comeca_pelo_cockpit():
    assert bookmarks.SEED[0]["nome"] == "Cockpit"
    assert bookmarks.SEED[0]["url"] == "http://127.0.0.1:5173"


def test_le_o_que_foi_gravado(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save([{"nome": "X", "url": "https://x.dev", "icone": "public"}], caminho)
    assert bookmarks.load(caminho) == [{"nome": "X", "url": "https://x.dev", "icone": "public"}]


def test_add_anexa_e_persiste(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save([], caminho)
    itens = bookmarks.add("Jenkins", "https://jenkins.exemplo.dev", caminho, icone="build")
    assert itens[-1] == {
        "nome": "Jenkins",
        "url": "https://jenkins.exemplo.dev",
        "icone": "build",
    }
    assert bookmarks.load(caminho) == itens


def test_add_da_mesma_url_nao_duplica(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save([], caminho)
    bookmarks.add("Jenkins", "https://jenkins.exemplo.dev", caminho)
    itens = bookmarks.add("Jenkins de novo", "https://jenkins.exemplo.dev", caminho)
    assert len(itens) == 1


def test_add_sem_nome_usa_a_url(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save([], caminho)
    itens = bookmarks.add("", "https://x.dev", caminho)
    assert itens[0]["nome"] == "https://x.dev"


def test_add_sem_url_e_ignorado(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save([], caminho)
    assert bookmarks.add("Nada", "", caminho) == []


def test_remove_tira_a_url(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save(
        [
            {"nome": "A", "url": "https://a.dev", "icone": "public"},
            {"nome": "B", "url": "https://b.dev", "icone": "public"},
        ],
        caminho,
    )
    itens = bookmarks.remove("https://a.dev", caminho)
    assert [item["url"] for item in itens] == ["https://b.dev"]


def test_remove_de_url_inexistente_nao_quebra(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save([{"nome": "A", "url": "https://a.dev", "icone": "public"}], caminho)
    assert len(bookmarks.remove("https://z.dev", caminho)) == 1


def test_arquivo_corrompido_vira_bak_e_volta_ao_seed(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    caminho.write_text("isso nao e json", encoding="utf-8")
    itens = bookmarks.load(caminho)
    assert itens == bookmarks.SEED
    backup = tmp_path / "bookmarks.json.bak"
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == "isso nao e json"


def test_entradas_invalidas_sao_descartadas(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    caminho.write_text(
        json.dumps(
            [
                {"nome": "bom", "url": "https://ok.dev", "icone": "public"},
                {"nome": "sem url"},
                "string solta",
                42,
            ]
        ),
        encoding="utf-8",
    )
    itens = bookmarks.load(caminho)
    assert [item["nome"] for item in itens] == ["bom"]


def test_item_sem_icone_ganha_padrao(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    caminho.write_text(
        json.dumps([{"nome": "bom", "url": "https://ok.dev"}]), encoding="utf-8"
    )
    assert bookmarks.load(caminho)[0]["icone"] == "public"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/test_bookmarks.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'warpzone.bookmarks'`

- [ ] **Step 3: Implementar**

`warpzone/bookmarks.py`:

```python
"""Atalhos fixos do launcher, persistidos em ~/.config/warpzone."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".config/warpzone/bookmarks.json"

ICONE_PADRAO = "public"

SEED: list[dict] = [
    {"nome": "Cockpit", "url": "http://127.0.0.1:5173", "icone": "dashboard"},
    {"nome": "Cockpit API", "url": "http://127.0.0.1:8765/docs", "icone": "api"},
    {"nome": "Grafana", "url": "https://grafana.exemplo.dev", "icone": "monitoring"},
    {"nome": "Jira", "url": "https://jira.exemplo.com.br", "icone": "task_alt"},
    {"nome": "Outline", "url": "https://wiki.exemplo.com", "icone": "menu_book"},
    {"nome": "GitLab", "url": "https://gitlab.exemplo.dev", "icone": "merge"},
    {"nome": "Jenkins", "url": "https://jenkins.exemplo.dev", "icone": "build"},
]


def load(path: Path | None = None) -> list[dict]:
    """Lê os atalhos. Primeira execução grava o seed; arquivo quebrado vira .bak."""
    destino = path or CONFIG_PATH
    if not destino.exists():
        save(list(SEED), destino)
        return list(SEED)

    try:
        dados = json.loads(destino.read_text(encoding="utf-8"))
        if not isinstance(dados, list):
            raise ValueError("esperava uma lista")
    except Exception:
        destino.with_name(destino.name + ".bak").write_bytes(destino.read_bytes())
        save(list(SEED), destino)
        return list(SEED)

    return [_normalizar(item) for item in dados if _valido(item)]


def save(itens: list[dict], path: Path | None = None) -> None:
    destino = path or CONFIG_PATH
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(itens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def add(
    nome: str,
    url: str,
    path: Path | None = None,
    icone: str = "bookmark",
) -> list[dict]:
    """Anexa um atalho. URL repetida é ignorada; devolve a lista final."""
    itens = load(path)
    if not url:
        return itens
    if any(item["url"] == url for item in itens):
        return itens
    itens.append({"nome": nome or url, "url": url, "icone": icone})
    save(itens, path)
    return itens


def remove(url: str, path: Path | None = None) -> list[dict]:
    itens = [item for item in load(path) if item["url"] != url]
    save(itens, path)
    return itens


def _valido(item) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("nome"), str)
        and isinstance(item.get("url"), str)
        and bool(item["url"])
    )


def _normalizar(item: dict) -> dict:
    return {
        "nome": item["nome"],
        "url": item["url"],
        "icone": item.get("icone") or ICONE_PADRAO,
    }
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/test_bookmarks.py -v`
Expected: PASS — 12 passed.

- [ ] **Step 5: Commit**

```bash
git add warpzone/bookmarks.py tests/test_bookmarks.py
git commit -m "feat: atalhos persistidos com seed e recuperacao de arquivo corrompido"
```

---

### Task 4: Janela transparente com WebView

**Files:**
- Create: `warpzone/app.py`
- Create: `warpzone/__main__.py`

**Interfaces:**
- Consumes: `urls.normalize`, `scheme.load_scheme`.
- Produces:
  - `app.CockpitWindow(start_url: str | None = None)` — `Gtk.Window` sem decoração com `self.webview`.
  - `app.APP_ID = "warpzone"`, `app.DATA_DIR: Path`
  - `__main__.main(argv: list[str] | None = None) -> int`

Nesta task a janela ainda **não** tem launcher nem atalhos: ela abre a URL passada na linha de comando. Sem URL, carrega um HTML mínimo só para provar que a transparência funciona. O launcher entra na Task 5.

- [ ] **Step 1: Implementar a janela**

`warpzone/app.py`:

```python
"""Janela do warpzone: um WebView só, sem cromo de navegador."""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")

from gi.repository import Gdk, Gtk, WebKit2  # noqa: E402

from . import scheme  # noqa: E402

APP_ID = "warpzone"
DATA_DIR = Path.home() / ".local/share/warpzone"

# Placeholder da Task 4; a Task 5 troca por load_launcher().
_PAGINA_PROVISORIA = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  html,body{height:100%;margin:0;background:transparent;
    font:500 28px Rubik,sans-serif;color:#c3c3ee;
    display:flex;align-items:center;justify-content:center}
  div{padding:32px 44px;border-radius:28px;
    background:rgba(25,25,32,.55);border:1px solid rgba(72,71,80,.5);
    backdrop-filter:blur(18px)}
</style></head>
<body><div>warpzone</div></body></html>
"""


class CockpitWindow(Gtk.Window):
    """Janela sem decoração cujo conteúdo inteiro é um WebView."""

    def __init__(self, start_url: str | None = None) -> None:
        super().__init__(title="Warpzone")
        self.set_default_size(1280, 820)
        self.set_decorated(False)
        self._fullscreen = False
        self._tornar_transparente()

        self.scheme = scheme.load_scheme()
        self.webview = self._montar_webview()
        self.add(self.webview)

        self.connect("destroy", Gtk.main_quit)

        if start_url:
            self.webview.load_uri(start_url)
        else:
            self.webview.load_html(_PAGINA_PROVISORIA, None)

    def _tornar_transparente(self) -> None:
        """Sem visual RGBA o alfa não chega ao compositor e o blur não existe."""
        visual = self.get_screen().get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)
        self.set_app_paintable(True)

    def _montar_webview(self) -> WebKit2.WebView:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        gerenciador = WebKit2.WebsiteDataManager(
            base_data_directory=str(DATA_DIR),
            base_cache_directory=str(DATA_DIR / "cache"),
        )
        contexto = WebKit2.WebContext.new_with_website_data_manager(gerenciador)

        view = WebKit2.WebView(web_context=contexto)
        # Sem isto o WebKit pinta um fundo branco por baixo do CSS.
        view.set_background_color(Gdk.RGBA(0.0, 0.0, 0.0, 0.0))
        view.get_settings().set_property("enable-developer-extras", True)
        return view
```

- [ ] **Step 2: Implementar a entrada CLI**

`warpzone/__main__.py`:

```python
"""Entrada do warpzone: `python3 -m warpzone [URL]`."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import GLib, Gtk  # noqa: E402

from . import urls  # noqa: E402
from .app import APP_ID, CockpitWindow  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argv is None else argv
    destino = urls.normalize(argumentos[0]) if argumentos else None

    # define o app_id que o Hyprland enxerga como "class"
    GLib.set_prgname(APP_ID)

    janela = CockpitWindow(destino)
    janela.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Smoke — a janela abre e é transparente**

Run:

```bash
cd ~/Projects/warpzone
timeout 12 /usr/bin/python3 -m warpzone &
sleep 4
hyprctl clients -j | jq -r '.[] | select(.class=="warpzone") | {class, title, size, floating}'
grim /tmp/shots/task4.png
wait
```

Expected:
- `hyprctl` lista um cliente com `"class": "warpzone"` (se a class sair diferente, ajustar `GLib.set_prgname` antes de seguir).
- O screenshot mostra o cartão "warpzone" com o desktop borrado atrás, sem barra de título.

Se o fundo aparecer preto sólido em vez de borrado, o compositor não está aplicando blur na janela — anotar e seguir; a Task 8 adiciona a `windowrulev2` se necessário.

- [ ] **Step 4: Smoke — carrega uma URL real**

Run:

```bash
timeout 12 /usr/bin/python3 -m warpzone http://127.0.0.1:5173 &
sleep 5
grim /tmp/shots/task4-cockpit.png
wait
```

Expected: o claude-cockpit renderizado na janela inteira, sem nenhum elemento de navegador.

- [ ] **Step 5: Commit**

```bash
git add warpzone/app.py warpzone/__main__.py
git commit -m "feat: janela sem decoracao com webview transparente"
```

---

### Task 5: Tela de launcher

**Files:**
- Create: `warpzone/launcher_page.py`
- Create: `warpzone/launcher/index.html`
- Create: `warpzone/launcher/style.css`
- Create: `warpzone/launcher/app.js`
- Modify: `warpzone/app.py` (adiciona `show_launcher`, ponte `nav`, atalho `Ctrl+L`)
- Test: `tests/test_launcher_page.py`

**Interfaces:**
- Consumes: `scheme.css_block`, `bookmarks.load`, `urls.normalize`.
- Produces:
  - `launcher_page.render(dados_scheme: dict, itens: list[dict], base: Path = LAUNCHER_DIR) -> str`
  - `launcher_page.LAUNCHER_DIR: Path`
  - `CockpitWindow.show_launcher() -> None`

**Por que inline:** CSS e JS são costurados dentro do HTML antes do `load_html`, em vez de virem por `<link>`/`<script src>`. Isso evita depender da política de acesso a `file://` do WebKit e deixa os arquivos separados no disco para edição.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_launcher_page.py`:

```python
"""Montagem do HTML final do launcher."""

import json

from warpzone import launcher_page, scheme


def _render(itens):
    return launcher_page.render(scheme.load_scheme(), itens)


def test_nao_sobra_placeholder():
    html = _render([{"nome": "Cockpit", "url": "http://127.0.0.1:5173", "icone": "dashboard"}])
    for marcador in ("__SCHEME__", "__STYLE__", "__APP_JS__", "__BOOKMARKS__"):
        assert marcador not in html


def test_injeta_as_css_vars():
    html = _render([])
    assert "--m3-primary:" in html
    assert "--m3-surface-container-rgb:" in html


def test_injeta_os_bookmarks_como_json_parseavel():
    itens = [{"nome": "Cockpit", "url": "http://127.0.0.1:5173", "icone": "dashboard"}]
    html = _render(itens)
    inicio = html.index('id="bootstrap"')
    abre = html.index(">", inicio) + 1
    fecha = html.index("</script>", abre)
    assert json.loads(html[abre:fecha]) == itens


def test_injeta_o_css_e_o_js():
    html = _render([])
    assert ".omni" in html          # veio do style.css
    assert "__cockpitSetBookmarks" in html  # veio do app.js


def test_nome_com_html_nao_vira_marcacao():
    """Nome vem de <title> remoto; tem que entrar como dado, não como tag."""
    html = _render([{"nome": "<img src=x onerror=alert(1)>", "url": "https://x.dev", "icone": "public"}])
    assert "<img src=x onerror=alert(1)>" not in html
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/test_launcher_page.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'warpzone.launcher_page'`

- [ ] **Step 3: Escrever o HTML**

`warpzone/launcher/index.html`:

```html
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Warpzone</title>
<style>/*__SCHEME__*/</style>
<style>/*__STYLE__*/</style>
</head>
<body>
  <main class="stage">
    <header class="brand">
      <span class="material-symbols-rounded brand__icon">rocket_launch</span>
      <div class="brand__text">
        <h1>Warpzone</h1>
        <p id="clock"></p>
      </div>
    </header>

    <form class="omni" id="omni" autocomplete="off">
      <span class="material-symbols-rounded omni__icon">travel_explore</span>
      <input id="input" type="text" spellcheck="false" autofocus
             placeholder="digite uma URL ou filtre os atalhos…">
      <kbd class="omni__enter">↵</kbd>
    </form>

    <section class="cards" id="cards"></section>
    <p class="empty" id="empty" hidden>nenhum atalho com esse nome — Enter abre como URL</p>
  </main>

  <footer class="keys">
    <span><kbd>Ctrl</kbd><kbd>L</kbd>launcher</span>
    <span><kbd>Ctrl</kbd><kbd>R</kbd>recarregar</span>
    <span><kbd>Ctrl</kbd><kbd>D</kbd>fixar atalho</span>
    <span><kbd>Alt</kbd><kbd>←</kbd>voltar</span>
    <span><kbd>F11</kbd>tela cheia</span>
    <span><kbd>Ctrl</kbd><kbd>Q</kbd>sair</span>
  </footer>

<script id="bootstrap" type="application/json">/*__BOOKMARKS__*/</script>
<script>/*__APP_JS__*/</script>
</body>
</html>
```

- [ ] **Step 4: Escrever o CSS**

`warpzone/launcher/style.css`:

```css
/* Glassmorphism no padrão Caelestia. Toda cor vem das vars geradas do
   scheme.json; o alfa é aplicado sobre os triplets --m3-*-rgb. */

* { box-sizing: border-box; margin: 0; padding: 0; }

html, body { height: 100%; overflow: hidden; }

body {
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 38px clamp(24px, 6vw, 96px) 22px;
  color: var(--m3-on-surface);
  font-family: Rubik, system-ui, sans-serif;
  /* véu translúcido: dá corpo ao vidro sobre o blur do compositor */
  background:
    radial-gradient(120% 90% at 10% -10%, rgba(var(--m3-primary-rgb), .16) 0%, transparent 55%),
    radial-gradient(90% 80% at 95% 5%, rgba(var(--m3-tertiary-rgb), .12) 0%, transparent 60%),
    rgba(var(--m3-surface-rgb), .72);
}

.stage {
  flex: 1;
  width: 100%;
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 26px;
}

/* --- cabeçalho --- */
.brand { display: flex; align-items: center; gap: 16px; }
.brand__icon { font-size: 38px; color: var(--m3-primary); }
.brand h1 { font-size: 25px; font-weight: 500; letter-spacing: -.01em; }
.brand p {
  margin-top: 2px;
  font-family: 'CaskaydiaCove NF', monospace;
  font-size: 12px;
  color: var(--m3-on-surface-variant);
}

/* --- campo de URL --- */
.omni {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 17px 22px;
  border-radius: 26px;
  background: rgba(var(--m3-surface-container-rgb), .55);
  border: 1px solid rgba(var(--m3-outline-variant-rgb), .45);
  backdrop-filter: blur(18px) saturate(1.25);
  box-shadow: 0 18px 40px rgba(var(--m3-shadow-rgb), .35);
  transition: border-color .18s cubic-bezier(.2,0,0,1),
              box-shadow .18s cubic-bezier(.2,0,0,1);
}
.omni:focus-within {
  border-color: rgba(var(--m3-primary-rgb), .65);
  box-shadow: 0 22px 52px rgba(var(--m3-shadow-rgb), .45);
}
.omni.invalid {
  border-color: rgba(var(--m3-error-rgb), .85);
  animation: shake .3s cubic-bezier(.2,0,0,1);
}
@keyframes shake {
  0%,100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}
.omni__icon { font-size: 25px; color: var(--m3-primary); }
.omni input {
  flex: 1;
  border: 0; outline: 0; background: none;
  color: var(--m3-on-surface);
  font: 400 18px/1.25 Rubik, sans-serif;
}
.omni input::placeholder { color: var(--m3-on-surface-variant); opacity: .75; }
.omni__enter {
  font-family: 'CaskaydiaCove NF', monospace;
  font-size: 12px;
  padding: 3px 9px;
  border-radius: 8px;
  color: var(--m3-on-surface-variant);
  background: rgba(var(--m3-surface-container-highest-rgb), .7);
  border: 1px solid rgba(var(--m3-outline-variant-rgb), .5);
}

/* --- grid de atalhos --- */
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(152px, 1fr));
  gap: 13px;
}
.card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 9px;
  padding: 17px;
  border-radius: 22px;
  cursor: pointer;
  outline: 0;
  background: rgba(var(--m3-surface-container-rgb), .45);
  border: 1px solid rgba(var(--m3-outline-variant-rgb), .35);
  backdrop-filter: blur(14px);
  transition: transform .16s cubic-bezier(.2,0,0,1),
              background .16s cubic-bezier(.2,0,0,1),
              border-color .16s cubic-bezier(.2,0,0,1);
}
.card:hover, .card:focus-visible {
  transform: translateY(-2px);
  background: rgba(var(--m3-surface-container-high-rgb), .65);
  border-color: rgba(var(--m3-primary-rgb), .5);
}
.card__icon { font-size: 27px; color: var(--m3-primary); }
.card__name {
  font-size: 15px; font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.card__url {
  font-family: 'CaskaydiaCove NF', monospace;
  font-size: 11px;
  color: var(--m3-on-surface-variant);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.card__remove {
  position: absolute; top: 9px; right: 9px;
  font-size: 17px; opacity: 0;
  color: var(--m3-on-surface-variant);
  transition: opacity .15s, color .15s;
}
.card:hover .card__remove { opacity: .65; }
.card__remove:hover { opacity: 1; color: var(--m3-error); }

.empty { font-size: 13px; color: var(--m3-on-surface-variant); text-align: center; }

/* --- rodapé de atalhos --- */
.keys {
  display: flex; flex-wrap: wrap; gap: 16px; justify-content: center;
  font-size: 11px; color: var(--m3-on-surface-variant);
}
.keys span { display: inline-flex; align-items: center; gap: 4px; }
kbd {
  font-family: 'CaskaydiaCove NF', monospace;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 6px;
  background: rgba(var(--m3-surface-container-highest-rgb), .6);
  border: 1px solid rgba(var(--m3-outline-variant-rgb), .5);
}

/* --- toast (usado pelo Ctrl+D, injetado pelo Python) --- */
.material-symbols-rounded {
  font-family: 'Material Symbols Rounded';
  font-weight: normal; font-style: normal;
  line-height: 1; letter-spacing: normal; text-transform: none;
  display: inline-block; white-space: nowrap; direction: ltr;
  font-feature-settings: 'liga';
  -webkit-font-smoothing: antialiased;
}
```

- [ ] **Step 5: Escrever o JS**

`warpzone/launcher/app.js`:

```js
(() => {
  'use strict';

  const form  = document.getElementById('omni');
  const input = document.getElementById('input');
  const grid  = document.getElementById('cards');
  const empty = document.getElementById('empty');
  const clock = document.getElementById('clock');

  const send = (canal, carga) => {
    const handler = window.webkit
      && window.webkit.messageHandlers
      && window.webkit.messageHandlers[canal];
    if (handler) handler.postMessage(carga);
  };

  let atalhos = [];
  try {
    atalhos = JSON.parse(document.getElementById('bootstrap').textContent) || [];
  } catch (e) {
    atalhos = [];
  }

  // chamado pelo Python depois de add/remove
  window.__cockpitSetBookmarks = (itens) => {
    atalhos = Array.isArray(itens) ? itens : [];
    render();
  };

  // chamado pelo Python quando a URL digitada não é navegável
  window.__cockpitInvalid = () => {
    form.classList.remove('invalid');
    void form.offsetWidth;            // reinicia a animação
    form.classList.add('invalid');
  };

  const visiveis = () => {
    const busca = input.value.trim().toLowerCase();
    if (!busca) return atalhos;
    return atalhos.filter((a) =>
      a.nome.toLowerCase().includes(busca) || a.url.toLowerCase().includes(busca));
  };

  // Sem innerHTML: nome e URL podem vir de <title> de página remota.
  function montarCard(atalho) {
    const el = document.createElement('div');
    el.className = 'card';
    el.tabIndex = 0;

    const icone = document.createElement('span');
    icone.className = 'material-symbols-rounded card__icon';
    icone.textContent = atalho.icone || 'public';

    const nome = document.createElement('span');
    nome.className = 'card__name';
    nome.textContent = atalho.nome;

    const url = document.createElement('span');
    url.className = 'card__url';
    url.textContent = atalho.url.replace(/^https?:\/\//, '');

    const remover = document.createElement('span');
    remover.className = 'material-symbols-rounded card__remove';
    remover.textContent = 'close';
    remover.title = 'remover atalho';
    remover.addEventListener('click', (evento) => {
      evento.stopPropagation();
      send('bookmarkRemove', atalho.url);
    });

    const abrir = () => send('nav', atalho.url);
    el.addEventListener('click', abrir);
    el.addEventListener('keydown', (evento) => {
      if (evento.key === 'Enter' || evento.key === ' ') {
        evento.preventDefault();
        abrir();
      }
    });

    el.append(icone, nome, url, remover);
    return el;
  }

  function render() {
    const mostrados = visiveis();
    grid.replaceChildren(...mostrados.map(montarCard));
    empty.hidden = mostrados.length > 0 || !input.value.trim();
  }

  const pareceUrl = (texto) =>
    /^[a-z][a-z0-9+.\-]*:\/\//i.test(texto) || /\./.test(texto.split(/[/?#]/)[0]);

  form.addEventListener('submit', (evento) => {
    evento.preventDefault();
    const texto = input.value.trim();
    if (!texto) return;
    const mostrados = visiveis();
    // filtro casando com atalho ganha do palpite de URL, salvo se for URL clara
    if (mostrados.length && !pareceUrl(texto)) {
      send('nav', mostrados[0].url);
      return;
    }
    send('nav', texto);
  });

  input.addEventListener('input', render);
  input.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape') {
      input.value = '';
      render();
    }
  });

  function tique() {
    const agora = new Date();
    const data = agora.toLocaleDateString('pt-BR', {
      weekday: 'long', day: 'numeric', month: 'long',
    });
    const hora = agora.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    clock.textContent = `${data} · ${hora}`;
  }

  tique();
  setInterval(tique, 30000);
  render();
  input.focus();
})();
```

- [ ] **Step 6: Implementar o montador de página**

`warpzone/launcher_page.py`:

```python
"""Costura o HTML final do launcher com CSS, JS e dados já embutidos."""

from __future__ import annotations

import json
from pathlib import Path

from . import scheme

LAUNCHER_DIR = Path(__file__).parent / "launcher"


def render(dados_scheme: dict, itens: list[dict], base: Path = LAUNCHER_DIR) -> str:
    """HTML do launcher pronto para load_html, sem nenhum recurso externo."""
    html = (base / "index.html").read_text(encoding="utf-8")
    return (
        html.replace("/*__SCHEME__*/", scheme.css_block(dados_scheme))
        .replace("/*__STYLE__*/", (base / "style.css").read_text(encoding="utf-8"))
        .replace("/*__APP_JS__*/", (base / "app.js").read_text(encoding="utf-8"))
        .replace("/*__BOOKMARKS__*/", _json_seguro(itens))
    )


def _json_seguro(itens: list[dict]) -> str:
    """JSON que não consegue fechar a tag <script> que o contém.

    O nome do atalho pode vir do <title> de uma página remota (Ctrl+D), e
    json.dumps não escapa `<` por padrão — um título com `</script>` sairia
    da tag e viraria marcação.
    """
    return (
        json.dumps(itens, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
```

- [ ] **Step 7: Rodar os testes e confirmar que passam**

Run: `.venv/bin/pytest tests/test_launcher_page.py -v`
Expected: PASS — 5 passed.

- [ ] **Step 8: Ligar o launcher na janela**

Em `warpzone/app.py`: trocar o import, remover `_PAGINA_PROVISORIA`, e adicionar a ponte `nav` mais o `Ctrl+L`.

Import (topo do arquivo, depois do bloco `gi`):

```python
from . import bookmarks, launcher_page, scheme, urls  # noqa: E402
```

Trocar o final do `__init__`:

```python
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self._ao_teclar)

        if start_url:
            self.webview.load_uri(start_url)
        else:
            self.show_launcher()
```

Registrar os handlers dentro de `_montar_webview`, antes de criar o `WebView`:

```python
        ucm = WebKit2.UserContentManager()
        ucm.register_script_message_handler("nav")
        ucm.connect("script-message-received::nav", self._ao_navegar)

        view = WebKit2.WebView(web_context=contexto, user_content_manager=ucm)
```

Adicionar os métodos:

```python
    def show_launcher(self) -> None:
        """Carrega a tela de launcher no mesmo WebView."""
        self.webview.load_html(
            launcher_page.render(self.scheme, bookmarks.load()), None
        )

    @staticmethod
    def _texto_da_mensagem(mensagem) -> str:
        """WebKit2 4.1 entrega JavascriptResult; 6.0 entregaria JSCValue."""
        valor = mensagem.get_js_value() if hasattr(mensagem, "get_js_value") else mensagem
        return valor.to_string()

    def _ao_navegar(self, _ucm, mensagem) -> None:
        destino = urls.normalize(self._texto_da_mensagem(mensagem))
        if destino:
            self.webview.load_uri(destino)
        else:
            self._js("window.__cockpitInvalid && window.__cockpitInvalid()")

    def _js(self, script: str) -> None:
        self.webview.evaluate_javascript(script, -1)

    def _ao_teclar(self, _widget, evento) -> bool:
        ctrl = bool(evento.state & Gdk.ModifierType.CONTROL_MASK)
        tecla = Gdk.keyval_name(evento.keyval) or ""
        if ctrl and tecla.lower() == "l":
            self.show_launcher()
            return True
        return False
```

- [ ] **Step 9: Smoke — o launcher aparece e navega**

Run:

```bash
timeout 20 /usr/bin/python3 -m warpzone &
sleep 4
grim /tmp/shots/task5-launcher.png
wait
```

Expected no screenshot: cartão de busca em vidro, 7 cards (Cockpit primeiro), relógio no cabeçalho, rodapé com os atalhos, desktop borrado atrás.

Depois, à mão: clicar no card **Cockpit** deve carregar o `:5173`; `Ctrl+L` deve voltar ao launcher; digitar `xyz` e apertar Enter deve sacudir a borda em vermelho.

- [ ] **Step 10: Commit**

```bash
git add warpzone/launcher_page.py warpzone/launcher/ warpzone/app.py tests/test_launcher_page.py
git commit -m "feat: tela de launcher em glassmorphism com filtro e navegacao"
```

---

### Task 6: Atalhos completos e bookmarks vivos

**Files:**
- Modify: `warpzone/app.py`

**Interfaces:**
- Consumes: `bookmarks.add`, `bookmarks.remove`, `bookmarks.load`.
- Produces: `CockpitWindow._empurrar_bookmarks(itens)`, `CockpitWindow._toast(texto)`.

- [ ] **Step 1: Registrar os handlers de bookmark**

Em `_montar_webview`, junto do handler `nav`:

```python
        for canal in ("bookmarkAdd", "bookmarkRemove"):
            ucm.register_script_message_handler(canal)
        ucm.connect("script-message-received::bookmarkAdd", self._ao_fixar)
        ucm.connect("script-message-received::bookmarkRemove", self._ao_remover)
```

- [ ] **Step 2: Implementar os handlers e o toast**

```python
    def _ao_fixar(self, _ucm, mensagem) -> None:
        try:
            dados = json.loads(self._texto_da_mensagem(mensagem))
        except (json.JSONDecodeError, TypeError):
            return
        itens = bookmarks.add(dados.get("nome", ""), dados.get("url", ""))
        self._empurrar_bookmarks(itens)

    def _ao_remover(self, _ucm, mensagem) -> None:
        self._empurrar_bookmarks(bookmarks.remove(self._texto_da_mensagem(mensagem)))

    def _empurrar_bookmarks(self, itens: list[dict]) -> None:
        carga = json.dumps(itens, ensure_ascii=False)
        self._js(f"window.__cockpitSetBookmarks && window.__cockpitSetBookmarks({carga})")

    def _toast(self, texto: str) -> None:
        """Aviso efêmero injetado na página atual — vale também em site remoto."""
        cores = self.scheme["colours"]
        fundo = cores.get("surfaceContainerHigh", "#1f1f26")
        frente = cores.get("onSurface", "#e7e4f0")
        borda = cores.get("outlineVariant", "#484750")
        script = """(() => {
          const t = document.createElement('div');
          t.textContent = %s;
          t.style.cssText = 'position:fixed;z-index:2147483647;bottom:26px;'
            + 'left:50%%;transform:translateX(-50%%);padding:11px 20px;'
            + 'border-radius:999px;font:14px Rubik,sans-serif;'
            + 'color:%s;background:%s;border:1px solid %s;'
            + 'box-shadow:0 10px 30px rgba(0,0,0,.45)';
          document.body.appendChild(t);
          setTimeout(() => t.remove(), 2200);
        })()""" % (json.dumps(texto), frente, fundo, borda)
        self._js(script)
```

Adicionar `import json` no topo de `app.py`, junto dos outros imports da stdlib.

- [ ] **Step 3: Implementar o resto dos atalhos**

Substituir `_ao_teclar` inteiro:

```python
    def _ao_teclar(self, _widget, evento) -> bool:
        ctrl = bool(evento.state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(evento.state & Gdk.ModifierType.SHIFT_MASK)
        alt = bool(evento.state & Gdk.ModifierType.MOD1_MASK)
        tecla = (Gdk.keyval_name(evento.keyval) or "").lower()

        if ctrl and shift and tecla == "i":
            self.webview.get_inspector().show()
            return True
        if ctrl and tecla == "l":
            self.show_launcher()
            return True
        if ctrl and tecla == "r":
            self.webview.reload()
            return True
        if ctrl and tecla == "d":
            self._fixar_atual()
            return True
        if ctrl and tecla == "q":
            self.destroy()
            return True
        if alt and tecla == "left":
            self.webview.go_back()
            return True
        if alt and tecla == "right":
            self.webview.go_forward()
            return True
        if tecla == "f11":
            self._alternar_fullscreen()
            return True
        return False

    def _alternar_fullscreen(self) -> None:
        self._fullscreen = not self._fullscreen
        if self._fullscreen:
            self.fullscreen()
        else:
            self.unfullscreen()

    def _fixar_atual(self) -> None:
        """Ctrl+D na página atual. No launcher não há o que fixar."""
        uri = self.webview.get_uri() or ""
        if not uri.startswith(("http://", "https://")):
            return
        titulo = self.webview.get_title() or urlsplit(uri).netloc
        bookmarks.add(titulo, uri)
        self._toast(f"atalho fixado: {titulo}")
```

Adicionar `from urllib.parse import urlsplit` no topo.

- [ ] **Step 4: Smoke — cada atalho**

Run `timeout 60 /usr/bin/python3 -m warpzone &` e verificar à mão, um a um:

| Atalho | Esperado |
|---|---|
| clicar em Cockpit | carrega `:5173` |
| `Ctrl+D` ali | toast "atalho fixado: …" |
| `Ctrl+L` | volta ao launcher, agora com o card novo |
| `×` no card novo | some na hora, sem recarregar a página |
| `Ctrl+R` | recarrega |
| `Alt+←` | volta no histórico |
| `F11` duas vezes | entra e sai de tela cheia |
| `Ctrl+Shift+I` | abre o inspetor |
| `Ctrl+Q` | fecha a janela |

Confirmar também que o card fixado sobreviveu:

```bash
cat ~/.config/warpzone/bookmarks.json
```

- [ ] **Step 5: Commit**

```bash
git add warpzone/app.py
git commit -m "feat: atalhos de teclado, fixar/remover atalho e toast"
```

---

### Task 7: Página de erro com dica de serviço

**Files:**
- Create: `warpzone/services.py`
- Create: `warpzone/launcher/error.html`
- Modify: `warpzone/launcher_page.py` (adiciona `render_error`)
- Modify: `warpzone/app.py` (liga `load-failed`)
- Test: `tests/test_services.py`, `tests/test_error_page.py`

**Interfaces:**
- Consumes: `scheme.css_block`.
- Produces:
  - `services.hint_for(uri: str, runner=services.systemctl_state) -> str | None`
  - `services.UNIDADES: dict[str, str]`
  - `launcher_page.render_error(dados_scheme: dict, uri: str, dica: str | None, base: Path = LAUNCHER_DIR) -> str`

- [ ] **Step 1: Escrever o teste de `services.py`**

`tests/test_services.py`:

```python
"""Dica de systemctl quando um host local do cockpit não responde."""

from warpzone import services


def _parado(_unidade):
    return "inactive"


def _ativo(_unidade):
    return "active"


def _explode(_unidade):
    raise OSError("systemctl sumiu")


def test_frontend_parado_sugere_o_start():
    dica = services.hint_for("http://127.0.0.1:5173/", runner=_parado)
    assert dica == "systemctl --user start claude-cockpit-frontend.service"


def test_backend_parado_sugere_o_start():
    dica = services.hint_for("http://localhost:8765/docs", runner=_parado)
    assert dica == "systemctl --user start claude-cockpit-backend.service"


def test_servico_ativo_nao_gera_dica():
    assert services.hint_for("http://127.0.0.1:5173/", runner=_ativo) is None


def test_porta_desconhecida_nao_gera_dica():
    assert services.hint_for("http://127.0.0.1:9999/", runner=_parado) is None


def test_host_remoto_nao_gera_dica():
    assert services.hint_for("https://grafana.exemplo.dev", runner=_parado) is None


def test_uri_lixo_nao_quebra():
    assert services.hint_for("", runner=_parado) is None
    assert services.hint_for("nao://é//uri", runner=_parado) is None


def test_falha_do_systemctl_e_engolida():
    assert services.hint_for("http://127.0.0.1:5173/", runner=_explode) is None
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/test_services.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'warpzone.services'`

- [ ] **Step 3: Implementar `services.py`**

```python
"""Descobre se a falha de carregamento é só o serviço do cockpit parado."""

from __future__ import annotations

import subprocess
from urllib.parse import urlsplit

# porta -> unit systemd do usuário
UNIDADES: dict[int, str] = {
    5173: "claude-cockpit-frontend.service",
    8765: "claude-cockpit-backend.service",
}

_HOSTS_LOCAIS = frozenset({"127.0.0.1", "localhost", "0.0.0.0"})


def systemctl_state(unidade: str) -> str:
    """Estado da unit ('active', 'inactive', 'failed', ...)."""
    resultado = subprocess.run(
        ["systemctl", "--user", "is-active", unidade],
        capture_output=True,
        text=True,
        timeout=3,
    )
    return resultado.stdout.strip()


def hint_for(uri: str, runner=systemctl_state) -> str | None:
    """Comando a sugerir, ou None quando não há dica útil."""
    try:
        partes = urlsplit(uri)
        if partes.hostname not in _HOSTS_LOCAIS:
            return None
        unidade = UNIDADES.get(partes.port or 0)
    except ValueError:  # porta não numérica
        return None
    if unidade is None:
        return None

    try:
        estado = runner(unidade)
    except Exception:  # systemctl ausente, timeout, permissão
        return None

    if estado == "active":
        return None
    return f"systemctl --user start {unidade}"
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/test_services.py -v`
Expected: PASS — 7 passed.

- [ ] **Step 5: Escrever a página de erro**

`warpzone/launcher/error.html`:

```html
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>não carregou</title>
<style>/*__SCHEME__*/</style>
<style>/*__STYLE__*/</style>
<style>
  .falha {
    margin: auto;
    max-width: 560px;
    display: flex; flex-direction: column; align-items: center; gap: 16px;
    padding: 40px; text-align: center;
    border-radius: 30px;
    background: rgba(var(--m3-surface-container-rgb), .55);
    border: 1px solid rgba(var(--m3-outline-variant-rgb), .45);
    backdrop-filter: blur(18px) saturate(1.25);
    box-shadow: 0 20px 50px rgba(var(--m3-shadow-rgb), .4);
  }
  .falha__icon { font-size: 48px; color: var(--m3-error); }
  .falha h1 { font-size: 21px; font-weight: 500; }
  .falha__uri {
    font-family: 'CaskaydiaCove NF', monospace; font-size: 12px;
    color: var(--m3-on-surface-variant); word-break: break-all;
  }
  .falha__dica {
    width: 100%; margin-top: 4px; padding: 13px 16px; border-radius: 16px;
    text-align: left;
    background: rgba(var(--m3-surface-container-highest-rgb), .7);
    border: 1px solid rgba(var(--m3-outline-variant-rgb), .5);
  }
  .falha__dica p { font-size: 12px; color: var(--m3-on-surface-variant); margin-bottom: 6px; }
  .falha__dica code {
    font-family: 'CaskaydiaCove NF', monospace; font-size: 12px;
    color: var(--m3-primary); user-select: all;
  }
  .falha__acoes { display: flex; gap: 10px; margin-top: 8px; }
  .botao {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 11px 20px; border: 0; border-radius: 999px; cursor: pointer;
    font: 500 14px Rubik, sans-serif;
    background: rgba(var(--m3-surface-container-highest-rgb), .8);
    color: var(--m3-on-surface);
    transition: background .15s cubic-bezier(.2,0,0,1);
  }
  .botao:hover { background: rgba(var(--m3-surface-container-high-rgb), 1); }
  .botao--principal { background: var(--m3-primary); color: var(--m3-on-primary); }
  .botao--principal:hover { background: var(--m3-primary-dim); }
</style>
</head>
<body>
  <div class="falha">
    <span class="material-symbols-rounded falha__icon">cloud_off</span>
    <h1>não deu pra abrir essa página</h1>
    <span class="falha__uri">__URI__</span>
    __DICA__
    <div class="falha__acoes">
      <button class="botao botao--principal" id="retry" data-uri="__URI__">
        <span class="material-symbols-rounded">refresh</span>tentar de novo
      </button>
      <button class="botao" id="home">
        <span class="material-symbols-rounded">grid_view</span>voltar ao launcher
      </button>
    </div>
  </div>
<script>
  // A URI viaja por data-uri, não interpolada aqui dentro: atributo é
  // decodificado como HTML, corpo de <script> não é.
  const enviar = (canal, carga) => {
    const h = window.webkit && window.webkit.messageHandlers
      && window.webkit.messageHandlers[canal];
    if (h) h.postMessage(carga);
  };
  const botaoRetry = document.getElementById('retry');
  botaoRetry.addEventListener('click',
    () => enviar('nav', botaoRetry.dataset.uri));
  document.getElementById('home').addEventListener('click',
    () => enviar('home', ''));
</script>
</body>
</html>
```

- [ ] **Step 6: Escrever o teste de `render_error`**

`tests/test_error_page.py`:

```python
"""Página de falha de carregamento."""

from warpzone import launcher_page, scheme


def _render(uri, dica=None):
    return launcher_page.render_error(scheme.load_scheme(), uri, dica)


def test_nao_sobra_placeholder():
    html = _render("http://127.0.0.1:5173/")
    for marcador in ("__SCHEME__", "__STYLE__", "__URI__", "__DICA__"):
        assert marcador not in html


def test_mostra_a_uri():
    assert "http://127.0.0.1:5173/" in _render("http://127.0.0.1:5173/")


def test_sem_dica_nao_desenha_o_bloco():
    assert "falha__dica" not in _render("https://x.dev")


def test_com_dica_desenha_o_comando():
    html = _render("http://127.0.0.1:5173/", "systemctl --user start claude-cockpit-frontend.service")
    assert "falha__dica" in html
    assert "systemctl --user start claude-cockpit-frontend.service" in html


def test_uri_hostil_e_escapada():
    html = _render('https://x.dev/"><script>alert(1)</script>')
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
```

- [ ] **Step 7: Implementar `render_error`**

Em `warpzone/launcher_page.py`, adicionar `import html as html_mod` no topo e:

```python
def render_error(
    dados_scheme: dict,
    uri: str,
    dica: str | None,
    base: Path = LAUNCHER_DIR,
) -> str:
    """Página de falha. A URI é escapada: vem de fonte não confiável."""
    pagina = (base / "error.html").read_text(encoding="utf-8")
    bloco_dica = ""
    if dica:
        bloco_dica = (
            '<div class="falha__dica"><p>o serviço parece estar parado — suba com:</p>'
            f"<code>{html_mod.escape(dica)}</code></div>"
        )
    return (
        pagina.replace("/*__SCHEME__*/", scheme.css_block(dados_scheme))
        .replace("/*__STYLE__*/", (base / "style.css").read_text(encoding="utf-8"))
        .replace("__DICA__", bloco_dica)
        .replace("__URI__", html_mod.escape(uri, quote=True))
    )
```

A ordem importa: `__DICA__` é trocado antes de `__URI__` para que a URI escapada não seja reprocessada.

- [ ] **Step 8: Ligar na janela**

Em `warpzone/app.py`, importar `services` e, em `_montar_webview`, registrar o canal `home` e o sinal de falha:

```python
        ucm.register_script_message_handler("home")
        ucm.connect("script-message-received::home", lambda *_: self.show_launcher())
```

```python
        view.connect("load-failed", self._ao_falhar)
```

E o handler:

```python
    def _ao_falhar(self, _view, _evento, uri_falha, _erro) -> bool:
        """True impede a página de erro padrão do WebKit."""
        pagina = launcher_page.render_error(
            self.scheme, uri_falha, services.hint_for(uri_falha)
        )
        self.webview.load_html(pagina, None)
        return True
```

- [ ] **Step 9: Rodar a suíte inteira**

Run: `.venv/bin/pytest -v`
Expected: PASS — 59 passed (19 + 11 + 12 + 5 + 7 + 5).

- [ ] **Step 10: Smoke — derrubar o frontend e ver a dica**

Run:

```bash
systemctl --user stop claude-cockpit-frontend.service
timeout 20 /usr/bin/python3 -m warpzone http://127.0.0.1:5173 &
sleep 5
grim /tmp/shots/task7-erro.png
wait
systemctl --user start claude-cockpit-frontend.service
```

Expected no screenshot: cartão de erro em vidro, a URI, e o bloco com `systemctl --user start claude-cockpit-frontend.service`. Clicar em "voltar ao launcher" deve funcionar.

**Importante:** religar a unit no fim, mesmo se o smoke falhar.

- [ ] **Step 11: Commit**

```bash
git add warpzone/services.py warpzone/launcher/error.html warpzone/launcher_page.py warpzone/app.py tests/test_services.py tests/test_error_page.py
git commit -m "feat: pagina de erro com deteccao de servico parado"
```

---

### Task 8: Instalação como app desktop

**Files:**
- Create: `packaging/warpzone.desktop`
- Create: `packaging/warpzone.svg`
- Create: `packaging/install.sh`
- Create: `README.md`

**Interfaces:**
- Consumes: tudo.
- Produces: `~/.local/bin/warpzone`, entrada de menu "Warpzone".

- [ ] **Step 1: Escrever o ícone**

`packaging/warpzone.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#c3c3ee"/>
      <stop offset="1" stop-color="#8f8fd0"/>
    </linearGradient>
  </defs>
  <rect x="8" y="8" width="112" height="112" rx="30" fill="#191920"/>
  <rect x="8" y="8" width="112" height="112" rx="30" fill="none"
        stroke="url(#g)" stroke-opacity=".55" stroke-width="2"/>
  <rect x="26" y="34" width="76" height="14" rx="7" fill="url(#g)" fill-opacity=".9"/>
  <rect x="26" y="60" width="34" height="34" rx="11" fill="url(#g)" fill-opacity=".55"/>
  <rect x="68" y="60" width="34" height="34" rx="11" fill="url(#g)" fill-opacity=".3"/>
</svg>
```

- [ ] **Step 2: Escrever o `.desktop`**

`packaging/warpzone.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Warpzone
GenericName=Cockpit em janela própria
Comment=Abre o claude-cockpit numa janela sem navegador
Exec=warpzone http://127.0.0.1:5173
Icon=warpzone
Terminal=false
Categories=Development;Utility;
StartupWMClass=warpzone
Actions=launcher;

[Desktop Action launcher]
Name=Abrir o launcher
Exec=warpzone
```

- [ ] **Step 3: Escrever o instalador**

`packaging/install.sh`:

```sh
#!/usr/bin/env sh
# Instala o warpzone no ~/.local — sem tocar em nada fora da home.
set -eu

RAIZ=$(cd "$(dirname "$0")/.." && pwd)
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ICONES="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$BIN" "$APPS" "$ICONES"

cat > "$BIN/warpzone" <<EOF
#!/usr/bin/env sh
# gerado por packaging/install.sh
export PYTHONPATH="$RAIZ\${PYTHONPATH:+:\$PYTHONPATH}"
exec /usr/bin/python3 -m warpzone "\$@"
EOF
chmod +x "$BIN/warpzone"

cp "$RAIZ/packaging/warpzone.svg" "$ICONES/warpzone.svg"
cp "$RAIZ/packaging/warpzone.desktop" "$APPS/warpzone.desktop"

update-desktop-database "$APPS" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "instalado:"
echo "  $BIN/warpzone"
echo "  $APPS/warpzone.desktop"
printf '%s\n' "$PATH" | tr ':' '\n' | grep -qx "$BIN" \
  || echo "AVISO: $BIN não está no PATH"
```

- [ ] **Step 4: Instalar e verificar**

Run:

```bash
sh packaging/install.sh
command -v warpzone
timeout 12 warpzone &
sleep 4
hyprctl clients -j | jq -r '.[] | select(.class=="warpzone") | .class'
wait
```

Expected: `warpzone` resolve no PATH, a janela abre no launcher, e o `hyprctl` confirma a class `warpzone` (o que faz o `StartupWMClass` do `.desktop` casar).

- [ ] **Step 5: Regra de blur, só se necessário**

Rodar apenas se o smoke da Task 4 tiver mostrado fundo opaco em vez de borrado. Acrescentar em `~/.config/caelestia/hypr-user.conf`:

```conf
# warpzone: janela translúcida que quer o blur do compositor
windowrulev2 = opacity 1.0 override, class:^(warpzone)$
layerrule = blur, warpzone
```

Depois: `hyprctl reload` e repetir o screenshot. Se o blur já funcionava, **não mexer no arquivo**.

- [ ] **Step 6: Escrever o README**

`README.md`:

```markdown
# warpzone

Mini-browser desktop para o [claude-cockpit](../../../claude-cockpit) e outras URLs
internas. Uma janela, sem abas, sem barra de endereço — só o conteúdo, no tema
dinâmico do Caelestia.

## Instalar

```sh
sh packaging/install.sh
```

Cria `~/.local/bin/warpzone` e a entrada de menu "Warpzone".

## Usar

```sh
warpzone                      # abre o launcher
warpzone localhost:5173       # vai direto
```

| Atalho | Ação |
|---|---|
| `Ctrl+L` | volta ao launcher |
| `Ctrl+R` | recarrega |
| `Ctrl+D` | fixa a página atual como atalho |
| `Alt+←` / `Alt+→` | histórico |
| `F11` | tela cheia |
| `Ctrl+Shift+I` | inspetor |
| `Ctrl+Q` | sair |

A janela não tem decoração: mover e redimensionar é pelo Hyprland
(`Super`+arrastar), como qualquer janela flutuante.

## Arquivos

| Caminho | O quê |
|---|---|
| `~/.config/warpzone/bookmarks.json` | atalhos do launcher |
| `~/.local/share/warpzone/` | cookies e localStorage do WebKit |
| `~/.local/state/caelestia/scheme.json` | fonte das cores (só leitura) |

## Testes

```sh
uv venv --system-site-packages .venv
uv pip install --python .venv/bin/python pytest
.venv/bin/pytest
```

`app.py` não tem teste automatizado — é GTK puro, validado por smoke manual.
```

- [ ] **Step 7: Suíte completa + commit final**

```bash
.venv/bin/pytest
git add packaging/ README.md
git commit -m "feat: instalacao como app desktop com icone e entrada de menu"
```

Expected: 59 passed antes do commit.

---

## Verificação final — executada em 2026-08-04

- [x] `.venv/bin/pytest` → **61 passed** (2 testes a mais que o previsto, do fix de barra final)
- [x] `warpzone` abre o launcher com vidro e cards — `docs/launcher.png`
- [x] Blur real do compositor confirmado por screenshot (wallpaper borrado dentro da janela, nítido fora)
- [x] `hyprctl clients` confirma `class=warpzone` → `StartupWMClass` casa
- [x] `warpzone grafana.exemplo.dev` completa https e carrega o Grafana real
- [x] `Ctrl+D` fixa e persiste; `Ctrl+L`, `Ctrl+R`, `F11` (0→2→0), `Alt+←`, `Ctrl+Q` acionados via
      `hyprctl dispatch sendshortcut` e observados
- [x] Com o `claude-cockpit-frontend.service` parado, a página de erro mostra o comando certo; unit religada
- [x] `desktop-file-validate` sem avisos

## Desvios do plano (o que a execução mudou)

1. **`uv venv` precisa de `--python /usr/bin/python3`** — sem isso o uv usa um CPython próprio (3.12)
   e o `gi` some. Corrigido na Task 1, Step 2.
2. **`pythonpath = ["."]` no `pyproject.toml`** — o pacote roda da raiz sem ser instalado, e o pytest
   não colocava a raiz no `sys.path`.
3. **Dedup de atalho ignora barra final** — `Ctrl+D` em `:5173` grava `:5173/` e criava card gêmeo do
   seed. Adicionado `bookmarks._chave()` + 2 testes.
4. **`load_html` apaga o histórico do WebView** (verificado: `can_go_back()` vira False e a URI vira
   `about:blank`). Consequências reais encontradas no smoke: `Ctrl+R` no launcher **branqueava a
   janela** e `Alt+←` nunca voltava. Corrigido com estado próprio (`_no_launcher`, `_ultima_uri`) e o
   método `navegar()`; do launcher, `Alt+←` retoma o último site.
5. **`test_sem_dica_nao_desenha_o_bloco` estava errado** — checava a string `falha__dica`, que também
   existe no CSS embutido. Passou a checar a `<div>`.
6. **Regra de blur no Hyprland não foi necessária** (Task 8, Step 5 não executado): o compositor já
   borra a janela translúcida sem regra nenhuma. `hypr-user.conf` **não foi tocado**.
7. **`Categories` do `.desktop`** virou `Network;WebBrowser;` — `Development;Utility;` gerava aviso de
   duas categorias principais no `desktop-file-validate`.
8. **Véu do launcher a 55%** em vez de 72% — a 72% o blur do compositor ficava invisível.
