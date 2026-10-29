
document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector(".navbar-toggle");
    const menu = document.querySelector(".navbar-menu");

    if (!toggle || !menu) return;

    toggle.addEventListener("click", () => {
        const isOpen = menu.classList.toggle("is-open");

        toggle.setAttribute("aria-expanded", String(isOpen));
        toggle.setAttribute(
            "aria-label",
            isOpen ? "Tutup menu navigasi" : "Buka menu navigasi"
        );
    });

    menu.querySelectorAll(".navbar-links a").forEach((link) => {
        link.addEventListener("click", () => {
            menu.classList.remove("is-open");
            toggle.setAttribute("aria-expanded", "false");
            toggle.setAttribute("aria-label", "Buka menu navigasi");
        });
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth > 900) {
            menu.classList.remove("is-open");
            toggle.setAttribute("aria-expanded", "false");
            toggle.setAttribute("aria-label", "Buka menu navigasi");
        }
    });
    
    // Tutup menu dengan tombol Escape
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && menu.classList.contains("is-open")) {
            menu.classList.remove("is-open");
            toggle.setAttribute("aria-expanded", "false");
            toggle.setAttribute("aria-label", "Buka menu navigasi");
            toggle.focus();
        }
    });

    // Tutup menu saat klik di luar navbar
    document.addEventListener("click", (event) => {
        if (
            menu.classList.contains("is-open") &&
            !event.target.closest(".navbar-container")
        ) {
            menu.classList.remove("is-open");
            toggle.setAttribute("aria-expanded", "false");
            toggle.setAttribute("aria-label", "Buka menu navigasi");
        }
    });

});
