(() => {
    function fallback(image) {
        if (!image.dataset.fallback || image.dataset.fallbackUsed) return;
        image.dataset.fallbackUsed = "true";
        image.src = image.dataset.fallback;
        image.closest("figure").querySelector("figcaption").textContent = "Imagen ilustrativa";
    }
    document.addEventListener("error", event => {
        if (event.target instanceof HTMLImageElement) fallback(event.target);
    }, true);
    document.querySelectorAll("img[data-fallback]").forEach(image => {
        if (image.complete && !image.naturalWidth) fallback(image);
    });

    const reader = document.querySelector("[data-news-reader]");
    if (!reader) return;
    const grid = reader.querySelector("#article-grid");
    const more = reader.querySelector("[data-load-more]");
    const status = reader.querySelector("[data-reader-status]");
    const positionKey = () => `news:${reader.dataset.user}:${location.pathname}${location.search}`;
    const remember = () => {
        try { sessionStorage.setItem(positionKey(), String(window.scrollY)); } catch (_) { /* Storage may be disabled. */ }
    };
    window.addEventListener("pagehide", remember);
    document.addEventListener("click", event => {
        if (event.target.closest("a")) remember();
    });
    let restored;
    try { restored = sessionStorage.getItem(positionKey()); } catch (_) { /* Use native scroll restoration. */ }
    if (restored !== null && restored !== undefined && performance.getEntriesByType("navigation")[0]?.type !== "back_forward") {
        requestAnimationFrame(() => window.scrollTo({top: Number(restored), behavior: "instant"}));
    }

    async function json(url, options = {}) {
        const response = await fetch(url, {...options, headers: {Accept: "application/json"}});
        if (!response.ok || !response.headers.get("Content-Type")?.includes("application/json")) {
            throw new Error("No se pudo completar la solicitud. Probá de nuevo o recargá la página.");
        }
        return response.json();
    }

    more.addEventListener("click", async event => {
        if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        if (more.getAttribute("aria-disabled") === "true") return;
        more.setAttribute("aria-disabled", "true");
        grid.setAttribute("aria-busy", "true");
        more.textContent = "Cargando…";
        status.textContent = "";
        try {
            const data = await json(more.href);
            const scrollPosition = window.scrollY;
            const fragment = document.createElement("template");
            fragment.innerHTML = data.html;
            let firstAdded;
            fragment.content.querySelectorAll("[data-article-id]").forEach(card => {
                if (!document.getElementById(card.id)) {
                    firstAdded ||= card;
                    grid.append(card);
                }
            });
            more.hidden = !data.next_url;
            if (data.next_url) more.href = data.next_url;
            const url = new URL(location.href);
            url.searchParams.delete("cursor");
            url.searchParams.set("visible", grid.children.length);
            history.replaceState(null, "", url);
            reader.querySelectorAll('input[name="next"]').forEach(input => input.value = url.pathname + url.search);
            remember();
            status.textContent = data.next_url ? "Se agregaron más noticias." : "Ya viste todas las noticias disponibles.";
            if (event.detail === 0 && firstAdded) firstAdded.querySelector("h2 a").focus({preventScroll: true});
            else if (more.hidden) status.focus({preventScroll: true});
            more.textContent = "Ver más";
            window.scrollTo({top: scrollPosition, behavior: "instant"});
        } catch (error) {
            status.textContent = error.message;
            more.textContent = "Reintentar";
        } finally {
            more.removeAttribute("aria-disabled");
            grid.removeAttribute("aria-busy");
        }
    });

    reader.addEventListener("submit", async event => {
        const form = event.target.closest(".save-form");
        if (!form) return;
        event.preventDefault();
        const button = form.querySelector("button");
        button.disabled = true;
        try {
            const data = await json(form.action, {method: "POST", body: new FormData(form)});
            form.action = data.action;
            button.classList.toggle("is-saved", data.saved);
            const label = data.saved ? "Quitar de guardadas" : "Guardar noticia";
            button.title = label;
            button.setAttribute("aria-label", `${label}: ${form.closest("article").querySelector("h2").textContent}`);
            status.textContent = data.saved ? "Noticia guardada." : "Noticia quitada de tus guardadas.";
        } catch (error) {
            status.textContent = error.message;
        } finally {
            button.disabled = false;
        }
    });
})();
