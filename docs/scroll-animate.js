// Very subtle scroll animations
(function () {
  const observerOptions = {
    threshold: 0.15,
    rootMargin: "0px 0px -50px 0px",
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
      }
    });
  }, observerOptions);

  // Observe all sections
  const sections = document.querySelectorAll(".section");
  sections.forEach((section) => {
    section.classList.add("fade-in-section");
    observer.observe(section);
  });
})();
