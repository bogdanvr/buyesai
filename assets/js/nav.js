document.addEventListener("DOMContentLoaded", () => {
    const burger = document.querySelector(".burger");
    const mobileNav = document.querySelector(".mobile-nav");

    if (!burger || !mobileNav) return;

    const closeMenu = () => {
        mobileNav.classList.remove("open");
    };

    burger.addEventListener("click", () => {
        mobileNav.classList.toggle("open");
    });

    mobileNav.addEventListener("click", (event) => {
        if (!event.target.closest("a")) return;
        closeMenu();
    });
});
