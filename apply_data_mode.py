#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Добавляет в ttt_kod1.html режим DATA (Data Collection Mode).

    python3 apply_data_mode.py ttt_kod1.html              -> ttt_kod1_DATA.html
    python3 apply_data_mode.py вход.html выход.html

Каждая правка ищется по уникальному фрагменту и должна найтись РОВНО один раз, иначе скрипт остановится
и ничего не запишет. Исходный файл не меняется. CONFIG не трогается.
"""
import sys
if len(sys.argv) < 2:
    sys.exit(__doc__)
src = sys.argv[1]
dst = sys.argv[2] if len(sys.argv) > 2 else (src[:-5] if src.endswith('.html') else src) + '_DATA.html'
s = open(src, encoding='utf-8').read()
log = []
def rep(old, new, tag):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit('СТОП: правка "%s": фрагмент найден %d раз (нужно 1). Файл не записан.' % (tag, n))
    s = s.replace(old, new); log.append(tag)
dcm = r'''/* ==== DCM:BEGIN — режим исследования (Data Collection Mode). Только читает готовые результаты конвейера, CONFIG не меняет. Выключен — хуки не делают ничего. ==== */
const DCM = {
on: false, snapEvery: 10, lastFt: null, vidSec: 0, dirty: true, cache: null,
BF: ['minAreaPx', 'minWidthLane', 'minHeightLane', 'minAreaLane2', 'minFill'], // порядок = порядок проверок в extract()
BR: ['SMALL_BLOB', 'BAD_WIDTH', 'BAD_HEIGHT', 'BAD_AREA', 'BAD_FILL'],
FN: ['minAreaPx', 'minWidthLane', 'minAreaLane2', 'minHeightLane', 'minFill', 'softMinLane', 'ownerFrac', 'ownerTol', 'dropFragments', 'confirmFrames', 'minMovePx', 'minShowPts', 'minShowWinSec', 'minShowPath', 'finalMinPts'],
CLS: ['car', 'truck', 'bus', 'motorcycle'], ZN: ['FAR', 'MID', 'NEAR'], TH: [30, 40, 50, 60, 70, 80, 90],
reset() {
this.recs = []; this.snaps = []; this.vehN = 0; this.nNoise = 0; this.nLate = 0; this.nCap = 0; this.nCand = 0; this.nCandDet = 0;
this.rs = {}; this.rsV = {}; this.blobRej = {}; this.ownR = []; this.vidSec = 0; this.lastFt = null; this.dirty = true; this.cache = null;
this.F = {}; for (const k of this.FN) this.F[k] = { n: 0, rej: 0, sole: 0, nd: 0, rejd: 0, soled: 0 };
},
// ---------- статистика ----------
num(a) { return a.filter(x => typeof x === 'number' && isFinite(x)).sort((x, y) => x - y); },
q(s, p) { if (!s.length) return NaN; const i = (s.length - 1) * p / 100, lo = Math.floor(i), hi = Math.ceil(i); return s[lo] + (s[hi] - s[lo]) * (i - lo); },
med(a) { return this.q(this.num(a), 50); },
dist(a) { const s = this.num(a), o = { n: s.length }; if (!s.length) return o; o.min = s[0]; o.max = s[s.length - 1]; for (const p of [10, 25, 50, 75, 90, 95]) o['p' + p] = this.q(s, p); return o; },
// ---------- хуки блобов (extract) ----------
blob(b, lw, bw, bh, bc) { // вызывается ДО штатных фильтров и их решения не меняет; «det» — кандидат подтверждён рамкой детектора машин
const det = !!(vdGate() && VD.cal && vdHit(b));
const f = [b.area < bc.minAreaPx, bw < bc.minWidthLane * lw, bh < bc.minHeightLane * lw, b.area < Math.min(bc.minAreaLane2 * lw * lw, bc.minAreaMaxPx), b.area < bc.minFill * bw * bh];
const nf = f.filter(Boolean).length;
this.nCand++; if (det) this.nCandDet++;
for (let i = 0; i < 5; i++) { const o = this.F[this.BF[i]]; o.n++; if (det) o.nd++; if (f[i]) { o.rej++; if (det) o.rejd++; if (nf === 1) { o.sole++; if (det) o.soled++; } } }
if (nf) { const r = this.BR[f.indexOf(true)], o = this.blobRej[r] || (this.blobRej[r] = [0, 0]); o[0]++; if (det) o[1]++; }
},
own(arr, sA, bY, owner, maxA, bc) { // кластер склеенных блобов соседних полос: кто стал «хозяином» кромки
let nfr = 0, ntol = 0;
for (const r of arr) { if (r === owner) continue; if (sA[r] >= bc.minAreaPx && sA[r] < bc.ownerFrac * maxA) nfr++; if (Math.abs(bY[r] - bY[owner]) <= bc.ownerTol) ntol++; }
const F = this.F; F.dropFragments.n += arr.length; F.dropFragments.rej += arr.length - 1; F.ownerFrac.n += arr.length; F.ownerFrac.rej += nfr; F.ownerTol.n += arr.length - 1; F.ownerTol.rej += ntol;
if (this.ownR.length < 20000) this.ownR.push(sA[owner] / maxA);
},
post(b, bc, lw) { if (b.clipped && !b.touching) { const o = this.F.softMinLane; o.n++; if (!b.soft) o.rej++; } },
// ---------- рамка детектора → класс и уверенность ----------
det(b) {
if (!VD.cal) return null;
let best = null, bo = 0; const ba = (b.x1 + 1 - b.x0) * (b.y1 + 1 - b.y0);
for (const r of VD.cal) { const ox = Math.min(b.x1 + 1, r.x1) - Math.max(b.x0, r.x0), oy = Math.min(b.y1 + 1, r.y1) - Math.max(b.y0, r.y0); if (ox > 0 && oy > 0) { const o = ox * oy / Math.max(1, Math.min(ba, (r.x1 - r.x0) * (r.y1 - r.y0))); if (o > bo) { bo = o; best = r; } } }
return bo >= 0.3 && best ? { cls: best.cls || 'vehicle', sc: best.sc == null ? 1 : best.sc } : null;
},
cls(d) { let b = 'unknown', bv = 0; for (const k in d.vote) if (d.vote[k] > bv) { bv = d.vote[k]; b = k; } return b; },
// ---------- покадровый сбор по живым трекам (всё уже посчитано конвейером) ----------
frame(t) {
const trk = R.trk, g = R.geo, tc = CONFIG.track; if (!trk || !g) return;
if (this.lastFt != null) this.vidSec += clamp(t - this.lastFt, 0, 0.5); this.lastFt = t;
const N1 = g.N + 1;
for (const tr of trk.tracks) {
const b = tr.blob; if (tr.tLast !== t || !b || !(b.lane >= 1 && b.lane <= g.N)) continue;
const d = tr.dc || (tr.dc = { S: [], vote: {}, nDet: 0, maxSc: 0, revN: 0, late: tr.frames > 1, veh: false, want: 0, snap: null });
const lane = b.lane, lw = b.laneW || laneWidthAt(g, b.yb, lane), bw = b.bw || (b.x1 - b.x0 + 1), bh = b.y1 - b.y0 + 1;
const yy = clamp(Math.round(b.yb), 0, g.ah - 1), xl = g.xsAt[yy * N1 + lane - 1], xr = g.xsAt[yy * N1 + lane];
const uw = Math.max(1, b.ux1 - b.ux0 + 1), ov = 100 * (Math.max(0, xl - b.ux0) + Math.max(0, b.ux1 + 1 - xr)) / uw; // доля ширины (с осколками) за границами своей полосы
const li = lane - 1, c = calAt(trk.cals, li), v = trk._v(b.xc, b.yEdge, li), s = sOfV(trk.cals, v, li), sN = sOfV(trk.cals, c.vNear, li), sF = sOfV(trk.cals, c.vFar, li);
let fr = isFinite(s) && isFinite(sN) && isFinite(sF) && sF !== sN ? (s - sN) / (sF - sN) : (c.vNear - v) / Math.max(1e-6, c.vNear - c.vFar); // 0 — у камеры, 1 — дальний край зоны (по расстоянию)
const zone = fr < 1 / 3 ? 'NEAR' : (fr < 2 / 3 ? 'MID' : 'FAR');
const clean = !b.touching && !b.clipped, wP = 100 * bw / lw;
const dm = this.det(b); if (dm) { d.vote[dm.cls] = (d.vote[dm.cls] || 0) + dm.sc; d.nDet++; if (dm.sc > d.maxSc) d.maxSc = dm.sc; }
d.S.push([wP, 100 * bh / lw, 100 * b.area / (lw * lw), bh / bw, b.area / (bw * bh), bw, bh, b.area, b.yb, lw, ov, b.exA ? b.area / (b.area + b.exA) : 1, b.ownR == null ? 1 : b.ownR, zone, s, clean ? 1 : 0, t, lane]);
if (!d.veh && tr.moved && tr.frames >= tc.confirmFrames) { d.veh = true; if (++this.vehN % this.snapEvery === 0) d.want = 12; } // каждая N-я машина получает фото
if (d.want > 0) { if (clean && !d.snap) { const cl = this.cls(d), u = this.snap(tr, b, wP, cl); if (u) { d.snap = { id: tr.id, cls: cl, lane, pw: wP, pf: null, url: u }; this.snaps.push(d.snap); if (this.snaps.length > 60) this.snaps.shift(); d.want = 0; } else d.want--; } else d.want--; }
}
this.dirty = true;
},
snap(tr, b, wp, cl) { // фото машины (кроп кадра) с отметкой: ширина полосы — бирюзовая линия, ширина машины — оранжевая, внизу «№ класс полоса %»
try {
const vw = video.videoWidth, vh = video.videoHeight, g = R.geo; if (!vw || !g) return null;
const pv = g.pivot, sx = vw / R.aw, sy = vh / R.ah, W = (x, y) => { const q = warpFwd(R.p, pv, x, y); return [q[0] * sx, q[1] * sy]; };
const P = [W(b.ux0, b.uy0), W(b.ux1 + 1, b.uy0), W(b.ux0, b.uy1 + 1), W(b.ux1 + 1, b.uy1 + 1)];
let x0 = Math.min(...P.map(q => q[0])), x1 = Math.max(...P.map(q => q[0])), y0 = Math.min(...P.map(q => q[1])), y1 = Math.max(...P.map(q => q[1]));
const mx = (x1 - x0) * 0.3 + 10, my = (y1 - y0) * 0.3 + 10;
x0 = clamp(x0 - mx, 0, vw - 2); x1 = clamp(x1 + mx, x0 + 2, vw); y0 = clamp(y0 - my, 0, vh - 2); y1 = clamp(y1 + my, y0 + 2, vh);
const k = Math.min(3, 220 / (x1 - x0)), w = Math.max(2, Math.round((x1 - x0) * k)), h = Math.max(2, Math.round((y1 - y0) * k)), cv = document.createElement('canvas'); cv.width = Math.max(w, 190); cv.height = h + 22; // дальние (узкие) кропы увеличиваем, чтобы влезла подпись
const x = cv.getContext('2d'); x.drawImage(video, x0, y0, x1 - x0, y1 - y0, 0, 0, w, h);
const N1 = g.N + 1, yy = clamp(Math.round(b.yb), 0, g.ah - 1), A = W(g.xsAt[yy * N1 + b.lane - 1], b.yb), B = W(g.xsAt[yy * N1 + b.lane], b.yb), C0 = W(b.x0, b.yb), C1 = W(b.x1 + 1, b.yb);
const ly = clamp((A[1] - y0) * k, 8, h - 4), X = a => (a - x0) * k;
x.lineWidth = 3; x.strokeStyle = '#3de6d1'; x.beginPath(); x.moveTo(X(A[0]), ly); x.lineTo(X(B[0]), ly); x.stroke();
x.strokeStyle = '#ffab4d'; x.beginPath(); x.moveTo(X(C0[0]), ly - 5); x.lineTo(X(C1[0]), ly - 5); x.stroke();
x.fillStyle = '#000'; x.fillRect(0, h, cv.width, 22); x.fillStyle = '#fff'; x.font = '600 13px system-ui,sans-serif'; x.textBaseline = 'middle';
x.fillText('#' + tr.id + ' ' + cl + ' П' + b.lane + ' · ' + Math.round(wp) + '% полосы', 4, h + 11);
return cv.toDataURL('image/jpeg', 0.72);
} catch (e) { return null; }
},
// ---------- события трекера (через jl) ----------
ev(ev, tr, t, why, ps) {
if (ev === 'revive') { if (tr.dc) tr.dc.revN++; } else if (ev === 'end') this.finish(tr, t, why, ps); // revive = трек терялся и был найден снова
},
reason(tr, why) { // почему трек закончился без результата; нельзя определить точно — UNKNOWN
const tc = CONFIG.track, P = tr.pts, n = P.length, w = String(why || '');
if (tr.dup || w.startsWith('dup')) return 'DUPLICATE';
if (/gap/.test(w)) return 'GAP_RESET';
if (tr.frames < tc.confirmFrames) return 'NO_CONFIRM';
if (!tr.moved) return 'NO_MOVE';
if (!tr.shown && /miss|occluded/.test(w) && n < tc.minShowPts) return 'MISSED_TRACK';
if (n < tc.finalMinPts) return !tr.shown && !(tr.win >= tc.minShowWinSec) && n >= 3 ? 'TOO_SHORT_TIME' : 'TOO_FEW_POINTS';
let f = null; try { f = wlsLine(P, 0, n - 1); } catch (e) { }
if (!f) return 'UNKNOWN';
const kmh = Math.abs(f.slope) * 3.6, path = Math.abs(P[n - 1].s - P[0].s);
if (kmh < tc.minSpeedKmh || kmh > tc.maxSpeedKmh) return 'SPEED_REJECT';
if (!(f.rel <= tc.showErr)) return 'HIGH_ERR';
if (f.rms > tc.finalMaxRmsM) return 'HIGH_RMS';
if (isFinite(tr.minK) && tr.maxK - tr.minK > tc.maxSpreadKmh) return 'SPEED_REJECT';
if (path < tc.minTravelM || (!tr.shown && path < tc.unshownMinPathM)) return 'TOO_SHORT_PATH';
if (!tr.shown) { if (f.rms > tc.unshownMaxRmsM) return 'HIGH_RMS'; if ((tr.carHits || 0) < 3) return 'NO_CONFIRM'; if (f.rel > tc.maxRelErr) return 'HIGH_ERR'; }
return 'UNKNOWN';
},
finish(tr, t, why, ps) {
const tc = CONFIG.track, d = tr.dc, P = tr.pts, n = P.length, F = this.F;
const veh = !tr.dup && tr.moved && tr.frames >= tc.confirmFrames, rs = ps ? 'PASS' : this.reason(tr, why);
this.rs[rs] = (this.rs[rs] || 0) + 1; if (veh) this.rsV[rs] = (this.rsV[rs] || 0) + 1;
const add = (k, rej) => { F[k].n++; if (rej) F[k].rej++; }; // фильтры трекера: условие на момент конца трека (не взаимоисключающие)
if (!tr.dup) { add('confirmFrames', tr.frames < tc.confirmFrames); if (tr.frames >= tc.confirmFrames) add('minMovePx', !tr.moved); }
if (veh) { add('minShowPts', n < tc.minShowPts); add('minShowWinSec', !(tr.win >= tc.minShowWinSec)); add('minShowPath', !(tr.path >= Math.max(tc.minTravelM, tc.minShowPath))); add('finalMinPts', n < tc.finalMinPts); }
this.dirty = true;
if (!veh || !d || !d.S.length) { this.nNoise++; return; }
if (d.late) { this.nLate++; return; }
if (this.recs.length >= 30000) { this.nCap++; return; }
const lc = {}; for (const s of d.S) lc[s[17]] = (lc[s[17]] || 0) + 1;
const lane = +Object.keys(lc).sort((a, b) => lc[b] - lc[a])[0], laneSw = d.S.reduce((n, s, i) => n + (i && s[17] !== d.S[i - 1][17] ? 1 : 0), 0);
const all = d.S.filter(s => s[17] === lane), cl = all.filter(s => s[15]), use = cl.length ? cl : all, col = (i, a) => (a || use).map(s => s[i]);
const zc = {}, zw = {}; for (const s of use) zc[s[13]] = (zc[s[13]] || 0) + 1;
for (const z of this.ZN) { const a = use.filter(s => s[13] === z).map(s => s[0]); zw[z] = a.length ? this.med(a) : NaN; }
const zone = Object.keys(zc).sort((a, b) => zc[b] - zc[a])[0] || '';
const sf = this.num(all.map(s => s[14])), s0 = sf.length ? all.map(s => s[14]).find(isFinite) : NaN, s1 = sf.length ? all.map(s => s[14]).filter(isFinite).pop() : NaN;
const vis = Math.max(0, tr.tLast - tr.t0); let spd = NaN, sp = '';
if (ps) { spd = ps.kmh; sp = 'pass'; } else { let f = null; if (n >= 3) { try { f = wlsLine(P, 0, n - 1); } catch (e) { } } if (f) { spd = Math.abs(f.slope) * 3.6; sp = 'fit'; } else if (isFinite(s0) && isFinite(s1) && vis > 0.05) { spd = Math.abs(s1 - s0) / vis * 3.6; sp = 'est'; } }
const k3 = Math.min(3, all.length), avg = a => a.reduce((x, y) => x + y, 0) / a.length;
const rec = { id: tr.id, t0: tr.t0, vis, frames: tr.frames, cls: this.cls(d), conf: d.maxSc || NaN, detFrac: d.nDet / d.S.length, lane, laneSw, zone,
w: this.med(col(0)), wMax: Math.max(...col(0, all)), wPx: this.med(col(5)), hPx: this.med(col(6)), aPx: this.med(col(7)), bY0: all[0][8], bY1: all[all.length - 1][8], lw: this.med(col(9)), hw: this.med(col(3)), fill: this.med(col(4)),
aP: this.med(col(2)), hP: this.med(col(1)), of: Math.min(...col(11, all)), ownR: Math.min(...col(12, all)), ov: this.med(col(10, all)), ovMax: Math.max(...col(10, all)),
s0, s1, dist: isFinite(s0) && isFinite(s1) ? Math.abs(s1 - s0) : NaN, spd, spdSrc: sp, growth: avg(all.slice(-k3).map(s => s[0])) / Math.max(1e-6, avg(all.slice(0, k3).map(s => s[0]))),
res: rs, pts: n, path: Math.abs(tr.path || 0), lostN: d.revN, endLost: /miss|occluded/.test(String(why || '')) ? 1 : 0, shown: tr.shown ? 1 : 0, clean: cl.length, zw, snap: d.snap ? 1 : 0 };
this.recs.push(rec); if (d.snap) { d.snap.pf = rec.w; d.snap.res = rs; }
},
// ---------- расчёт сводки ----------
curVal(k) { return CONFIG.blob[k] != null ? CONFIG.blob[k] : CONFIG.track[k]; },
calc() {
const R0 = this.recs, tc = CONFIG.track, G = { all: R0 }, K = { n: R0.length, cnt: {}, w: {}, zone: {}, thr: {}, det: {} };
for (const c of this.CLS) G[c] = R0.filter(r => r.cls === c);
G.large = R0.filter(r => r.cls === 'truck' || r.cls === 'bus'); G.unknown = R0.filter(r => !this.CLS.includes(r.cls));
for (const k in G) { K.cnt[k] = G[k].length; K.w[k] = this.dist(G[k].map(r => r.w)); }
for (const z of this.ZN) { K.zone[z] = {}; for (const k of ['all', 'car', 'large']) K.zone[z][k] = this.dist(G[k].map(r => r.zw[z])); }
for (const k of ['car', 'truck', 'bus', 'large']) { const ws = this.num(G[k].map(r => r.w)); K.thr[k] = this.TH.map(T => ws.length ? 100 * ws.filter(x => x >= T).length / ws.length : NaN); }
for (const k of ['car', 'truck', 'bus', 'large']) { const a = G[k]; K.det[k] = { n: a.length, w: K.w[k], wMax: this.dist(a.map(r => r.wMax)), ov: this.dist(a.map(r => r.ov)), ovMax: this.dist(a.map(r => r.ovMax)), of: this.dist(a.map(r => r.of)), vis: this.dist(a.map(r => r.vis)), frames: this.dist(a.map(r => r.frames)), lost: a.length ? a.reduce((x, r) => x + r.lostN, 0) / a.length : NaN, lostTracks: a.filter(r => r.lostN > 0).length, endLost: a.length ? 100 * a.filter(r => r.endLost).length / a.length : NaN }; }
const B = [[0, 0.25, '<0.25 s'], [0.25, 0.5, '0.25–0.5 s'], [0.5, 1, '0.5–1 s'], [1, 2, '1–2 s'], [2, 1e9, '>2 s']], pr = (a, f) => a.length ? 100 * a.filter(f).length / a.length : NaN;
K.fast = B.map(([a, b, name]) => { const r = R0.filter(x => x.vis >= a && x.vis < b); return { name, n: r.length, pct: R0.length ? 100 * r.length / R0.length : 0, pass: pr(r, x => x.res === 'PASS'), spd: this.med(r.map(x => x.spd)), fr: [15, 20, 30].map(f => this.med(r.map(x => x.vis * f + 1))) }; });
const fast = R0.filter(x => x.vis < 0.5);
K.reach = [15, 20, 30].map(f => ({ fps: f, confirm: pr(R0, x => x.vis * f + 1 >= tc.confirmFrames), fin: pr(R0, x => x.vis * f + 1 >= tc.finalMinPts), finFast: pr(fast, x => x.vis * f + 1 >= tc.finalMinPts) }));
K.need = { confirmFrames: tc.confirmFrames, minShowPts: tc.minShowPts, finalMinPts: tc.finalMinPts, fastN: fast.length };
K.rsV = this.rsV; K.rs = this.rs; K.blobRej = this.blobRej; K.nCand = this.nCand; K.nCandDet = this.nCandDet;
K.filters = this.FN.map(k => Object.assign({ name: k, cur: this.curVal(k) }, this.F[k]));
const base = G.car.length >= 10 ? G.car : R0, pc = (f, p) => this.q(this.num(base.map(f)), p);
K.sugBase = base === G.car ? 'cars' : 'all vehicles';
const lo = (cur, v, scale) => ({ cur, p10: v, test: isFinite(v) ? Math.max(0.05, Math.floor(0.7 * v / scale / 0.05) * 0.05) : NaN });
K.sug = { minWidthLane: lo(CONFIG.blob.minWidthLane, pc(r => r.w, 10), 100), minHeightLane: lo(CONFIG.blob.minHeightLane, pc(r => r.hP, 10), 100), minAreaLane2: lo(CONFIG.blob.minAreaLane2, pc(r => r.aP, 10), 100), minFill: lo(CONFIG.blob.minFill, pc(r => r.fill, 10) * 100, 100), ownerFrac: { cur: CONFIG.blob.ownerFrac, p10: this.q(this.num(this.ownR), 10), p1: this.q(this.num(this.ownR), 1), n: this.ownR.length } };
const cp95 = K.w.car.p95, tp50 = K.det.large.w.p50, T = isFinite(cp95) && isFinite(tp50) && tp50 > cp95 ? Math.round((cp95 + tp50) / 2) : (isFinite(K.w.car.p90) ? Math.round(K.w.car.p90) : NaN);
K.wide = { carP95: cp95, largeP50: tp50, T, separable: isFinite(cp95) && isFinite(tp50) && tp50 > cp95, carAbove: T ? pr(G.car, r => r.w >= T) : NaN, largeBelow: T ? pr(G.large, r => r.w < T) : NaN };
return K;
},
// ---------- текст ----------
text(K) {
const L = [], N = x => typeof x === 'number' && isFinite(x), f1 = x => (N(x) ? x.toFixed(1) : '—'), f0 = x => (N(x) ? String(Math.round(x)) : '—'), f2 = x => (N(x) ? x.toFixed(2) : '—');
const pd = (s, n) => String(s).padStart(n), pe = (s, n) => String(s).padEnd(n), HD = pe('', 6) + pd('n', 5) + ['min', 'P10', 'P25', 'P50', 'P75', 'P90', 'P95', 'max'].map(k => pd(k, 6)).join('');
const row = (lb, d) => pe(lb, 6) + pd(d.n, 5) + ['min', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95', 'max'].map(k => pd(f1(d[k]), 6)).join('');
const top = o => Object.entries(o).filter(e => e[0] !== 'PASS').sort((a, b) => b[1] - a[1]), sum = o => Object.values(o).reduce((a, x) => a + x, 0);
const T3 = k => [70, 80, 90].map(T => f0(K.thr[k][this.TH.indexOf(T)])).join('/') + '%';
L.push('=== DATA SUMMARY ===', 'video: ' + (S.fileName || S.srcKind || '—') + ', ' + f0(this.vidSec) + ' s analysed', 'detector classes: ' + (vdGate() ? 'on' : 'OFF (class = unknown)'));
if (K.n && K.cnt.unknown === K.n) L.push('', '!! Detector gave no classes (models not loaded):', '   car/truck/bus split is unavailable.', '   Put the model files into ./models or allow CDN.');
L.push('', 'Vehicles: ' + K.n, 'Cars: ' + K.cnt.car, 'Trucks: ' + K.cnt.truck, 'Buses: ' + K.cnt.bus, 'Motorcycles: ' + K.cnt.motorcycle + (K.cnt.unknown ? '   unclassified: ' + K.cnt.unknown : ''),
'(short/noise tracks ' + this.nNoise + ', warm-up skipped ' + this.nLate + (this.nCap ? ', over cap ' + this.nCap : '') + ')');
L.push('', 'Width % of lane (blob width / lane width', 'at its bottom row; per-track median, clean frames):', HD);
for (const [lb, k] of [['all', 'all'], ['car', 'car'], ['truck', 'truck'], ['bus', 'bus'], ['moto', 'motorcycle']]) L.push(row(lb, K.w[k]));
L.push('', 'Width % by distance zone (thirds of the', 'calibrated zone; FAR = far from camera):', pe('zone', 6) + pe('group', 8) + pd('n', 6) + ['P10', 'P50', 'P90', 'P95'].map(k => pd(k, 6)).join(''));
for (const z of this.ZN) for (const k of ['all', 'car', 'large']) { const d = K.zone[z][k]; L.push(pe(z, 6) + pe(k, 8) + pd(d.n, 6) + [d.p10, d.p50, d.p90, d.p95].map(x => pd(f1(x), 6)).join('')); }
L.push('', 'Retained = share of vehicles with', 'width >= T % of lane:', '   T     car   truck     bus   truck+bus');
this.TH.forEach((T, i) => L.push(pd(T + '%', 4) + [K.thr.car[i], K.thr.truck[i], K.thr.bus[i], K.thr.large[i]].map(x => pd(f0(x) + '%', 8)).join('')));
const Dl = K.det.large, Dc = K.det.car;
L.push('', 'Trucks/buses (n=' + Dl.n + ') vs cars (n=' + Dc.n + '):',
'  width % P50/P90: ' + f1(Dl.w.p50) + ' / ' + f1(Dl.w.p90) + '   cars ' + f1(Dc.w.p50) + ' / ' + f1(Dc.w.p90),
'  width >70/80/90%: ' + T3('large') + '   cars ' + T3('car'),
'  lane overlap % P50/P90: ' + f1(Dl.ov.p50) + ' / ' + f1(Dl.ov.p90) + '   cars ' + f1(Dc.ov.p50) + ' / ' + f1(Dc.ov.p90),
'  owner fraction P10/P50: ' + f2(Dl.of.p10) + ' / ' + f2(Dl.of.p50) + '   cars ' + f2(Dc.of.p10) + ' / ' + f2(Dc.of.p50),
'  visible P50: ' + f2(Dl.vis.p50) + ' s, ' + f0(Dl.frames.p50) + ' frames   cars ' + f2(Dc.vis.p50) + ' s, ' + f0(Dc.frames.p50),
'  lost & re-found per track: ' + f2(Dl.lost) + '   cars ' + f2(Dc.lost),
'  ended by lost blob: ' + f0(Dl.endLost) + '%   cars ' + f0(Dc.endLost) + '%');
const bt = Object.entries(K.blobRej).map(([k, v]) => [k, K.nCandDet >= 20 ? v[1] : v[0]]).filter(e => e[1] > 0).sort((a, b) => b[1] - a[1]), tv = top(K.rsV);
L.push('', 'Largest rejection causes:', ' blob level (' + (K.nCandDet >= 20 ? 'detector-confirmed' : 'ALL candidates, detector off') + ', frames):');
bt.slice(0, 3).forEach((e, i) => L.push('  ' + (i + 1) + '. ' + e[0] + ' = ' + e[1])); if (!bt.length) L.push('  —'); else L.push('  all: ' + bt.map(e => e[0] + ' ' + e[1]).join(', '), '  (first failing filter in code order)');
L.push(' vehicle tracks without speed result', '  (' + (sum(K.rsV) - (K.rsV.PASS || 0)) + ' of ' + sum(K.rsV) + '):'); tv.slice(0, 3).forEach((e, i) => L.push('  ' + (i + 1) + '. ' + e[0] + ' = ' + e[1] + ' (' + f1(100 * e[1] / Math.max(1, sum(K.rsV))) + '%)')); if (!tv.length) L.push('  —'); else L.push('  all: ' + tv.map(e => e[0] + ' ' + e[1]).join(', '));
L.push('', 'Fast tracks (visible time):', '  bin           n     %  pass%  km/h P50  frames@15/20/30');
for (const b of K.fast) L.push('  ' + pe(b.name, 11) + pd(b.n, 5) + pd(f1(b.pct), 6) + pd(f0(b.pass), 6) + pd(f0(b.spd), 9) + '   ' + b.fr.map(x => f1(x)).join('/'));
L.push('  frames needed: confirm ' + K.need.confirmFrames + ', showPts ' + K.need.minShowPts + ', final ' + K.need.finalMinPts, '  (usable points are fewer than frames)');
for (const r of K.reach) L.push('  @' + r.fps + ' fps: confirm ' + f0(r.confirm) + '%, final ' + f0(r.fin) + '%, <0.5 s: ' + f0(r.finFast) + '% (n=' + K.need.fastN + ')');
const frow = o => '  ' + pe(o.name, 14) + pd(o.cur, 6) + pd(o.n, 9) + pd(o.rej, 9) + pd(o.n ? f1(100 * o.rej / o.n) + '%' : '—', 7) + pd(o.sole, 6);
L.push('', 'Current filters, all candidates (checked = blobs/frame', 'after noisePx+merge, or tracks at their end;', 'only = fails ONLY this filter):', '  filter           cur  checked rejected      %  only');
for (const o of K.filters) L.push(frow(o));
L.push('', 'Same, detector-confirmed candidates only:');
const dets = K.filters.filter(o => o.nd); if (!dets.length) L.push('  — (detector off or no candidates)'); else { L.push('  filter           cur  checked rejected      %  only'); for (const o of dets) L.push(frow({ name: o.name, cur: o.cur, n: o.nd, rej: o.rejd, sole: o.soled })); }
const S_ = K.sug, W_ = K.wide;
L.push('', 'Possible runtime changes (CONFIG is NOT changed).', 'Test value = 0.7 x observed P10, floored to 0.05;', 'observed on ' + K.sugBase + ' (per-track median).');
for (const [nm, o] of [['minWidthLane', S_.minWidthLane], ['minHeightLane', S_.minHeightLane], ['minAreaLane2', S_.minAreaLane2], ['minFill', S_.minFill]]) L.push('', nm + ':', ' current = ' + f2(o.cur), ' observed P10 = ' + f2(o.p10 / 100), ' suggested test = ' + f2(o.test));
L.push('', 'ownerFrac:', ' current = ' + f2(S_.ownerFrac.cur), ' owner/largest area in clusters (n=' + S_.ownerFrac.n + '):', ' P1 = ' + f2(S_.ownerFrac.p1) + ', P10 = ' + f2(S_.ownerFrac.p10), ' keep ownerFrac below P1');
L.push('', 'wide vehicle threshold:', ' car P95 = ' + f1(W_.carP95) + '%, truck/bus P50 = ' + f1(W_.largeP50) + '%');
if (W_.separable) L.push(' width separates them; test T ~ ' + f0(W_.T) + '%', ' (cars >=T: ' + f0(W_.carAbove) + '%, trucks/buses <T: ' + f0(W_.largeBelow) + '%)');
else L.push(' width alone does NOT separate them' + (N(W_.T) ? ';' : ' (not enough data)'), N(W_.T) ? ' at T = ' + f0(W_.T) + '% (car P90): cars >=T ' + f0(W_.carAbove) + '%,' : '', N(W_.T) ? ' trucks/buses <T ' + f0(W_.largeBelow) + '%' : '');
L.push('', 'Notes: widths are motion-mask blob widths in the', 'analysis frame, not detector boxes. Class and', 'confidence come from the detector box overlapping', 'the blob. Photos: every ' + this.snapEvery + 'th vehicle (' + this.snaps.length + ' kept).', 'Filter rows: ownerFrac = cluster parts barred from', 'owning the edge; ownerTol = edge ties decided by', 'area; dropFragments = fragments merged into owner;', 'track filters (confirmFrames..finalMinPts) = state', 'at track end, not mutually exclusive.');
return L.filter(x => x !== '' || true).join('\n');
},
// ---------- выгрузка ----------
dl(name, text, mime) {
try { const url = URL.createObjectURL(new Blob([text], { type: mime })); const a = el('a', { href: url, download: name }); document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 8000); } catch (e) { toast('Не удалось сохранить файл.'); }
},
exportCsv() {
if (!this.recs.length) { toast('DATA: пока нет завершённых машин.'); return; }
const cols = ['id', 't0', 'vis', 'frames', 'cls', 'conf', 'detFrac', 'lane', 'laneSw', 'zone', 'w', 'wMax', 'wPx', 'hPx', 'aPx', 'bY0', 'bY1', 'lw', 'hw', 'fill', 'aP', 'hP', 'of', 'ownR', 'ov', 'ovMax', 's0', 's1', 'dist', 'spd', 'spdSrc', 'growth', 'res', 'pts', 'path', 'lostN', 'endLost', 'shown', 'clean', 'snap'];
const hd = ['trackId', 't0_s', 'visible_s', 'frames', 'class', 'confidence', 'detFrac', 'lane', 'laneSwitches', 'zone', 'widthPctLane', 'widthPctLaneMax', 'widthPx', 'heightPx', 'areaPx', 'bottomY_first', 'bottomY_last', 'laneWidthPx', 'height_width', 'fill', 'areaPctLane2', 'heightPctLane', 'ownerFrac_min', 'ownerRatio_min', 'overlapPct_med', 'overlapPct_max', 'dist_start_m', 'dist_end_m', 'distTravelled_m', 'speed_kmh', 'speedSrc', 'sizeGrowth', 'result', 'points', 'path_m', 'lostAndRefound', 'endedByLostBlob', 'shown', 'cleanFrames', 'photo'];
const v = x => (typeof x === 'number' ? (isFinite(x) ? (Math.round(x * 1000) / 1000).toString().replace('.', ',') : '') : (x == null ? '' : String(x)));
const csv = '\uFEFF' + [hd].concat(this.recs.map(r => cols.map(c => v(r[c])))).map(r => r.map(x => (/[;"\n]/.test(x) ? '"' + x.replace(/"/g, '""') + '"' : x)).join(';')).join('\r\n');
this.dl('data-tracks-' + Date.now() + '.csv', csv, 'text/csv;charset=utf-8');
},
exportJson() {
const K = this.calc(), cfg = { blob: CONFIG.blob, track: CONFIG.track, perf: CONFIG.perf };
const o = { meta: { app: 'skorostemer DATA', date: new Date().toISOString(), video: S.fileName || S.srcKind, videoSecAnalysed: this.vidSec, detector: vdGate(), snapEvery: this.snapEvery, config: cfg }, summary: K, summaryText: this.text(K), tracks: this.recs, photos: this.snaps.map(s => ({ id: s.id, cls: s.cls, lane: s.lane, widthPctLive: s.pw, widthPctTrack: s.pf, result: s.res || null, jpeg: s.url })) };
this.dl('data-collection-' + Date.now() + '.json', JSON.stringify(o, (k, x) => (typeof x === 'number' && !isFinite(x) ? null : x)), 'application/json');
},
copy(txt) { try { navigator.clipboard.writeText(txt).then(() => toast('Скопировано.'), () => toast('Не удалось скопировать.')); } catch (e) { toast('Не удалось скопировать.'); } },
// ---------- интерфейс ----------
showSummary() {
const txt = this.text(this.calc()), btn = (t, f) => el('button', { class: 'btn small', type: 'button', onclick: f }, t);
const gal = el('div', { class: 'dcmGal' }); for (const s of this.snaps) gal.append(el('figure', {}, el('img', { src: s.url, alt: '#' + s.id }), el('figcaption', { text: '#' + s.id + ' ' + s.cls + ' П' + s.lane + ' · live ' + Math.round(s.pw) + '%' + (s.pf != null && isFinite(s.pf) ? ' · track ' + Math.round(s.pf) + '%' : '') + (s.res ? ' · ' + s.res : '') })));
openSheet('DATA SUMMARY', el('div', {}, el('div', { class: 'dcmAct' }, btn('Copy', () => this.copy(txt)), btn('CSV', () => this.exportCsv()), btn('JSON', () => this.exportJson())), el('pre', { class: 'dcmPre', text: txt }), this.snaps.length ? el('p', { class: 'fine', text: 'Фото: каждая ' + this.snapEvery + '-я машина (бирюзовая линия — ширина полосы, оранжевая — ширина машины).' }) : null, gal));
},
toggle(v) {
if (v === this.on) return;
this.on = v; $('btnData').classList.toggle('on', v); this.panel.hidden = !v; this.lastFt = null;
if (v) { this.dirty = true; this.paint(); toast('DATA COLLECTION: ON — собираю статистику по ходу воспроизведения.'); } else this.showSummary();
},
paint() {
if (!this.panel || this.panel.hidden) return;
try { const h = $('hud'); if (h && !h.hidden) this.panel.style.top = (h.offsetHeight + 6) + 'px'; } catch (e) { } // панель — строго под рядами кнопок HUD, сколько бы строк они ни заняли
if (this.dirty || !this.cache) { const R0 = this.recs, c = k => R0.filter(r => r.cls === k).length, w = this.dist(R0.map(r => r.w)); const lost = R0.filter(r => r.res !== 'PASS' && r.frames >= CONFIG.track.confirmFrames).length;
const det = this.nCandDet >= 20, bl = this.FN.slice(0, 5).map(k => { const o = this.F[k], n = det ? o.nd : o.n, rj = det ? o.rejd : o.rej; return [k, n ? rj / n : 0, rj, o.sole]; }).sort((a, b) => b[1] - a[1] || b[3] - a[3])[0];
const tl = Object.entries(this.rsV).filter(e => e[0] !== 'PASS').sort((a, b) => b[1] - a[1])[0]; this.cache = { n: R0.length, car: c('car'), truck: c('truck'), bus: c('bus'), moto: c('motorcycle'), w, lost, bl, det, tl }; this.dirty = false; }
const m = this.cache, f = x => (isFinite(x) ? x.toFixed(0) + '%' : '—'), fp = fpsNow();
this.pre.textContent = 'DATA COLLECTION: ON\nTracks: ' + m.n + '  Cars: ' + m.car + '  Trucks: ' + m.truck + '  Buses: ' + m.bus + (m.moto ? '  Moto: ' + m.moto : '') + '\nP50 width/lane: ' + f(m.w.p50) + '   P90: ' + f(m.w.p90) + '   P95: ' + f(m.w.p95) + '\nLost tracks: ' + m.lost + '   Top loss: ' + (m.tl ? m.tl[0] + ' (' + m.tl[1] + ')' : '—') + '\nMain rejection: ' + (m.bl && m.bl[2] ? m.bl[0] + ' (' + (100 * m.bl[1]).toFixed(1) + '%' + (m.det ? ' det' : ' all') + ')' : '—') + '\nPhotos: ' + this.snaps.length + ' (1/' + this.snapEvery + ')   FPS: ' + (fp.src ? fp.src.toFixed(0) : '—') + '/' + (fp.an ? fp.an.toFixed(0) : '—');
},
fail(e) { this.err = (this.err || 0) + 1; try { console.error('DATA:', e); } catch (_) { } if (this.err >= 5 && this.on) { this.on = false; try { $('btnData').classList.remove('on'); this.panel.hidden = true; toast('DATA: внутренняя ошибка, режим выключен (замер не затронут).'); } catch (_) { } } },
guard() { for (const k of ['blob', 'own', 'post', 'ev', 'frame']) { const f = this[k]; this[k] = (...a) => { try { return f.apply(this, a); } catch (e) { this.fail(e); } }; } },
init() {
this.guard();
const css = (t, f) => el('button', { type: 'button', onclick: f }, t);
this.reset(); this.pre = el('pre');
this.snapBtn = css('📷 1/10', () => { this.snapEvery = this.snapEvery === 10 ? 15 : 10; this.snapBtn.textContent = '📷 1/' + this.snapEvery; this.dirty = true; this.paint(); });
this.panel = el('div', { id: 'dcm', hidden: true }, this.pre, el('div', { class: 'dcmRow' }, css('Summary', () => this.showSummary()), css('CSV', () => this.exportCsv()), css('JSON', () => this.exportJson()), this.snapBtn, css('Reset', () => { if (confirm('Очистить собранные данные DATA?')) { this.reset(); this.paint(); } })));
$('stage').append(this.panel);
$('btnData').addEventListener('click', () => this.toggle(!this.on));
setInterval(() => { if (this.on && !document.hidden) this.paint(); }, 700);
}
};
/* ==== DCM:END ==== */'''
# ---- CSS ----
css = """#btnData.on{background:rgba(255,90,95,.3);border-color:var(--bad);color:#ffd9da}
#dcm{position:absolute;left:8px;top:calc(98px + env(safe-area-inset-top));z-index:6;max-width:min(94%,370px);padding:6px 8px;border-radius:10px;background:rgba(10,12,15,.8);border:1px solid rgba(255,90,95,.55);pointer-events:none;-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)}
#dcm pre{margin:0;font:11px/1.38 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#e8edf3;white-space:pre-wrap}
#dcm .dcmRow{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px;pointer-events:auto}
#dcm .dcmRow button{min-height:30px;padding:3px 9px;border-radius:8px;border:1px solid rgba(255,255,255,.25);background:rgba(26,32,39,.92);font-size:11px;font-weight:700}
.dcmAct{display:flex;gap:8px;margin-bottom:10px}
.dcmPre{margin:0 0 10px;font:11.5px/1.38 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre;overflow-x:auto;color:#dfe6ee}
.dcmGal{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.dcmGal figure{margin:0}.dcmGal img{width:100%;border-radius:8px;display:block}.dcmGal figcaption{font-size:11px;color:var(--mut)}
"""
rep("</style>", css + "</style>", 'css')
rep("maxAccel, maxPxMeters.\n", "maxAccel, maxPxMeters.\n\u2022 DATA (\u0440\u0435\u0436\u0438\u043c \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u044f, \u0431\u043b\u043e\u043a DCM, \u0442\u043e\u043b\u044c\u043a\u043e \u0447\u0438\u0442\u0430\u0435\u0442 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u044b \u043a\u043e\u043d\u0432\u0435\u0439\u0435\u0440\u0430, CONFIG \u043d\u0435 \u043c\u0435\u043d\u044f\u0435\u0442): \u0445\u0443\u043a\u0438 DCM.blob/own/post \u0432 MotionDetector.extract, DCM.ev \u0432 jl, DCM.frame \u0432 processFrame;\n\u25e6 \u0431\u043b\u043e\u0431: b.exA, b.ownR; \u0440\u0430\u043c\u043a\u0438 VD.cal: cls, sc; \u0442\u0440\u0435\u043a: tr.dc (\u0432\u044b\u0431\u043e\u0440\u043a\u0438 \u043f\u043e \u043a\u0430\u0434\u0440\u0430\u043c).\n", 'rules note')
# ---- HTML: кнопка DATA ----
rep('<button class="chip btn" id="btnReconf" type="button">⚙ Перенастроить</button>',
    '<button class="chip btn" id="btnReconf" type="button">⚙ Перенастроить</button>\n<button class="chip btn" id="btnData" type="button">DATA</button>', 'btnData')
# ---- детектор машин: класс и уверенность дальше по цепочке (поля добавляются, логика не меняется) ----
rep("out.push({ x0: (b.originX - px) * sx, y0: (b.originY - py) * sy, x1: (b.originX + b.width + px) * sx, y1: (b.originY + b.height + py) * sy });",
    "out.push({ x0: (b.originX - px) * sx, y0: (b.originY - py) * sy, x1: (b.originX + b.width + px) * sx, y1: (b.originY + b.height + py) * sy, cls: d.categories && d.categories[0] ? String(d.categories[0].categoryName || '').toLowerCase() : '', sc: d.categories && d.categories[0] ? d.categories[0].score : null }); // DATA: класс и уверенность", 'vdRun')
rep("return { x0: Math.min(...q.map(a => a[0])), x1: Math.max(...q.map(a => a[0])), y0: Math.min(...q.map(a => a[1])), y1: Math.max(...q.map(a => a[1])) };",
    "return { x0: Math.min(...q.map(a => a[0])), x1: Math.max(...q.map(a => a[0])), y0: Math.min(...q.map(a => a[1])), y1: Math.max(...q.map(a => a[1])), cls: r.cls, sc: r.sc };", 'vdTick')
# ---- extract(): счётчики фильтров и данные «хозяина» кромки ----
rep("const ex = { a: 0, x0: 1e6, x1: -1, y0: 1e6, y1: -1 };", "const ex = { a: 0, x0: 1e6, x1: -1, y0: 1e6, y1: -1, ow: sA[owner] / maxA };", 'ex.ow')
rep("this.extra.set(owner, ex);", "this.extra.set(owner, ex);\nif (DCM.on) DCM.own(arr, sA, bY, owner, maxA, bc);", 'DCM.own')
rep("if (ex) { bl.ux0 = Math.min(bl.ux0, ex.x0); bl.ux1 = Math.max(bl.ux1, ex.x1); bl.uy0 = Math.min(bl.uy0, ex.y0); bl.uy1 = Math.max(bl.uy1, ex.y1); }",
    "if (ex) { bl.ux0 = Math.min(bl.ux0, ex.x0); bl.ux1 = Math.max(bl.ux1, ex.x1); bl.uy0 = Math.min(bl.uy0, ex.y0); bl.uy1 = Math.max(bl.uy1, ex.y1); bl.exA = ex.a; bl.ownR = ex.ow; }", 'bl.exA')
rep("a.area += b.area;", "a.area += b.area; a.exA = (a.exA || 0) + (b.exA || 0); if (b.ownR != null && !(a.ownR <= b.ownR)) a.ownR = b.ownR;", 'merge')
rep("if (b.area < bc.minAreaPx || bw < bc.minWidthLane * lw", "if (DCM.on) DCM.blob(b, lw, bw, bh, bc);\nif (b.area < bc.minAreaPx || bw < bc.minWidthLane * lw", 'DCM.blob')
rep("b.usable = !b.touching && (!b.clipped || b.soft);", "b.usable = !b.touching && (!b.clipped || b.soft);\nif (DCM.on) DCM.post(b, bc, lw);", 'DCM.post')
# ---- события трекера и покадровый сбор ----
rep("function jl(ev, tr, t, why, ps) {\n", "function jl(ev, tr, t, why, ps) {\nif (DCM.on) DCM.ev(ev, tr, t, why, ps);\n", 'jl')
rep("const fin = R.trk.update(blobs, t);\n", "const fin = R.trk.update(blobs, t);\nif (DCM.on) DCM.frame(t);\n", 'frame')
# ---- сам модуль и запуск ----
rep("\ninit();\nvdLoad();", "\n" + dcm + "\n\nDCM.init();\ninit();\nvdLoad();", 'DCM block + init')

open(dst, 'w', encoding='utf-8').write(s)
print('Готово:', dst, '| применено правок:', len(log))
