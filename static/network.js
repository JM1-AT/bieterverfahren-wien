(function(){
  const canvas = document.getElementById('netCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const wrap = canvas.parentElement;

  let W, H, nodes = [], animId;

  const isMobile  = window.innerWidth < 768;
  const NODE_COUNT = isMobile ? 55 : 110;
  const MAX_DIST   = isMobile ? 100 : 160;
  const SPEED      = 0.45;
  const COL        = 'rgba(107,124,133,';

  function resize(){
    W = canvas.width  = wrap.offsetWidth;
    H = canvas.height = wrap.offsetHeight;
  }

  function makeNode(){
    return {
      x:  Math.random() * W,
      y:  Math.random() * H,
      vx: (Math.random() - 0.5) * SPEED,
      vy: (Math.random() - 0.5) * SPEED,
      r:  Math.random() * 2.2 + 1
    };
  }

  function init(){
    resize();
    nodes = [];
    for (let i = 0; i < NODE_COUNT; i++) nodes.push(makeNode());
    cancelAnimationFrame(animId);
    loop();
  }

  function loop(){
    ctx.clearRect(0, 0, W, H);

    for (let i = 0; i < nodes.length; i++){
      const a = nodes[i];
      a.x += a.vx; a.y += a.vy;
      if (a.x < 0 || a.x > W) a.vx *= -1;
      if (a.y < 0 || a.y > H) a.vy *= -1;

      for (let j = i + 1; j < nodes.length; j++){
        const b = nodes[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < MAX_DIST){
          const alpha = (1 - dist / MAX_DIST) * 0.4;
          ctx.beginPath();
          ctx.strokeStyle = COL + alpha + ')';
          ctx.lineWidth = 0.65;
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    for (let i = 0; i < nodes.length; i++){
      const n = nodes[i];
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fillStyle = COL + '0.7)';
      ctx.fill();
    }

    animId = requestAnimationFrame(loop);
  }

  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      cancelAnimationFrame(animId);
      init();
    }, 150);
  });

  init();
})();
