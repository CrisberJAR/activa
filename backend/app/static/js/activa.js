// ACTIVA 360°: tema claro/oscuro, tablas con búsqueda y paginación, confirmaciones (sin librerías)
(function () {
  "use strict";

  // ---------- Tema ----------
  var boton = document.getElementById("cambiarTema");
  function pintarIcono() {
    if (!boton) return;
    var oscuro = document.documentElement.getAttribute("data-bs-theme") === "dark";
    boton.innerHTML = oscuro ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
  }
  if (boton) {
    pintarIcono();
    boton.addEventListener("click", function () {
      var nuevo = document.documentElement.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-bs-theme", nuevo);
      try { localStorage.setItem("activa-tema", nuevo); } catch (e) { /* sin almacenamiento */ }
      pintarIcono();
      document.dispatchEvent(new CustomEvent("activa:tema", { detail: nuevo }));
    });
  }

  // ---------- Tablas: <table data-tabla data-por-pagina="15"> ----------
  function normalizar(t) {
    return (t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }

  document.querySelectorAll("table[data-tabla]").forEach(function (tabla, n) {
    var cuerpo = tabla.tBodies[0];
    if (!cuerpo) return;
    var filas = Array.prototype.slice.call(cuerpo.rows);
    var porPagina = parseInt(tabla.getAttribute("data-por-pagina") || "15", 10);
    var pagina = 1;
    var visibles = filas;

    var barra = document.createElement("div");
    barra.className = "d-flex flex-wrap gap-2 align-items-center mb-2 no-imprimir";
    var id = "buscar-tabla-" + n;
    barra.innerHTML =
      '<label class="visually-hidden" for="' + id + '">Buscar en la tabla</label>' +
      '<div class="input-group input-group-sm" style="max-width: 320px">' +
      '<span class="input-group-text"><i class="bi bi-search"></i></span>' +
      '<input type="search" class="form-control" id="' + id + '" placeholder="Buscar…"></div>' +
      '<span class="small text-body-secondary ms-auto" aria-live="polite"></span>';
    var contenedor = tabla.closest(".table-responsive") || tabla;
    contenedor.parentNode.insertBefore(barra, contenedor);
    var buscador = barra.querySelector("input");
    var contador = barra.querySelector("span[aria-live]");

    var nav = document.createElement("nav");
    nav.setAttribute("aria-label", "Paginación de la tabla");
    nav.className = "no-imprimir";
    contenedor.parentNode.insertBefore(nav, contenedor.nextSibling);

    function pintar() {
      var total = visibles.length;
      var paginas = Math.max(1, Math.ceil(total / porPagina));
      if (pagina > paginas) pagina = paginas;
      var desde = (pagina - 1) * porPagina;
      filas.forEach(function (f) { f.style.display = "none"; });
      visibles.slice(desde, desde + porPagina).forEach(function (f) { f.style.display = ""; });
      contador.textContent = total === filas.length ? total + " registros" : total + " de " + filas.length + " registros";
      if (paginas <= 1) { nav.innerHTML = ""; return; }
      var html = '<ul class="pagination pagination-sm mt-2 flex-wrap">';
      for (var p = 1; p <= paginas; p++) {
        html += '<li class="page-item' + (p === pagina ? " active" : "") + '"><button type="button" class="page-link" data-p="' + p + '"' +
          (p === pagina ? ' aria-current="page"' : "") + ">" + p + "</button></li>";
      }
      nav.innerHTML = html + "</ul>";
    }

    nav.addEventListener("click", function (e) {
      var b = e.target.closest("[data-p]");
      if (!b) return;
      pagina = parseInt(b.getAttribute("data-p"), 10);
      pintar();
    });
    buscador.addEventListener("input", function () {
      var q = normalizar(buscador.value.trim());
      visibles = q ? filas.filter(function (f) { return normalizar(f.textContent).indexOf(q) !== -1; }) : filas;
      pagina = 1;
      pintar();
    });
    pintar();
  });

  // ---------- Confirmación: <form data-confirmar="¿Seguro?"> ----------
  document.querySelectorAll("form[data-confirmar]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (!window.confirm(f.getAttribute("data-confirmar"))) e.preventDefault();
    });
  });

  // ---------- Botón que se desactiva al enviar (evita dobles envíos) ----------
  document.querySelectorAll("form[data-una-vez]").forEach(function (f) {
    f.addEventListener("submit", function () {
      var b = f.querySelector("button[type=submit]");
      if (b) { b.disabled = true; b.insertAdjacentHTML("afterbegin", '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>'); }
    });
  });
})();
