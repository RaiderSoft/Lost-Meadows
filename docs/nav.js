// Enhanced navigation with scroll effects and mobile toggle
(function () {
  const header = document.querySelector("header");
  const nav = document.querySelector("nav");
  const navToggle = document.querySelector(".nav-toggle");

  window.addEventListener("scroll", () => {
    const currentScroll = window.pageYOffset;
    if (currentScroll > 50) {
      header.classList.add("scrolled");
    } else {
      header.classList.remove("scrolled");
    }
  });

  if (navToggle && nav) {
    navToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = nav.classList.toggle("nav-open");
      navToggle.setAttribute("aria-expanded", open);
    });

    nav.querySelectorAll(".nav-menu a").forEach((link) => {
      link.addEventListener("click", () => {
        nav.classList.remove("nav-open");
        navToggle.setAttribute("aria-expanded", "false");
      });
    });

    document.addEventListener("click", (e) => {
      if (!nav.contains(e.target)) {
        nav.classList.remove("nav-open");
        navToggle.setAttribute("aria-expanded", "false");
      }
    });
  }
})();
