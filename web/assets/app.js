/* Shared utilities for the NameRank companion site. Dependency-free. */

export async function loadJSON(path) {
  const r = await fetch(path, { cache: "no-store" });
  if (!r.ok) throw new Error(`failed to load ${path}: ${r.status}`);
  return r.json();
}

export function zone(nr) {
  if (nr <= 0.1) return "silent";
  if (nr >= 0.7) return "universal";
  return "discriminative";
}

export function fmt(n, p = 3) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return Number(n).toFixed(p);
}

/* Draw a horizontal bar [0..1] inside a 100%-width track. */
export function bar(nr) {
  const z = zone(nr);
  const pct = Math.max(0, Math.min(1, nr)) * 100;
  return `<div class="bar-track"><div class="bar-fill ${z}" style="width:${pct.toFixed(1)}%"></div></div>`;
}

/* Build an SVG horizontal-bar chart. */
export function svgBars({ rows, width = 720, rowHeight = 22, labelW = 220, valueMax = 1, accessor = r => r.value, label = r => r.label, color = () => "#1f77b4", annotate = r => r.value.toFixed(3) }) {
  const padTop = 8, padBottom = 18, padRight = 70;
  const height = padTop + padBottom + rows.length * rowHeight;
  const chartLeft = labelW + 12;
  const chartW = width - chartLeft - padRight;
  const x = v => chartLeft + (v / valueMax) * chartW;

  const lines = [];
  // axis ticks
  for (let t = 0; t <= valueMax; t += 0.1) {
    lines.push(`<line x1="${x(t)}" y1="${padTop}" x2="${x(t)}" y2="${height - padBottom}" stroke="#eee" />`);
    if (Math.abs(t - Math.round(t * 5) / 5) < 1e-6) {
      lines.push(`<text x="${x(t)}" y="${height - 5}" font-size="10" fill="#888" text-anchor="middle">${t.toFixed(1)}</text>`);
    }
  }

  rows.forEach((r, i) => {
    const y = padTop + i * rowHeight;
    const v = Math.max(0, Math.min(valueMax, accessor(r)));
    lines.push(`<text x="${labelW + 6}" y="${y + rowHeight - 7}" font-size="11" fill="#1d1d1f" text-anchor="end">${escapeHTML(label(r))}</text>`);
    lines.push(`<rect x="${chartLeft}" y="${y + 3}" width="${(v / valueMax) * chartW}" height="${rowHeight - 6}" fill="${color(r)}" />`);
    lines.push(`<text x="${chartLeft + (v / valueMax) * chartW + 4}" y="${y + rowHeight - 7}" font-size="11" fill="#444">${annotate(r)}</text>`);
  });

  return `<svg viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="chart">${lines.join("")}</svg>`;
}

export function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* Debounced input handler. */
export function debounce(fn, ms = 120) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}
