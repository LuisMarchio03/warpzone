(() => {
  'use strict';

  const omni  = document.getElementById('omni');
  const input = document.getElementById('input');
  const grid  = document.getElementById('cards');
  const empty = document.getElementById('empty');
  const clock = document.getElementById('clock');

  const modal      = document.getElementById('modal');
  const form       = document.getElementById('form');
  const formTitulo = document.getElementById('form-titulo');
  const fNome      = document.getElementById('f-nome');
  const fUrl       = document.getElementById('f-url');
  const fIcone     = document.getElementById('f-icone');
  const fPreview   = document.getElementById('f-preview');
  const fErro      = document.getElementById('f-erro');
  const sugestoes  = document.getElementById('sugestoes');

  // nomes de glifo do Material Symbols Rounded que cobrem a maioria dos casos
  const ICONES_SUGERIDOS = [
    'public', 'dashboard', 'terminal', 'code', 'api', 'monitoring',
    'database', 'cloud', 'bug_report', 'merge', 'build', 'rocket_launch',
    'task_alt', 'menu_book', 'description', 'mail', 'chat', 'calendar_month',
    'analytics', 'lock', 'settings', 'bolt', 'star', 'home',
  ];

  const send = (canal, carga) => {
    const handler = window.webkit
      && window.webkit.messageHandlers
      && window.webkit.messageHandlers[canal];
    if (handler) handler.postMessage(carga);
  };

  let favoritos = [];
  try {
    favoritos = JSON.parse(document.getElementById('bootstrap').textContent) || [];
  } catch (e) {
    favoritos = [];
  }

  // ---- chamados pelo Python -------------------------------------------

  window.__warpzoneSetBookmarks = (itens) => {
    favoritos = Array.isArray(itens) ? itens : [];
    render();
  };

  window.__warpzoneInvalid = () => {
    omni.classList.remove('invalid');
    void omni.offsetWidth;            // reinicia a animação
    omni.classList.add('invalid');
  };

  window.__warpzoneFormErro = (mensagem) => {
    fErro.textContent = mensagem;
    fErro.hidden = false;
  };

  window.__warpzoneFecharForm = () => fecharForm();

  // ---- cards ------------------------------------------------------------

  const visiveis = () => {
    const busca = input.value.trim().toLowerCase();
    if (!busca) return favoritos;
    return favoritos.filter((f) =>
      f.nome.toLowerCase().includes(busca) || f.url.toLowerCase().includes(busca));
  };

  function acao(icone, titulo, classe, aoClicar) {
    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = `card__acao ${classe}`;
    botao.title = titulo;
    const glifo = document.createElement('span');
    glifo.className = 'material-symbols-rounded';
    glifo.textContent = icone;
    botao.append(glifo);
    botao.addEventListener('click', (evento) => {
      evento.stopPropagation();
      aoClicar();
    });
    return botao;
  }

  // Sem innerHTML: nome e URL podem vir de <title> de página remota.
  function montarCard(favorito) {
    const el = document.createElement('div');
    el.className = 'card';
    el.tabIndex = 0;

    const icone = document.createElement('span');
    icone.className = 'material-symbols-rounded card__icon';
    icone.textContent = favorito.icone || 'public';

    const nome = document.createElement('span');
    nome.className = 'card__name';
    nome.textContent = favorito.nome;

    const url = document.createElement('span');
    url.className = 'card__url';
    url.textContent = favorito.url.replace(/^https?:\/\//, '');

    const acoes = document.createElement('div');
    acoes.className = 'card__acoes';
    acoes.append(
      acao('edit', 'editar', 'card__acao--editar', () => abrirForm(favorito)),
      acao('close', 'remover', 'card__acao--remover',
           () => send('bookmarkRemove', favorito.url)),
    );

    const abrir = () => send('nav', favorito.url);
    el.addEventListener('click', abrir);
    el.addEventListener('keydown', (evento) => {
      if (evento.key === 'Enter' || evento.key === ' ') {
        evento.preventDefault();
        abrir();
      }
    });

    el.append(icone, nome, url, acoes);
    return el;
  }

  function montarCardNovo() {
    const el = document.createElement('div');
    el.className = 'card card--novo';
    el.tabIndex = 0;
    el.title = 'adicionar favorito';

    const icone = document.createElement('span');
    icone.className = 'material-symbols-rounded card__icon';
    icone.textContent = 'add';

    const texto = document.createElement('span');
    texto.textContent = 'novo favorito';

    el.append(icone, texto);
    el.addEventListener('click', () => abrirForm(null));
    el.addEventListener('keydown', (evento) => {
      if (evento.key === 'Enter' || evento.key === ' ') {
        evento.preventDefault();
        abrirForm(null);
      }
    });
    return el;
  }

  function render() {
    const busca = input.value.trim();
    const mostrados = visiveis();
    const filhos = mostrados.map(montarCard);
    if (!busca) filhos.push(montarCardNovo());   // o "+" só atrapalha durante o filtro
    grid.replaceChildren(...filhos);

    if (busca && !mostrados.length) {
      empty.textContent = 'nenhum favorito com esse nome — Enter abre como URL';
      empty.hidden = false;
    } else if (!busca && !favoritos.length) {
      empty.textContent = 'nenhum favorito ainda — clique em + , ou aperte Ctrl+D dentro de um site';
      empty.hidden = false;
    } else {
      empty.hidden = true;
    }
  }

  // ---- formulário -------------------------------------------------------

  let editando = null;   // URL original quando é edição, null quando é novo

  function abrirForm(favorito) {
    editando = favorito ? favorito.url : null;
    formTitulo.textContent = favorito ? 'editar favorito' : 'novo favorito';
    fNome.value  = favorito ? favorito.nome : '';
    fUrl.value   = favorito ? favorito.url : '';
    fIcone.value = favorito ? (favorito.icone || 'public') : '';
    atualizarPreview();
    fErro.hidden = true;
    modal.hidden = false;
    fNome.focus();
  }

  function fecharForm() {
    modal.hidden = true;
    editando = null;
    input.focus();
  }

  function atualizarPreview() {
    fPreview.textContent = fIcone.value.trim() || 'public';
  }

  ICONES_SUGERIDOS.forEach((nome) => {
    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = 'sugestao';
    botao.title = nome;
    const glifo = document.createElement('span');
    glifo.className = 'material-symbols-rounded';
    glifo.textContent = nome;
    botao.append(glifo);
    botao.addEventListener('click', () => {
      fIcone.value = nome;
      atualizarPreview();
    });
    sugestoes.append(botao);
  });

  fIcone.addEventListener('input', atualizarPreview);
  document.getElementById('f-cancelar').addEventListener('click', fecharForm);
  modal.addEventListener('click', (evento) => {
    if (evento.target === modal) fecharForm();   // clicar fora fecha
  });

  form.addEventListener('submit', (evento) => {
    evento.preventDefault();
    fErro.hidden = true;
    const url = fUrl.value.trim();
    if (!url) {
      window.__warpzoneFormErro('a URL não pode ficar vazia');
      return;
    }
    // o Python normaliza (localhost:3000 -> http://…) e rejeita o que não for URL
    send('bookmarkSave', JSON.stringify({
      original: editando,
      nome: fNome.value.trim(),
      url,
      icone: fIcone.value.trim(),
    }));
  });

  // ---- omnibox ----------------------------------------------------------

  const pareceUrl = (texto) =>
    /^[a-z][a-z0-9+.\-]*:\/\//i.test(texto) || /\./.test(texto.split(/[/?#]/)[0]);

  omni.addEventListener('submit', (evento) => {
    evento.preventDefault();
    const texto = input.value.trim();
    if (!texto) return;
    const mostrados = visiveis();
    // filtro casando com favorito ganha do palpite de URL, salvo se for URL clara
    if (mostrados.length && !pareceUrl(texto)) {
      send('nav', mostrados[0].url);
      return;
    }
    send('nav', texto);
  });

  input.addEventListener('input', render);

  document.addEventListener('keydown', (evento) => {
    if (evento.key !== 'Escape') return;
    if (!modal.hidden) {
      fecharForm();
    } else if (input.value) {
      input.value = '';
      render();
    }
  });

  // ---- relógio ----------------------------------------------------------

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
