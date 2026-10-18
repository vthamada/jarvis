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
  // Four thousand particles is a hard upper bound for the complete scene.
  const cloud = particleCloud(3200), inner = particleCloud(560), core = particleCloud(220);
  const projectedCloud = new Float32Array(cloud.length * 3);
  // Every edge shares vertices from the same subset, rather than creating
  // disconnected short branches. This fixed graph has fewer than 500 edges.
  const connections = (count, stride, offsets) => {
    const edges = [], vertices = Math.ceil(count / stride);
    for (let from = 0; from < vertices; from++) {
      for (const offset of offsets) if (from + offset < vertices) edges.push([from * stride * 3, (from + offset) * stride * 3]);
    }
    return edges;
  };
  const shellEdges = connections(cloud.length, 13, [7, 18]);
  const motion = host.matchMedia?.("(prefers-reduced-motion: reduce)");
  let mode = "idle", enabled = true, disposed = false, frame = null, last = null, phase = 0, level = 0;
  function audioLevel() {
    // An analyser can disappear while a local audio source is being replaced.
    // Presentation must stay alive without inventing a voice amplitude.
    try {
      const value = getLevel();
      return Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
    } catch { return 0; }
  }
  function draw(seconds, staticFrame = false) {
    const width = canvas.clientWidth, density = host.devicePixelRatio;
    const size = Number.isFinite(width) && width > 0 ? Math.max(1, Math.min(520, width)) : 320;
    const ratio = Number.isFinite(density) && density > 0 ? Math.max(1, Math.min(2, density)) : 1;
    const pixels = Math.round(size * ratio);
    if (canvas.width !== pixels || canvas.height !== pixels) { canvas.width = pixels; canvas.height = pixels; }
    context.setTransform(ratio, 0, 0, ratio, 0, 0); context.clearRect(0, 0, size, size);
    const center = size / 2, radius = size * 0.351;
    const target = staticFrame ? 0 : mode === "speaking_local" ? audioLevel() : mode === "speaking_fixture" ? 0.24 + 0.2 * Math.sin(phase * 6) ** 2 : 0;
    level = staticFrame ? 0 : smoothEnvelope(level, target, seconds);
    canvas.setAttribute?.("data-visual-level", String(Math.round(level * 1000) / 1000));
    canvas.setAttribute?.("data-visual-mode", mode);
    const t = staticFrame ? 0 : phase, deformation = 0.017 + level * 0.1;
    const rotation = t * 0.075, cos = Math.cos(rotation), sin = Math.sin(rotation);
    const tint = mode === "error" ? "255,151,90" : "22,204,255";
    const color = (opacity, white = false) => `rgba(${white ? "219,253,255" : tint},${opacity})`;
    const glow = context.createRadialGradient(center, center, 0, center, center, radius * 1.42);
    glow.addColorStop(0, color(0.46 + level * 0.15)); glow.addColorStop(0.2, color(0.13));
    glow.addColorStop(0.48, color(0.075)); glow.addColorStop(0.65, color(0.18));
    glow.addColorStop(0.73, color(0.08)); glow.addColorStop(1, color(0));
    context.fillStyle = glow; context.fillRect(0, 0, size, size);

    function orbit(scale, tilt, turn, start, sweep, opacity, lineWidth = 0.6, luminous = false) {
      const c = Math.cos(turn), s = Math.sin(turn);
      context.beginPath();
      for (let i = 0; i <= 100; i++) {
        const a = start + sweep * i / 100, x = Math.cos(a) * radius * scale, y = Math.sin(a) * radius * scale * tilt;
        const px = center + x * c - y * s, py = center + x * s + y * c;
        if (i === 0) context.moveTo(px, py); else context.lineTo(px, py);
      }
      if (luminous) {
        context.strokeStyle = color(opacity * 0.16); context.lineWidth = lineWidth + 4; context.stroke();
        context.strokeStyle = color(opacity * 0.28); context.lineWidth = lineWidth + 1.8; context.stroke();
      }
      context.strokeStyle = color(opacity, luminous); context.lineWidth = lineWidth; context.stroke();
    }
    function satellite(scale, tilt, turn, angle) {
      const x = Math.cos(angle) * radius * scale, y = Math.sin(angle) * radius * scale * tilt;
      const px = center + x * Math.cos(turn) - y * Math.sin(turn), py = center + x * Math.sin(turn) + y * Math.cos(turn);
      context.beginPath();
      for (let i = 0; i <= 16; i++) {
        const a = i * Math.PI * 2 / 16, dx = px + Math.cos(a) * size * 0.006, dy = py + Math.sin(a) * size * 0.006;
        if (i === 0) context.moveTo(dx, dy); else context.lineTo(dx, dy);
      }
      context.strokeStyle = color(0.22); context.lineWidth = size * 0.016; context.stroke();
      context.strokeStyle = color(0.9, true); context.lineWidth = size * 0.003; context.stroke();
      context.beginPath(); context.moveTo(px - size * 0.008, py); context.lineTo(px + size * 0.008, py);
      context.moveTo(px, py - size * 0.008); context.lineTo(px, py + size * 0.008);
      context.strokeStyle = color(0.92, true); context.lineWidth = 0.8; context.stroke();
    }

    // Precision instruments remain decorative: they never imply a task or sensor.
    orbit(1.245, 1, -t * 0.018, 0.2, Math.PI * 1.32, 0.3);
    orbit(1.245, 1, -t * 0.018, Math.PI * 1.57, Math.PI * 0.28, 0.76, 1.05);
    orbit(1.17, 1, t * 0.027, -0.7, Math.PI * 0.69, 0.63);
    orbit(1.17, 1, t * 0.027, Math.PI * 0.88, Math.PI * 0.73, 0.35);
    context.beginPath();
    for (let i = 0; i < 96; i++) {
      const a = i * Math.PI * 2 / 96, r = radius * 1.3, end = r + (i % 8 === 0 ? size * 0.012 : size * 0.004);
      context.moveTo(center + Math.cos(a) * r, center + Math.sin(a) * r);
      context.lineTo(center + Math.cos(a) * end, center + Math.sin(a) * end);
    }
    context.strokeStyle = color(0.35); context.lineWidth = 0.6; context.stroke();
    orbit(1.075, 0.38, -0.92 + t * 0.012, 0, Math.PI * 2, 0.27);
    orbit(1.28, 0.27, -0.28 + Math.sin(t * 0.07) * 0.04, 0, Math.PI * 2, 0.72, 0.85, true);

    context.globalCompositeOperation = "lighter";
    for (const [points, scale, projected] of [[cloud, 1, projectedCloud], [inner, 0.68, null], [core, 0.18, null]]) {
      for (let index = 0; index < points.length; index++) {
        const p = points[index];
        const wave = Math.sin(p.y * 13 + p.phase * 0.3 + t * 0.8) + Math.sin(p.phase * 0.7 - t * 0.6) * 0.55;
        const r = radius * scale * (1 + wave * deformation + Math.sin(t * 0.65) * 0.008);
        const x = p.x * cos + p.z * sin, z = p.z * cos - p.x * sin;
        const depth = 1 + z * 0.11, limb = Math.pow(1 - Math.abs(z), 2);
        const opacity = scale < 0.2 ? 0.48 + Math.max(0, z) * 0.5 : scale < 1 ? 0.16 + limb * 0.29 : 0.17 + limb * 0.7 + Math.max(0, z) * 0.16;
        const bright = scale < 0.2 || (index % 13 < 2 && z > -0.2);
        context.fillStyle = color(Math.min(1, opacity + level * 0.08), bright);
        const dot = Math.max(0.75, size / 355) * (0.75 + Math.max(0, z) * 0.5) * (scale < 1 ? 0.85 : 1) * (index % 13 === 0 ? 1.55 : index % 55 === 0 ? 1.8 : 1);
        const px = center + x * r * depth, py = center + p.y * r * depth;
        context.fillRect(px, py, dot, dot);
        if (projected) { projected[index * 3] = px; projected[index * 3 + 1] = py; projected[index * 3 + 2] = z; }
      }
    }

    function constellation(projected, edges, intensity) {
      for (let front = 0; front < 2; front++) {
        context.beginPath();
        for (const [from, to] of edges) {
          if (Number(projected[from + 2] + projected[to + 2] >= 0) !== front) continue;
          const x = projected[from], y = projected[from + 1], endX = projected[to], endY = projected[to + 1];
          const midX = (x + endX) / 2, midY = (y + endY) / 2;
          const controlX = midX + (midX - center) * 0.16, controlY = midY + (midY - center) * 0.16;
          context.moveTo(x, y);
          // Three segments soften long strands while keeping the whole graph
          // below 1,500 segments; no quadratic API or all-pairs lookup needed.
          for (let step = 1; step <= 3; step++) {
            const progress = step / 3, rest = 1 - progress;
            context.lineTo(rest * rest * x + 2 * rest * progress * controlX + progress * progress * endX,
              rest * rest * y + 2 * rest * progress * controlY + progress * progress * endY);
          }
        }
        if (front) {
          context.strokeStyle = color(intensity * 0.2); context.lineWidth = 2.4; context.stroke();
        }
        context.strokeStyle = color(intensity * (front ? 1 : 0.4), front === 1);
        context.lineWidth = front ? 0.6 : 0.45; context.stroke();
      }
    }
    constellation(projectedCloud, shellEdges, 0.29 + level * 0.09);
    // A few existing vertices get star-shaped highlights, not extra particles.
    context.beginPath();
    for (let index = 0; index < cloud.length; index += 110) {
      const at = index * 3; if (projectedCloud[at + 2] < -0.2) continue;
      const px = projectedCloud[at], py = projectedCloud[at + 1], ray = size * (0.005 + 0.003 * Math.sin(index + t * 0.5) ** 2);
      context.moveTo(px - ray, py); context.lineTo(px + ray, py);
      context.moveTo(px, py - ray); context.lineTo(px, py + ray);
    }
    context.strokeStyle = color(0.78, true); context.lineWidth = 0.75; context.stroke();

    // Latitude ribbons and tangential filaments create a breathing volume.
    for (let latitude = -3; latitude <= 3; latitude++) {
      const y = latitude / 4, scale = Math.sqrt(1 - y * y);
      context.beginPath();
      for (let i = 0; i <= 100; i++) {
        const a = i * Math.PI * 2 / 100 + rotation, wave = Math.sin(a * 6 + t * 0.7 + latitude) * deformation;
        const x = center + Math.cos(a) * radius * scale * (1 + wave);
        const py = center + y * radius + Math.sin(a) * radius * scale * 0.12 + wave * radius * 0.2;
        if (i === 0) context.moveTo(x, py); else context.lineTo(x, py);
      }
      context.strokeStyle = color(0.14 + level * 0.08); context.lineWidth = 0.55; context.stroke();
    }
    for (let layer = 0; layer < 9; layer++) {
      context.beginPath();
      for (let i = 0; i <= 160; i++) {
        const a = i * Math.PI * 2 / 160;
        const wave = Math.sin(a * 5 + t * 0.5 + layer * 0.45) * 0.6 + Math.sin(a * 9 - t * 0.65 + layer) * 0.4;
        const r = radius * (0.94 + layer * 0.009 + wave * (0.025 + level * 0.07));
        const x = center + Math.cos(a) * r, y = center + Math.sin(a) * r;
        if (i === 0) context.moveTo(x, y); else context.lineTo(x, y);
      }
      context.strokeStyle = color((layer % 3 === 0 ? 0.5 : 0.29 + layer * 0.024) + level * 0.095, layer % 3 === 0);
      context.lineWidth = layer % 3 === 0 ? 1 : 0.65; context.stroke();
    }
    orbit(0.2 + level * 0.015, 0.6, -t * 0.14, 0, Math.PI * 2, 0.72, 0.8, true);
    orbit(1.28, 0.27, -0.28 + Math.sin(t * 0.07) * 0.04, 0, Math.PI * 1.05, 0.93, 1.1, true);
    orbit(1.19, 0.5, 0.76 - t * 0.016, 0.25, Math.PI * 1.34, 0.62, 0.75, true);
    satellite(1.28, 0.27, -0.28 + Math.sin(t * 0.07) * 0.04, t * 0.11 + 0.4);
    satellite(1.19, 0.5, 0.76 - t * 0.016, -t * 0.08 + 2.7);
    satellite(1.245, 1, -t * 0.018, -t * 0.055 - 0.6);
    const light = context.createRadialGradient(center, center, 0, center, center, radius * 0.55);
    light.addColorStop(0, color(0.96, true)); light.addColorStop(0.045, color(0.9, true));
    light.addColorStop(0.12, color(0.64 + level * 0.15)); light.addColorStop(0.38, color(0.18 + level * 0.1)); light.addColorStop(1, color(0));
    context.fillStyle = light; context.fillRect(center - radius * 0.55, center - radius * 0.55, radius * 1.1, radius * 1.1);
    context.globalCompositeOperation = "source-over";
  }
  function active() { return !disposed && enabled && !motion?.matches && !host.document?.hidden; }
  function tick(timestamp) {
    frame = null; if (!active()) return;
    const delta = last === null ? 1 / 30 : Math.min(0.1, (timestamp - last) / 1000);
    if (last === null || timestamp - last >= 1000 / 30) { last = timestamp; phase += delta; draw(delta); }
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
    setMode(value) { if (!MODES.has(value)) throw new Error("invalid_sphere_mode"); if (disposed) return; mode = value; if (value !== "speaking_local" && value !== "speaking_fixture") level = 0; if (!active()) draw(0, true); },
    setMotion(value) { if (disposed) return; enabled = value === true; refresh(); }, refresh,
    dispose() {
      if (disposed) return; disposed = true; if (frame !== null) cancelFrame(frame);
      observer?.disconnect(); motion?.removeEventListener?.("change", refresh);
      host.document?.removeEventListener("visibilitychange", refresh);
    },
  });
}
