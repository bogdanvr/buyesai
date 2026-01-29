document.addEventListener('DOMContentLoaded', () => {
    // 1) Берём именно элементы с data-tilt
    const els = document.querySelectorAll('[data-tilt]');
    if (!els.length) return;
  
    // 2) Инициализируем, если не инициализировано
    VanillaTilt.init(els, {
      // можно задать тут — перекроет data-* приоритетом настроек
      max: 8,
      gyroscope: false,
      glare: false
    });
  
    // 3) Запускаем автодвижение для каждого
    els.forEach(el => startAutoTiltSimple(el, { radiusRatio: 0.28, rpm: 20 }));
  });
  
  function startAutoTiltSimple(element, { radiusRatio = 0.25, rpm = 20 } = {}) {
    // ждём пока vanillaTilt «прикрепится»
    const vt = element.vanillaTilt;
    if (!vt) return requestAnimationFrame(() => startAutoTiltSimple(element, { radiusRatio, rpm }));
  
    // насильно активируем hover-состояние
    vt.onMouseEnter();
  
    let t0 = performance.now();
  
    function frame(t) {
      // актуализируем геометрию (важно при адаптивной вёрстке)
      vt.updateElementPosition();
  
      const cx = vt.left + vt.width / 2;
      const cy = vt.top  + vt.height / 2;
      const r  = Math.min(vt.width, vt.height) * radiusRatio;
      const ang = ((t - t0) * (rpm * 2 * Math.PI)) / 60000;
  
      // «фейковая мышь» по окружности
      vt.event = {
        clientX: cx + r * Math.cos(ang),
        clientY: cy + r * Math.sin(ang)
      };
      vt.update();            // сразу применяем
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }