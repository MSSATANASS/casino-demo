/* ============================================================
   CASINO DEMO — sfx.js
   Shared Web Audio sound effects (no audio files, no CDNs).
   Exposes globals: sfxSpinReel, sfxLand, sfxWin, sfxLose,
   sfxCard, sfxChip, sfxBall, sfxToggle, sfxUnlock
   ============================================================ */
(function () {
  var ctx = null;
  var master = null;
  var muted = false;

  function ensure() {
    if (!ctx) {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      master = ctx.createGain();
      master.gain.value = 0.5;
      master.connect(ctx.destination);
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }

  function noiseBuffer(dur) {
    var c = ensure();
    var len = Math.max(1, Math.floor(c.sampleRate * dur));
    var buf = c.createBuffer(1, len, c.sampleRate);
    var d = buf.getChannelData(0);
    for (var i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    return buf;
  }

  function tone(freq, dur, type, vol, when, slideTo) {
    var c = ensure();
    if (!c) return;
    var t = c.currentTime + (when || 0);
    var o = c.createOscillator();
    var g = c.createGain();
    o.type = type || "sine";
    o.frequency.setValueAtTime(freq, t);
    if (slideTo) o.frequency.exponentialRampToValueAtTime(slideTo, t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol || 0.3, t + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g);
    g.connect(master);
    o.start(t);
    o.stop(t + dur + 0.05);
  }

  function noise(dur, vol, filterFreq, when) {
    var c = ensure();
    if (!c) return;
    var t = c.currentTime + (when || 0);
    var src = c.createBufferSource();
    src.buffer = noiseBuffer(dur);
    var f = c.createBiquadFilter();
    f.type = "lowpass";
    f.frequency.value = filterFreq || 2000;
    var g = c.createGain();
    g.gain.setValueAtTime(vol || 0.3, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(f);
    f.connect(g);
    g.connect(master);
    src.start(t);
    src.stop(t + dur + 0.05);
  }

  function play(fn) {
    if (muted) return;
    try { fn(); } catch (e) { /* ignore */ }
  }

  window.sfxUnlock = function () { ensure(); };
  window.sfxToggle = function () { muted = !muted; return muted; };

  window.sfxSpinReel = function () { play(function () { noise(0.9, 0.18, 2600); }); };
  window.sfxLand = function () {
    play(function () {
      noise(0.09, 0.5, 900);
      tone(170, 0.09, "square", 0.22);
    });
  };
  window.sfxWin = function () {
    play(function () {
      [523, 659, 784, 1047, 1319].forEach(function (f, i) { tone(f, 0.22, "triangle", 0.28, i * 0.13); });
    });
  };
  window.sfxLose = function () {
    play(function () { tone(220, 0.5, "sawtooth", 0.2, 0, 110); });
  };
  window.sfxCard = function () {
    play(function () { noise(0.14, 0.3, 4200); });
  };
  window.sfxChip = function () {
    play(function () {
      tone(1150, 0.05, "square", 0.16);
      tone(1500, 0.06, "square", 0.12, 0.06);
    });
  };
  window.sfxBall = function () {
    play(function () { tone(880, 0.03, "square", 0.12); });
  };

  // unlock audio on first user gesture
  function unlock() { ensure(); }
  document.addEventListener("pointerdown", unlock, { once: true });
  document.addEventListener("keydown", unlock, { once: true });

  // wire the mute button if present on the page
  document.addEventListener("DOMContentLoaded", function () {
    var b = document.getElementById("mute-btn");
    if (b) b.addEventListener("click", function () {
      b.textContent = window.sfxToggle() ? "🔇" : "🔊";
    });
  });
})();