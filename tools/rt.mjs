import { chromium } from "playwright";
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1400, height: 800 }, deviceScaleFactor: 2 });
p.on("pageerror", (e) => console.log("ERR", e.message));
await p.goto("http://127.0.0.1:5199/index.html");
await p.waitForTimeout(1500);
await p.screenshot({ path: "rt_full.png" });
for (const i of [1, 2, 3, 4]) {
  await p.waitForTimeout(i === 1 ? 10 : 230);
  const a = await p.evaluate(() => { const a = animals.reduce((m, x) => (x.gy > m.gy ? x : m)); return { x: a.x, gy: a.gy * innerHeight, u: a.hs * innerHeight, dir: a.dir, ph: a.ph, mode: a.mode }; });
  const k = a.u / ROTO_SH();
  const x0 = Math.max(0, a.x - 3.2 * a.u), y0 = Math.max(0, a.gy - 1.7 * a.u);
  const clip = { x: x0, y: y0, width: Math.min(1400 - x0, 6.4 * a.u), height: Math.min(800 - y0, 1.95 * a.u) };
  await p.screenshot({ path: `rt_c${i}.png`, clip });
  console.log(i, a.mode, "ph", a.ph.toFixed(2), "dir", a.dir);
}
const fps = await p.evaluate(() => new Promise((res) => { let n = 0; const t0 = performance.now(); const f = () => { n++; if (performance.now() - t0 < 3000) requestAnimationFrame(f); else res(n / 3); }; requestAnimationFrame(f); }));
console.log("fps", fps.toFixed(1));
await b.close();
function ROTO_SH() { return 61; }
