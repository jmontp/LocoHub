/* Shared SVG phase chart for previews, study pages, and comparisons. */
(function () {
  "use strict";
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const svgEl = (tag, attrs, text) => {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const finite = Number.isFinite;
  const fmt = (value) => finite(value) ? Number(value.toPrecision(5)).toString() : '—';
  function displayUnit(unit) {
    if (unit === 'rad') return {factor: 180 / Math.PI, label: 'degrees'};
    if (['rad/s', 'rad_s'].includes(unit)) return {factor: 180 / Math.PI, label: 'degrees/s'};
    if (['rad/s²', 'rad/s^2', 'rad_s2'].includes(unit)) return {factor: 180 / Math.PI, label: 'degrees/s²'};
    const labels = {deg: 'degrees', deg_s: 'degrees/s', deg_s2: 'degrees/s²', m_s: 'm/s', m_s2: 'm/s²', Nm_kg: 'Nm/kg', N_kg: 'N/kg', W_kg: 'W/kg', BW: 'body weights'};
    return {factor: 1, label: labels[unit] || unit || 'as stored'};
  }
  function ticks(min, max) {
    const raw = (max - min) / 4;
    if (!(raw > 0) || !finite(raw)) return [min];
    const power = 10 ** Math.floor(Math.log10(raw)), ratio = raw / power;
    const step = (ratio < 1.5 ? 1 : ratio < 3 ? 2 : ratio < 7 ? 5 : 10) * power;
    const result = [];
    for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9 && result.length < 20; v += step) result.push(Number(v.toPrecision(12)));
    return result;
  }
  function makeChart(phase, stats, signal, band, width, domain) {
    const unit = displayUnit(signal.unit);
    const points = phase.map((x, i) => ({x, y: finite(stats.mean[i]) ? stats.mean[i] * unit.factor : null,
      sd: finite(stats.sd[i]) && stats.n[i] >= 2 ? stats.sd[i] * unit.factor : null}));
    const valid = points.filter((p) => finite(p.x) && finite(p.y));
    if (!valid.length) return el('p', 'No recorded values for this signal and selection.', 'aggregate-empty');
    const W = Math.max(320, Math.round(width || 480)), H = 270, L = 52, R = 16, T = 28, B = 44;
    const lows = valid.map((p) => p.y - (band && finite(p.sd) ? p.sd : 0));
    const highs = valid.map((p) => p.y + (band && finite(p.sd) ? p.sd : 0));
    const lo = Math.min(...lows), hi = Math.max(...highs), pad = Math.max((hi - lo) * .1, Math.abs(hi) * .01, .000001);
    const ymin = domain ? domain[0] : lo - pad, ymax = domain ? domain[1] : hi + pad;
    const fullPhase = phase.filter(finite);
    const xmin = Math.min(...fullPhase), xmax = Math.max(...fullPhase);
    const X = (x) => L + (x - xmin) / (xmax - xmin || 1) * (W - L - R);
    const Y = (y) => H - B - (y - ymin) / (ymax - ymin) * (H - T - B);
    const svg = svgEl('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': `${signal.label}: mean${band ? ' and one standard deviation where at least two observations contribute' : ''}. Exact values are in Chart values below.`});
    svg.append(svgEl('title', {}, `${signal.label} (${unit.label})`));
    ticks(ymin, ymax).forEach((v) => {
      svg.append(svgEl('line', {x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: 'preview-grid'}));
      svg.append(svgEl('text', {x: L - 8, y: Y(v) + 4, 'text-anchor': 'end'}, fmt(v)));
    });
    ticks(xmin, xmax).forEach((v) => svg.append(svgEl('text', {x: X(v), y: H - B + 17, 'text-anchor': 'middle'}, fmt(v))));
    if (ymin < 0 && ymax > 0) svg.append(svgEl('line', {x1: L, x2: W - R, y1: Y(0), y2: Y(0), class: 'preview-zero'}));
    svg.append(svgEl('text', {x: L, y: 14, class: 'preview-axis-title'}, unit.label));
    svg.append(svgEl('text', {x: L + (W - L - R) / 2, y: H - 6, 'text-anchor': 'middle'}, 'Movement (%)'));
    if (band) {
      let segment = [];
      const flush = () => {
        if (segment.length > 1) {
          const top = segment.map((p) => `${X(p.x).toFixed(2)},${Y(p.y + p.sd).toFixed(2)}`);
          const bottom = [...segment].reverse().map((p) => `${X(p.x).toFixed(2)},${Y(p.y - p.sd).toFixed(2)}`);
          svg.append(svgEl('path', {d: `M${top.join(' L')} L${bottom.join(' L')} Z`, class: 'aggregate-band'}));
        }
        segment = [];
      };
      points.forEach((p) => { if (finite(p.x) && finite(p.y) && finite(p.sd)) segment.push(p); else flush(); });
      flush();
    }
    let path = '', connected = false;
    points.forEach((p) => {
      if (!finite(p.x) || !finite(p.y)) { connected = false; return; }
      path += `${connected ? 'L' : 'M'}${X(p.x).toFixed(2)},${Y(p.y).toFixed(2)} `; connected = true;
    });
    svg.append(svgEl('path', {d: path, class: 'preview-line aggregate-mean'}));
    return svg;
  }

  window.LocoHubPhaseChart = {makeChart, displayUnit};
})();
