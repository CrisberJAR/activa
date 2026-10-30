// Widget del asesor virtual: abre el chat, conversa con /api/chat y anima la página.
(() => {
  const CLAVE = "activa_chat_id";
  const $ = (id) => document.getElementById(id);
  const panel = $("chat-panel"), cuerpo = $("chat-cuerpo"), opcionesEl = $("chat-opciones");
  const form = $("chat-form"), entrada = $("chat-texto"), lanzador = $("chat-lanzador");
  const globo = $("chat-globo"), estado = $("chat-estado");

  let conversacionId = null;
  let iniciado = false;
  let ocupado = false;

  // localStorage puede fallar (modo privado): el chat funciona igual, solo no se recuerda
  const leerId = () => { try { return localStorage.getItem(CLAVE); } catch { return null; } };
  const guardarId = (id) => { try { id ? localStorage.setItem(CLAVE, id) : localStorage.removeItem(CLAVE); } catch { /* sin memoria */ } };
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
  const hora = (iso) => new Date(iso).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" });
  const bajar = () => { cuerpo.scrollTop = cuerpo.scrollHeight; };

  function burbuja(m) {
    const div = document.createElement("div");
    div.className = "burbuja-chat " + (m.rol === "bot" ? "bot" : m.rol === "cliente" ? "cliente" : "sistema");
    const texto = document.createElement("span");
    texto.textContent = m.texto; // textContent: nunca se interpreta como HTML
    div.append(texto);
    if (m.hora) {
      const t = document.createElement("small");
      t.textContent = hora(m.hora);
      div.append(t);
    }
    cuerpo.append(div);
    bajar();
  }

  function escribiendo(activo) {
    const actual = cuerpo.querySelector(".escribiendo");
    estado.textContent = activo ? "escribiendo…" : "en línea";
    if (activo && !actual) {
      const div = document.createElement("div");
      div.className = "escribiendo";
      div.innerHTML = "<span></span><span></span><span></span>";
      cuerpo.append(div);
      bajar();
    } else if (!activo && actual) {
      actual.remove();
    }
  }

  function opciones(lista) {
    opcionesEl.replaceChildren(...(lista || []).map((texto) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = texto;
      b.addEventListener("click", () => enviar(texto));
      return b;
    }));
  }

  function terminar(fin) {
    entrada.disabled = fin;
    entrada.placeholder = fin ? "Conversación finalizada · pulsa ↻ para empezar otra" : "Escribe un mensaje";
  }

  async function api(url, datos) {
    const r = await fetch(url, {
      method: datos ? "POST" : "GET",
      headers: { "Content-Type": "application/json" },
      body: datos ? JSON.stringify(datos) : undefined,
    });
    const json = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof json.detail === "string" ? json.detail : "No pudimos conectar. Intenta de nuevo.");
    return json;
  }

  // Muestra los mensajes del bot uno por uno, con "escribiendo…" entre ellos
  async function mostrar(res) {
    for (const m of res.mensajes) {
      escribiendo(true);
      await esperar(Math.min(1400, 350 + m.texto.length * 10));
      escribiendo(false);
      burbuja(m);
    }
    opciones(res.opciones);
    terminar(res.fin);
  }

  async function nueva(campanaId) {
    cuerpo.replaceChildren();
    opciones([]);
    terminar(false);
    escribiendo(true);
    try {
      const res = await api("/api/chat/iniciar", { campana_id: campanaId || null });
      conversacionId = res.conversacion_id;
      guardarId(conversacionId);
      escribiendo(false);
      await mostrar(res);
    } catch (e) {
      escribiendo(false);
      burbuja({ rol: "sistema", texto: e.message });
    }
  }

  async function abrir(campanaId) {
    panel.classList.add("abierto");
    panel.setAttribute("aria-hidden", "false");
    lanzador.setAttribute("aria-expanded", "true");
    globo.classList.remove("visible");
    if (campanaId) { // "Me interesa" en una campaña: chat nuevo sobre esa campaña
      iniciado = true;
      await nueva(campanaId);
    } else if (!iniciado) {
      iniciado = true;
      const guardado = leerId();
      if (guardado) {
        try {
          const h = await api(`/api/chat/${guardado}`);
          conversacionId = guardado;
          h.mensajes.forEach(burbuja);
          opciones(h.opciones);
          terminar(h.fin);
        } catch {
          guardarId(null);
          await nueva();
        }
      } else {
        await nueva();
      }
    }
    if (!entrada.disabled) entrada.focus();
  }

  function cerrar() {
    panel.classList.remove("abierto");
    panel.setAttribute("aria-hidden", "true");
    lanzador.setAttribute("aria-expanded", "false");
  }

  async function enviar(texto) {
    texto = texto.trim();
    if (!texto || ocupado || !conversacionId) return;
    ocupado = true;
    opciones([]);
    entrada.value = "";
    burbuja({ rol: "cliente", texto, hora: new Date().toISOString() });
    escribiendo(true);
    try {
      const res = await api("/api/chat/mensaje", { conversacion_id: conversacionId, texto });
      escribiendo(false);
      await mostrar(res);
    } catch (e) {
      escribiendo(false);
      burbuja({ rol: "sistema", texto: e.message });
    }
    ocupado = false;
  }

  // ---------- Eventos ----------
  lanzador.addEventListener("click", () => (panel.classList.contains("abierto") ? cerrar() : abrir()));
  $("chat-cerrar").addEventListener("click", cerrar);
  $("chat-reiniciar").addEventListener("click", () => { iniciado = true; nueva(); });
  $("chat-globo-cerrar").addEventListener("click", () => globo.classList.remove("visible"));
  form.addEventListener("submit", (e) => { e.preventDefault(); enviar(entrada.value); });
  document.querySelectorAll("[data-chat]").forEach((b) =>
    b.addEventListener("click", () => abrir(Number(b.dataset.campana) || null)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrar(); });

  // Globo de saludo a los pocos segundos
  setTimeout(() => { if (!panel.classList.contains("abierto")) globo.classList.add("visible"); }, 2500);
  if (new URLSearchParams(location.search).get("chat")) abrir();

  // Aparición de secciones al hacer scroll y sombra de la barra
  const observador = new IntersectionObserver((entradas) => entradas.forEach((en) => {
    if (en.isIntersecting) { en.target.classList.add("visible"); observador.unobserve(en.target); }
  }), { threshold: 0.12 });
  document.querySelectorAll(".revelar").forEach((el) => observador.observe(el));
  const barra = $("barra");
  window.addEventListener("scroll", () => barra.classList.toggle("con-sombra", window.scrollY > 10), { passive: true });
})();
