/* pong-sim.js — simulation core for the "clock" demo on the project page.

   The mechanism is the paper's: an agent decides at a fixed control frequency
   and its last decision is repeated until the next tick (stale-action repeat).
   The paddle here drives toward the ball position sampled at its last decision,
   so lowering the control frequency lowers how fresh that target is.

   Pure math, no DOM — also runs headless under node for verification. */
(function (root) {
  'use strict';

  var FIELD = { w: 1, h: 1 };
  var PADDLE = { x: 0.06, w: 0.018, half: 0.085, speed: 1.7 };
  var BALL = { r: 0.017, speed: 1.35, maxAng: 0.95 };
  var EPISODE_S = 45;              // one episode = the paper's 45 s real-time budget

  function mulberry32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      var t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  function serve(s) {
    var ang = (s.rnd() * 2 - 1) * BALL.maxAng;
    s.ball = {
      x: 0.55 + s.rnd() * 0.28,
      y: 0.18 + s.rnd() * 0.64,
      vx: -Math.cos(ang) * BALL.speed,
      vy: Math.sin(ang) * BALL.speed
    };
    s.rally = 0;
  }

  function create(seed, hz) {
    var s = {
      rnd: mulberry32(seed == null ? 1 : seed),
      seed: seed == null ? 1 : seed,
      t: 0, hz: hz || 14.4, over: false,
      ball: null, paddle: { y: 0.5, target: 0.5 },
      nextDecision: -1, lastDecisionAt: 0, decisions: 0,
      returns: 0, misses: 0, rally: 0, best: 0
    };
    serve(s);
    return s;
  }

  function reset(s) {
    var seed = s.seed, hz = s.hz;
    var n = create(seed, hz);
    for (var k in n) { s[k] = n[k]; }
    return s;
  }

  function step(s, dt, hz) {
    if (s.over) return s;
    if (hz) s.hz = hz;
    if (dt > 0.1) dt = 0.1;                    // ignore long tab-away gaps
    if (s.t >= EPISODE_S) { s.over = true; return s; }

    // 1. decide on a fixed clock (this is the control rate)
    if (s.nextDecision < 0 || s.t >= s.nextDecision) {
      s.paddle.target = s.ball.y;              // the decision: where the ball is NOW
      s.lastDecisionAt = s.t;
      s.decisions++;
      s.nextDecision = s.t + 1 / s.hz;
    }

    // 2. keep executing the last decision until the next tick
    var dy = s.paddle.target - s.paddle.y, maxd = PADDLE.speed * dt;
    s.paddle.y += Math.max(-maxd, Math.min(maxd, dy));
    if (s.paddle.y < PADDLE.half) s.paddle.y = PADDLE.half;
    if (s.paddle.y > FIELD.h - PADDLE.half) s.paddle.y = FIELD.h - PADDLE.half;

    // 3. the world does not wait for the agent
    var b = s.ball;
    b.x += b.vx * dt; b.y += b.vy * dt;
    if (b.y < BALL.r) { b.y = BALL.r; b.vy = -b.vy; }
    if (b.y > FIELD.h - BALL.r) { b.y = FIELD.h - BALL.r; b.vy = -b.vy; }
    if (b.x > FIELD.w - BALL.r && b.vx > 0) { b.x = FIELD.w - BALL.r; b.vx = -b.vx; }

    // 4. paddle plane
    if (b.x <= PADDLE.x + BALL.r && b.vx < 0) {
      if (Math.abs(b.y - s.paddle.y) <= PADDLE.half + BALL.r) {
        var off = Math.max(-1, Math.min(1, (b.y - s.paddle.y) / PADDLE.half));
        var ang = off * BALL.maxAng;
        b.x = PADDLE.x + BALL.r;
        b.vx = Math.cos(ang) * BALL.speed;
        b.vy = Math.sin(ang) * BALL.speed;
        s.returns++; s.rally++; if (s.rally > s.best) s.best = s.rally;
      } else {
        s.misses++; s.rally = 0; serve(s);
      }
    }

    s.t += dt;
    if (s.t >= EPISODE_S) s.over = true;
    return s;
  }

  // fixed-timestep episode, used by the verification harness
  function runEpisode(hz, seed, seconds) {
    var s = create(seed, hz), dt = 1 / 120, end = (seconds || EPISODE_S);
    while (!s.over && s.t < end) step(s, dt);
    s.over = true;
    return { hz: hz, seed: seed, returns: s.returns, misses: s.misses,
             best: s.best, decisions: s.decisions };
  }

  root.PongSim = {
    create: create, reset: reset, step: step, runEpisode: runEpisode,
    EPISODE_S: EPISODE_S, PADDLE: PADDLE, BALL: BALL, FIELD: FIELD
  };
})(typeof window !== 'undefined' ? window : globalThis);
