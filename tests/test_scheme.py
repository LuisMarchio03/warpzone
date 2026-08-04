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
