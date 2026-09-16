/* clock-demo.js — renders the stale-action Pong illustration on the project page.
   Physics lives in pong-sim.js (pure); this file is only the canvas + controls. */
(function () {
  'use strict';

  var canvas = document.getElementById('cd-canvas');
  if (!canvas || !window.PongSim) return;

  var ctx = canvas.getContext('2d');
  var W = canvas.width, H = canvas.height, PAD = 20;
  var sim = window.PongSim.create(7, 14.4);
  var running = false, last = 0, raf = null;

  var elRet = document.getElementById('cd-ret');
  var elMiss = document.getElementById('cd-miss');
  var elClock = document.getElementById('cd-t');
  var elHz = document.getElementById('cd-hzval');
  var slider = document.getElementById('cd-hz');
  var btn = document.getElementById('cd-run');

  function fx(x) { return PAD + x * (W - 2 * PAD); }
  function fy(y) { return PAD + y * (H - 2 * PAD); }

  function draw() {
    var P = window.PongSim.PADDLE, B = window.PongSim.BALL;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#0d1622';
    ctx.fillRect(0, 0, W, H);

    // field frame
    ctx.strokeStyle = '#1e2f45';
    ctx.lineWidth = 2;
    ctx.strokeRect(PAD, PAD, W - 2 * PAD, H - 2 * PAD);

    // centre line
    ctx.setLineDash([6, 8]);
    ctx.strokeStyle = '#1b2a3d';
    ctx.beginPath();
    ctx.moveTo(W / 2, PAD);
    ctx.lineTo(W / 2, H - PAD);
    ctx.stroke();
    ctx.setLineDash([]);

    // stale aim: where the ball was at the last decision
    var age = Math.max(0, sim.t - sim.lastDecisionAt);
    var ty = fy(sim.paddle.target);
    ctx.strokeStyle = 'rgba(231, 76, 60, 0.55)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(fx(0.02), ty);
    ctx.lineTo(fx(0.16), ty);
    ctx.stroke();
    ctx.fillStyle = 'rgba(231, 76, 60, 0.9)';
    ctx.beginPath();
    ctx.arc(fx(0.09), ty, 3.5, 0, Math.PI * 2);
    ctx.fill();

    // paddle -> aim line
    ctx.strokeStyle = 'rgba(231, 76, 60, 0.35)';
    ctx.beginPath();
    ctx.moveTo(fx(P.x), fy(sim.paddle.y));
    ctx.lineTo(fx(0.09), ty);
    ctx.stroke();

    // paddle
    ctx.fillStyle = '#e8eef7';
    var px = fx(P.x - P.w), pw = P.w * (W - 2 * PAD) * 1.0;
    ctx.beginPath();
    ctx.roundRect ? ctx.roundRect(px, fy(sim.paddle.y - P.half), pw, 2 * P.half * (H - 2 * PAD), 4)
                  : ctx.rect(px, fy(sim.paddle.y - P.half), pw, 2 * P.half * (H - 2 * PAD));
    ctx.fill();

    // ball
    if (sim.ball) {
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(fx(sim.ball.x), fy(sim.ball.y), B.r * (H - 2 * PAD), 0, Math.PI * 2);
      ctx.fill();
    }

    // aim age, in the field
    ctx.font = '13px ui-monospace, Menlo, Consolas, monospace';
    ctx.fillStyle = 'rgba(231, 76, 60, 0.9)';
    ctx.fillText('aim is ' + age.toFixed(1) + ' s old', fx(0.02), ty - 9);

    if (sim.over) {
      ctx.fillStyle = 'rgba(13, 22, 34, 0.82)';
      ctx.fillRect(PAD, PAD, W - 2 * PAD, H - 2 * PAD);
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.font = '600 26px Georgia, serif';
      ctx.fillText('45 s episode complete', W / 2, H / 2 - 34);
      ctx.font = '600 20px ui-monospace, Menlo, Consolas, monospace';
      ctx.fillStyle = '#e8eef7';
      ctx.fillText(sim.returns + ' returns · ' + sim.misses + ' misses at ' +
                   sim.hz.toFixed(1) + ' Hz', W / 2, H / 2 + 4);
      ctx.font = '14px sans-serif';
      ctx.fillStyle = '#9fb2c9';
      ctx.fillText('Change the control rate and run another episode.', W / 2, H / 2 + 40);
      ctx.textAlign = 'left';
    }
  }

  function hud() {
    elRet.textContent = sim.returns;
    elMiss.textContent = sim.misses;
    elClock.textContent = sim.t.toFixed(1) + ' s';
  }

  function frame(ts) {
    if (!running) return;
    if (!last) last = ts;
    var dt = (ts - last) / 1000;
    last = ts;
    window.PongSim.step(sim, dt);
    draw(); hud();
    if (sim.over) { running = false; btn.textContent = 'Run again'; return; }
    raf = requestAnimationFrame(frame);
  }

  function start() {
    if (sim.over) { window.PongSim.reset(sim); last = 0; }
    running = true;
    btn.textContent = 'Pause';
    last = 0;
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(frame);
  }

  function pause() {
    running = false;
    btn.textContent = 'Resume';
    cancelAnimationFrame(raf);
  }

  btn.addEventListener('click', function () {
    if (running) pause(); else start();
  });

  function setHz(v, fromSlider) {
    sim.hz = v;
    elHz.textContent = v.toFixed(1) + ' Hz';
    if (!fromSlider) slider.value = String(v);
    document.querySelectorAll('#cd-presets .sbtn').forEach(function (b) {
      b.setAttribute('aria-pressed', String(Math.abs(parseFloat(b.dataset.hz) - v) < 0.05));
    });
  }

  slider.addEventListener('input', function () { setHz(parseFloat(slider.value), true); });
  document.querySelectorAll('#cd-presets .sbtn').forEach(function (b) {
    b.addEventListener('click', function () { setHz(parseFloat(b.dataset.hz), false); });
  });

  setHz(14.4, true);
  draw(); hud();
})();
