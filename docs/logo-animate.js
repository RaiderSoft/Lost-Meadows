// Animated Logo - SVG Mountain Pieces Assembly
document.addEventListener("DOMContentLoaded", function () {
  const logo = document.querySelector(".logo");
  const logoIcon = document.querySelector(".logo-icon");

  if (!logo || !logoIcon) {
    console.log("Logo or icon not found");
    return;
  }

  console.log("Starting logo animation");

  // Hide icon initially for animation
  logoIcon.style.opacity = "0";
  logoIcon.style.transition = "opacity 0.5s ease";

  // Hide and position text at icon location initially
  logo.style.opacity = "0";
  logo.style.transform = "translateX(-30px)";
  logo.style.transition = "all 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)";

  // Get icon position
  const iconRect = logoIcon.getBoundingClientRect();

  // Create container for pieces
  const container = document.createElement("div");
  container.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 10000;
    `;
  document.body.appendChild(container);

  // Define the actual mountain SVG layers from favicon
  const mountainLayers = [
    {
      // Sky/background gradient
      type: "rect",
      color: "url(#skyGradient)",
      startX: Math.random() * 400 - 200,
      startY: -300,
      delay: 0,
    },
    {
      // Back mountain (darkest)
      path: "M 0 60 L 30 25 L 50 40 L 70 20 L 100 50 L 100 100 L 0 100 Z",
      color: "#2d5016",
      startX: -400,
      startY: Math.random() * 200 - 100,
      delay: 0.2,
    },
    {
      // Middle mountain
      path: "M 0 70 L 25 45 L 50 55 L 75 35 L 100 65 L 100 100 L 0 100 Z",
      color: "#4a7c2c",
      startX: 400,
      startY: Math.random() * 200 - 100,
      delay: 0.4,
    },
    {
      // Meadow/grass area
      path: "M 0 80 L 15 75 L 30 78 L 45 73 L 60 77 L 75 74 L 90 79 L 100 76 L 100 100 L 0 100 Z",
      color: "#7fb069",
      startX: Math.random() * 400 - 200,
      startY: 400,
      delay: 0.6,
    },
  ];

  const pieces = [];

  // Create SVG container for each piece
  mountainLayers.forEach((layer, index) => {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 100 100");
    svg.style.cssText = `
            position: fixed;
            width: 40px;
            height: 40px;
            left: ${iconRect.left + layer.startX}px;
            top: ${iconRect.top + layer.startY}px;
            opacity: 0;
            transition: all 1.5s cubic-bezier(0.34, 1.56, 0.64, 1);
            transition-delay: ${layer.delay}s;
            will-change: transform, opacity;
            transform: rotate(${Math.random() * 360 - 180}deg) scale(0.5);
        `;

    // Add gradient definition for sky if needed
    if (layer.type === "rect") {
      const defs = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "defs",
      );
      const gradient = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "linearGradient",
      );
      gradient.setAttribute("id", "skyGradient");
      gradient.setAttribute("x1", "0%");
      gradient.setAttribute("y1", "0%");
      gradient.setAttribute("x2", "0%");
      gradient.setAttribute("y2", "100%");

      const stop1 = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "stop",
      );
      stop1.setAttribute("offset", "0%");
      stop1.setAttribute("style", "stop-color:#90c695;stop-opacity:1");

      const stop2 = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "stop",
      );
      stop2.setAttribute("offset", "100%");
      stop2.setAttribute("style", "stop-color:#7fb069;stop-opacity:1");

      gradient.appendChild(stop1);
      gradient.appendChild(stop2);
      defs.appendChild(gradient);
      svg.appendChild(defs);

      const rect = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "rect",
      );
      rect.setAttribute("width", "100");
      rect.setAttribute("height", "100");
      rect.setAttribute("fill", "url(#skyGradient)");
      svg.appendChild(rect);
    } else {
      // Create path element
      const path = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "path",
      );
      path.setAttribute("d", layer.path);
      path.setAttribute("fill", layer.color);
      svg.appendChild(path);
    }

    container.appendChild(svg);
    pieces.push({
      element: svg,
      finalX: iconRect.left,
      finalY: iconRect.top,
    });
  });

  // Trigger animation
  setTimeout(() => {
    pieces.forEach(({ element, finalX, finalY }) => {
      element.style.left = finalX + "px";
      element.style.top = finalY + "px";
      element.style.transform = "rotate(0deg) scale(1)";
      element.style.opacity = "1";
    });
  }, 100);

  // After pieces assemble, fade in icon and remove pieces
  const totalAnimationTime = 1500 + mountainLayers.length * 200;
  setTimeout(() => {
    // Fade in the actual icon
    logoIcon.style.opacity = "1";

    // Fade out pieces
    pieces.forEach(({ element }, i) => {
      setTimeout(() => {
        element.style.transition = "opacity 0.5s ease";
        element.style.opacity = "0";
      }, i * 100);
    });

    // Slide logo text out from the icon
    setTimeout(() => {
      logo.style.opacity = "1";
      logo.style.transform = "translateX(0)";
    }, 400);

    // Clean up
    setTimeout(() => {
      container.remove();
    }, 1000);
  }, totalAnimationTime);
});
