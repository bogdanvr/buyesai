document.addEventListener("DOMContentLoaded", () => {
    const burger = document.querySelector(".burger");
    const mobileNav = document.querySelector(".mobile-nav");

    burger.addEventListener("click", () => {
        mobileNav.classList.toggle("open");
    });
});