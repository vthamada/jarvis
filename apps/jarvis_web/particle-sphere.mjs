// Presentation only. Never interprets speech, approves actions or claims Core activity.
const MODES = new Set(["idle", "thinking", "listening_fixture", "speaking_fixture", "speaking_local", "error"]);
export function particleCloud(count = 2400) {
  if (!Number.isInteger(count) || count < 1 || count > 4000) throw new Error("invalid_particle_count");
  return Array.from({ length: count }, (_, i) => {
    const y = 1 - (i + 0.5) * 2 / count, angle = i * Math.PI * (3 - Math.sqrt(5));
    const radius = Math.sqrt(1 - y * y);
    return Object.freeze({ x: Math.cos(angle) * radius, y, z: Math.sin(angle) * radius, phase: angle });
  });
}
export function smoothEnvelope(previous, target, seconds) {
  if (![previous, target, seconds].every(Number.isFinite)) return 0;
  const value = Math.max(0, Math.min(1, target));
  return Math.max(0, Math.min(1, previous + (value - previous) * (1 - Math.exp(-Math.max(0, seconds) * (value > previous ? 22 : 9)))));
}
export function createParticleSphere(canvas, {
  getLevel = () => 0, requestFrame = (fn) => requestAnimationFrame(fn),
  cancelFrame = (id) => cancelAnimationFrame(id), host = globalThis,
} = {}) {
  const context = canvas.getContext("2d");
  if (!context) return Object.freeze({ setMode() {}, setMotion() {}, refresh() {}, dispose() {} });
  const cloud = particleCloud(3200), core = particleCloud(220);
  const motion = host.matchMedia?.("(prefers-reduced-motion: reduce)");
  let mode = "idle", enabled = true, disposed = false, frame = null, last = null, phase = 0, level = 0;
  function draw(seconds, staticFrame = false) {
    const size = Math.max(1, Math.min(520, canvas.clientWidth || 320)), ratio = Math.min(2, host.devicePixelRatio || 1);
    const pixels = Math.round(size * ratio);
    if (canvas.width !== pixels || canvas.height !== pixels) { canvas.width = pixels; canvas.height = pixels; }
    context.setTransform(ratio, 0, 0, ratio, 0, 0); context.clearRect(0, 0, size, size);
    const center = size / 2, radius = size * 0.38;
    const glow = context.createRadialGradient(center, center, 0, center, center, radius * 1.45);
    glow.addColorStop(0, "#0b595935"); glow.addColorStop(0.65, "#007c7c20"); glow.addColorStop(1, "#00242400");
    context.fillStyle = glow; context.fillRect(0, 0, size, size);
    const target = mode === "speaking_local" ? getLevel() : mode === "speaking_fixture" ? 0.24 + 0.2 * Math.sin(phase * 6) ** 2 : 0;
    level = staticFrame ? 0 : smoothEnvelope(level, target, seconds);
    canvas.setAttribute?.("data-visual-level", String(Math.round(level * 1000) / 1000));
    canvas.setAttribute?.("data-visual-mode", mode);
    const t = staticFrame ? 0 : phase, deformation = 0.025 + level * 0.11;
    const rotation = t * 0.065, cos = Math.cos(rotation), sin = Math.sin(rotation);
    for (const [points, scale] of [[cloud, 1], [core, 0.145]]) {
      for (const p of points) {
        const wave = Math.sin(p.y * 13 + p.phase * 0.3 + t * 0.8) + Math.sin(p.phase * 0.7 - t * 0.6) * 0.55;
        const r = radius * scale * (1 + wave * deformation);
        const x = p.x * cos + p.z * sin, z = p.z * cos - p.x * sin;
        const depth = 1 + z * 0.12, limb = Math.pow(1 - Math.abs(z), 2);
        const opacity = scale < 1 ? 0.65 : 0.09 + limb * 0.84 + Math.max(0, z) * 0.04;
        context.fillStyle = `rgba(45,218,207,${opacity})`;
        const dot = Math.max(0.8, size / 420) * (0.85 + Math.max(0, z) * 0.35);
        context.fillRect(center + x * r * depth, center + p.y * r * depth, dot, dot);
      }
    }
    // Tangential filaments give the cloud a fluid, breathing silhouette.
    for (let layer = 0; layer < 10; layer++) {
      context.beginPath();
      for (let i = 0; i <= 180; i++) {
        const a = i * Math.PI * 2 / 180;
        const wave = Math.sin(a * 5 + t * 0.5 + layer * 0.45) * 0.6 + Math.sin(a * 9 - t * 0.65 + layer) * 0.4;
        const r = radius * (0.91 + layer * 0.013 + wave * (0.034 + level * 0.085));
        const x = center + Math.cos(a) * r, y = center + Math.sin(a) * r;
        if (i === 0) context.moveTo(x, y); else context.lineTo(x, y);
      }
      context.strokeStyle = `rgba(52,215,206,${0.28 + layer * 0.018 + level * 0.035})`; context.lineWidth = 0.85; context.stroke();
    }
  }
  function active() { return !disposed && enabled && !motion?.matches && !host.document?.hidden; }
  function tick(timestamp) {
    frame = null; if (!active()) return;
    const delta = last === null ? 1 / 30 : Math.min(0.1, (timestamp - last) / 1000);
    if (last === null || timestamp - last >= 32) { last = timestamp; phase += delta; draw(delta); }
    frame = requestFrame(tick);
  }
  function refresh() {
    if (disposed) return;
    if (frame !== null) cancelFrame(frame);
    frame = null; last = null;
    if (active()) frame = requestFrame(tick); else draw(0, true);
  }
  motion?.addEventListener?.("change", refresh);
  host.document?.addEventListener("visibilitychange", refresh);
  const observer = host.ResizeObserver ? new host.ResizeObserver(refresh) : null;
  observer?.observe(canvas); draw(0, true); refresh();
  return Object.freeze({
    setMode(value) { if (!MODES.has(value)) throw new Error("invalid_sphere_mode"); mode = value; if (value !== "speaking_local" && value !== "speaking_fixture") level = 0; if (!active()) draw(0, true); },
    setMotion(value) { enabled = value === true; refresh(); }, refresh,
    dispose() {
      if (disposed) return; disposed = true; if (frame !== null) cancelFrame(frame);
      observer?.disconnect(); motion?.removeEventListener?.("change", refresh);
      host.document?.removeEventListener("visibilitychange", refresh);
    },
  });
}
