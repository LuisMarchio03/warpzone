"""Janela do warpzone: um WebView só, sem cromo de navegador."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")

from gi.repository import Gdk, Gtk, WebKit2  # noqa: E402

from . import bookmarks, launcher_page, scheme, services, session, urls  # noqa: E402

APP_ID = "warpzone"
DATA_DIR = Path.home() / ".local/share/warpzone"


class CockpitWindow(Gtk.Window):
    """Janela sem decoração cujo conteúdo inteiro é um WebView."""

    def __init__(self, start_url: str | None = None) -> None:
        super().__init__(title="Warpzone")
        self.set_default_size(1280, 820)
        self.set_decorated(False)
        self._fullscreen = False
        # load_html apaga o histórico do WebView e deixa a URI como
        # about:blank, então o estado "estou no launcher" e o "último site"
        # são rastreados aqui em vez de perguntados ao WebKit.
        self._no_launcher = False
        self._ultima_uri: str | None = None
        self._tornar_transparente()

        self.scheme = scheme.load_scheme()
        self.webview = self._montar_webview()
        self.add(self.webview)

        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self._ao_teclar)

        if start_url:
            self.navegar(start_url)
        else:
            self.show_launcher()

    def _tornar_transparente(self) -> None:
        """Sem visual RGBA o alfa não chega ao compositor e o blur não existe."""
        visual = self.get_screen().get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)
        self.set_app_paintable(True)

    def _montar_webview(self) -> WebKit2.WebView:
        gerenciador = WebKit2.WebsiteDataManager(
            base_data_directory=str(DATA_DIR),
            base_cache_directory=str(DATA_DIR / "cache"),
        )
        # o base_data_directory acima não cobre cookies: sem esta linha o login
        # morre junto com a janela
        session.enable_persistence(gerenciador, DATA_DIR)
        contexto = WebKit2.WebContext.new_with_website_data_manager(gerenciador)

        ucm = WebKit2.UserContentManager()
        for canal in ("nav", "home", "bookmarkSave", "bookmarkRemove"):
            ucm.register_script_message_handler(canal)
        ucm.connect("script-message-received::nav", self._ao_navegar)
        ucm.connect("script-message-received::home", lambda *_: self.show_launcher())
        ucm.connect("script-message-received::bookmarkSave", self._ao_salvar_favorito)
        ucm.connect("script-message-received::bookmarkRemove", self._ao_remover)

        view = WebKit2.WebView(web_context=contexto, user_content_manager=ucm)
        # Sem isto o WebKit pinta um fundo branco por baixo do CSS.
        view.set_background_color(Gdk.RGBA(0.0, 0.0, 0.0, 0.0))
        view.get_settings().set_property("enable-developer-extras", True)
        view.connect("load-failed", self._ao_falhar)
        return view

    def _ao_falhar(self, _view, _evento, uri_falha, _erro) -> bool:
        """True impede a página de erro padrão do WebKit."""
        pagina = launcher_page.render_error(
            self.scheme, uri_falha, services.hint_for(uri_falha)
        )
        self.webview.load_html(pagina, None)
        return True

    # -- launcher e ponte com o JS --------------------------------------

    def show_launcher(self) -> None:
        """Carrega a tela de launcher no mesmo WebView."""
        uri = self.webview.get_uri()
        if uri and uri.startswith(("http://", "https://")):
            self._ultima_uri = uri
        self._no_launcher = True
        self.webview.load_html(
            launcher_page.render(self.scheme, bookmarks.load()), None
        )

    def navegar(self, uri: str) -> None:
        """Sai do launcher para um site."""
        self._no_launcher = False
        self.webview.load_uri(uri)

    @staticmethod
    def _texto_da_mensagem(mensagem) -> str:
        """WebKit2 4.1 entrega JavascriptResult; 6.0 entregaria JSCValue."""
        valor = mensagem.get_js_value() if hasattr(mensagem, "get_js_value") else mensagem
        return valor.to_string()

    def _ao_navegar(self, _ucm, mensagem) -> None:
        destino = urls.normalize(self._texto_da_mensagem(mensagem))
        if destino:
            self.navegar(destino)
        else:
            self._js("window.__warpzoneInvalid && window.__warpzoneInvalid()")

    def _js(self, script: str) -> None:
        self.webview.evaluate_javascript(script, -1)

    # -- favoritos ------------------------------------------------------

    def _ao_salvar_favorito(self, _ucm, mensagem) -> None:
        """Formulário do launcher: cria quando `original` é nulo, senão edita."""
        try:
            dados = json.loads(self._texto_da_mensagem(mensagem))
        except (json.JSONDecodeError, TypeError):
            return

        destino = urls.normalize(dados.get("url", ""))
        if not destino:
            self._js(
                "window.__warpzoneFormErro && "
                "window.__warpzoneFormErro('isso não parece uma URL')"
            )
            return

        nome = dados.get("nome") or ""
        icone = dados.get("icone") or bookmarks.ICONE_PADRAO
        original = dados.get("original")

        if original:
            itens = bookmarks.update(original, nome, destino, icone)
        else:
            itens = bookmarks.add(nome, destino, icone=icone)

        self._empurrar_bookmarks(itens)
        self._js("window.__warpzoneFecharForm && window.__warpzoneFecharForm()")

    def _ao_remover(self, _ucm, mensagem) -> None:
        self._empurrar_bookmarks(bookmarks.remove(self._texto_da_mensagem(mensagem)))

    def _empurrar_bookmarks(self, itens: list[dict]) -> None:
        carga = json.dumps(itens, ensure_ascii=False)
        self._js(f"window.__warpzoneSetBookmarks && window.__warpzoneSetBookmarks({carga})")

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

    def _fixar_atual(self) -> None:
        """Ctrl+D na página atual. No launcher não há o que fixar."""
        uri = self.webview.get_uri() or ""
        if not uri.startswith(("http://", "https://")):
            return
        titulo = self.webview.get_title() or urlsplit(uri).netloc
        bookmarks.add(titulo, uri)
        self._toast(f"atalho fixado: {titulo}")

    # -- teclado --------------------------------------------------------

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
            # recarregar o launcher pelo WebView traria about:blank de volta
            self.show_launcher() if self._no_launcher else self.webview.reload()
            return True
        if ctrl and tecla == "d":
            self._fixar_atual()
            return True
        if ctrl and tecla == "q":
            self.destroy()
            return True
        if alt and tecla == "left":
            # do launcher, "voltar" é retomar o site que estava aberto
            if self._no_launcher and self._ultima_uri:
                self.navegar(self._ultima_uri)
            else:
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
