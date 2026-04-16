(function() {
  const canvas = document.getElementById('netCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const wrap = canvas.parentElement;
  let W, H, nodes;
  const isMobile = window.innerWidth < 768;
  const COUNT = isMobile ? 25 : 55;
  const DIST  = isMobile ? 80 : 130;

  function resize() {
    W = canvas.width = wrap.offsetWidth;
    H = canvas.height = wrap.offsetHeight;
  }

  function init() {
    nodes = Array.from({length: COUNT}, () => ({
      x: Math.random() * W, y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      r: Math.random() * 1.5 + 0.5
    }));
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    nodes.forEach(n => {
      n.x += n.vx; n.y += n.vy;
      if (n.x < 0 || n.x > W) n.vx *= -1;
      if (n.y < 0 || n.y > H) n.vy *= -1;
    });
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const d = Math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2);
        if (d < DIST) {
          const alpha = (1 - d / DIST) * 0.5;
          const g = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
          g.addColorStop(0, `rgba(234,224,200,${alpha})`);
          g.addColorStop(0.5, `rgba(107,124,133,${alpha * 0.7})`);
          g.addColorStop(1, `rgba(234,224,200,${alpha})`);
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = g; ctx.lineWidth = 0.6; ctx.stroke();
        }
      }
    }
    nodes.forEach(n => {
      const g = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 5);
      g.addColorStop(0, 'rgba(234,224,200,0.4)');
      g.addColorStop(1, 'rgba(234,224,200,0)');
      ctx.beginPath(); ctx.arc(n.x, n.y, n.r * 5, 0, Math.PI * 2);
      ctx.fillStyle = g; ctx.fill();
      ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fillStyle = '#EAE0C8'; ctx.fill();
    });
    requestAnimationFrame(draw);
  }

  window.addEventListener('scroll', () => {
    canvas.style.transform = `translateY(${window.scrollY * 0.3}px)`;
  });
  window.addEventListener('resize', () => { resize(); });
  resize(); init(); draw();
})();
