const LOGO_SRC = "/app/assets/colbeef-logo.png";

/** Inserta el logo Colbeef en page-header si el módulo aún no lo tiene. */
export function enhancePageHeaderWithLogo() {
    const header = document.querySelector(".main .page-header");
    if (!header || header.querySelector("img[src*='colbeef-logo']")) return;

    const contentEl = header.querySelector(":scope > .page-header-brand")
        || header.querySelector(":scope > div:not(.page-header-actions)");

    if (!contentEl || contentEl.querySelector("img[src*='colbeef-logo']")) return;

    const brand = document.createElement("div");
    brand.className = "page-header-brand";

    const img = document.createElement("img");
    img.src = LOGO_SRC;
    img.alt = "Colbeef";
    img.width = 200;
    img.height = 72;

    const textWrap = document.createElement("div");
    if (contentEl.classList.contains("page-header-brand")) {
        const inner = contentEl.querySelector(":scope > div");
        if (inner) {
            while (inner.firstChild) textWrap.appendChild(inner.firstChild);
        }
    } else {
        while (contentEl.firstChild) textWrap.appendChild(contentEl.firstChild);
    }

    brand.appendChild(img);
    brand.appendChild(textWrap);
    contentEl.replaceWith(brand);
}
