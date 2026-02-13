document.addEventListener("DOMContentLoaded", () => {
    const burger = document.querySelector(".burger");
    const mobileNav = document.querySelector(".mobile-nav");

    if (!burger || !mobileNav) return;

    burger.addEventListener("click", () => {
        mobileNav.classList.toggle("open");
    });
});
