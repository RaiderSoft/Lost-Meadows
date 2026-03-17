// Realistic falling leaves animation
(function () {
  const leavesContainer = document.createElement("div");
  leavesContainer.id = "falling-leaves";
  leavesContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9999;
        overflow: hidden;
    `;
  document.body.appendChild(leavesContainer);

  const leafColors = [
    "rgba(127, 176, 105, 0.12)", // light green
    "rgba(74, 124, 44, 0.15)", // medium green
    "rgba(45, 80, 22, 0.15)", // dark green
    "rgba(139, 111, 71, 0.12)", // brown
    "rgba(144, 198, 149, 0.1)", // very light green
  ];

  // Track scroll state for fading
  let isScrolling = false;
  let scrollTimeout;
  let scrollOpacity = 1;

  class Leaf {
    constructor() {
      this.element = document.createElement("div");
      this.element.className = "leaf";
      this.reset();
      leavesContainer.appendChild(this.element);
    }

    reset() {
      // Random starting position
      this.x = Math.random() * window.innerWidth;
      this.y = -20;

      // Random properties for variation - smoother movement
      this.speed = 0.5 + Math.random() * 1;
      this.amplitude = 30 + Math.random() * 30;
      this.frequency = 0.005 + Math.random() * 0.01;
      this.rotation = Math.random() * 360;
      this.rotationSpeed = (Math.random() - 0.5) * 1.5;
      this.size = 6 + Math.random() * 8;
      this.color = leafColors[Math.floor(Math.random() * leafColors.length)];
      this.offsetX = 0;
      this.counter = Math.random() * 100;
      this.baseOpacity = 0.6 + Math.random() * 0.4;

      // Style the leaf
      this.element.style.cssText = `
                position: absolute;
                width: ${this.size}px;
                height: ${this.size}px;
                background: ${this.color};
                border-radius: 0 100% 0 100%;
                transform: rotate(${this.rotation}deg);
                left: ${this.x}px;
                top: ${this.y}px;
                opacity: 0;
                transition: opacity 1s ease-in-out, transform 0.1s ease-out;
                will-change: transform, opacity;
            `;

      // Fade in gradually
      setTimeout(() => {
        this.element.style.opacity = this.baseOpacity;
      }, 10);
    }

    update() {
      // Update position
      this.y += this.speed;
      this.counter += this.frequency;
      this.offsetX = Math.sin(this.counter) * this.amplitude;
      this.rotation += this.rotationSpeed;

      // Apply transform
      this.element.style.transform = `
                translate(${this.offsetX}px, 0)
                rotate(${this.rotation}deg)
            `;
      this.element.style.top = this.y + "px";

      // Adjust opacity based on scroll state
      const targetOpacity = this.baseOpacity * scrollOpacity;
      if (this.element.style.opacity !== targetOpacity.toString()) {
        this.element.style.opacity = targetOpacity;
      }

      // Reset if leaf goes off screen
      if (this.y > window.innerHeight + 20) {
        this.element.style.opacity = "0";
        setTimeout(() => this.reset(), 1000);
      }
    }

    destroy() {
      this.element.remove();
    }
  }

  // Create leaves
  const leaves = [];
  const leafCount = 10; // Number of leaves on screen - reduced for subtlety

  for (let i = 0; i < leafCount; i++) {
    setTimeout(() => {
      leaves.push(new Leaf());
    }, i * 600); // Stagger the initial creation
  }

  // Handle scroll events - fade leaves during scroll
  window.addEventListener(
    "scroll",
    () => {
      isScrolling = true;
      scrollOpacity = 0.15; // Reduce opacity significantly while scrolling

      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        isScrolling = false;
        scrollOpacity = 1; // Return to normal opacity
      }, 150);
    },
    { passive: true },
  );

  // Animation loop
  function animate() {
    leaves.forEach((leaf) => leaf.update());
    requestAnimationFrame(animate);
  }

  animate();

  // Handle window resize
  let resizeTimeout;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      leaves.forEach((leaf) => {
        if (leaf.x > window.innerWidth) {
          leaf.reset();
        }
      });
    }, 250);
  });

  // Cleanup on page unload
  window.addEventListener("beforeunload", () => {
    leaves.forEach((leaf) => leaf.destroy());
  });
})();
