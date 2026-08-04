"""CRUD do bookmarks.json."""

import json

from warpzone import bookmarks


def test_primeira_execucao_grava_o_seed(tmp_path):
    caminho = tmp_path / "sub" / "bookmarks.json"
    itens = bookmarks.load(caminho)
    assert itens == bookmarks.SEED
    assert caminho.exists()
    assert json.loads(caminho.read_text(encoding="utf-8")) == bookmarks.SEED


def test_seed_comeca_vazio():
    """Quem escolhe os favoritos é o usuário, na tela — não o app."""
    assert bookmarks.SEED == []


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


def test_add_ignora_barra_final_ao_deduplicar(tmp_path):
    """Ctrl+D numa página traz a URL com barra; não pode virar card gêmeo."""
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save([{"nome": "Cockpit", "url": "http://127.0.0.1:5173", "icone": "dashboard"}], caminho)
    itens = bookmarks.add("Claude Cockpit", "http://127.0.0.1:5173/", caminho)
    assert len(itens) == 1


def test_remove_ignora_barra_final(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save([{"nome": "Cockpit", "url": "http://127.0.0.1:5173/", "icone": "dashboard"}], caminho)
    assert bookmarks.remove("http://127.0.0.1:5173", caminho) == []


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


def test_update_troca_os_campos_preservando_a_posicao(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save(
        [
            {"nome": "A", "url": "https://a.dev", "icone": "public"},
            {"nome": "B", "url": "https://b.dev", "icone": "public"},
            {"nome": "C", "url": "https://c.dev", "icone": "public"},
        ],
        caminho,
    )
    itens = bookmarks.update("https://b.dev", "Bê", "https://novo.dev", "build", caminho)
    assert itens[1] == {"nome": "Bê", "url": "https://novo.dev", "icone": "build"}
    assert [item["nome"] for item in itens] == ["A", "Bê", "C"]
    assert bookmarks.load(caminho) == itens


def test_update_de_url_inexistente_nao_cria_nada(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save([{"nome": "A", "url": "https://a.dev", "icone": "public"}], caminho)
    itens = bookmarks.update("https://z.dev", "Z", "https://z2.dev", "public", caminho)
    assert itens == [{"nome": "A", "url": "https://a.dev", "icone": "public"}]


def test_update_sem_nome_usa_a_url(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save([{"nome": "A", "url": "https://a.dev", "icone": "public"}], caminho)
    itens = bookmarks.update("https://a.dev", "", "https://a.dev", "public", caminho)
    assert itens[0]["nome"] == "https://a.dev"


def test_update_ignora_barra_final_ao_localizar(tmp_path):
    caminho = tmp_path / "bookmarks.json"
    bookmarks.save([{"nome": "A", "url": "https://a.dev/", "icone": "public"}], caminho)
    itens = bookmarks.update("https://a.dev", "A2", "https://a.dev", "star", caminho)
    assert itens[0]["nome"] == "A2"


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
