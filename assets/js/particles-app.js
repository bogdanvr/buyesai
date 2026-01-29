// particles-app.js

document.addEventListener('DOMContentLoaded', function () {
  // даём чуть времени на верстку
  setTimeout(function () {
      // проверяем, что библиотека подключена и контейнер есть
      if (typeof window.particlesJS === 'undefined') return;

      var el = document.getElementById('particles-js');
      if (!el) return;

      particlesJS('particles-js', {
          particles: {
              number: {
                  value: 70,
                  density: {
                      enable: true,
                      value_area: 800
                  }
              },
              color: {
                  value: "#fff"
              },
              shape: {
                  type: "circle"
              },
              opacity: {
                  value: 0.3,
                  random: true
              },
              size: {
                  value: 2,
                  random: true
              },
              line_linked: {
                  enable: true,
                  distance: 80,
                  color: "#C14812",
                  opacity: 0.15,
                  width: 1
              },
              move: {
                  enable: true,
                  speed: 6.2,
                  direction: "none",
                  random: false,
                  straight: false,
                  out_mode: "out",
                  bounce: false
              }
          },
          interactivity: {
              detect_on: "canvas",
              events: {
                  onhover: {
                      enable: true,
                      mode: "repulse"
                  },
                  onclick: {
                      enable: false
                  },
                  resize: true
              },
              modes: {
                  repulse: {
                      distance: 90,
                      duration: 0.4
                  }
              }
          },
          retina_detect: true
      });
  }, 100);
});
