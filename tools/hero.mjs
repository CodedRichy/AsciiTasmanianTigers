// One animal, frozen, large and side-on, at 4 gait phases: the image a critic judges.
import { chromium } from "playwright";
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1400, height: 800 }, deviceScaleFactor: 2 });
p.on("pageerror", (e) => console.log("ERR", e.message));
await p.goto("http://127.0.0.1:5199/index.html");
await p.waitForTimeout(1200);
await p.evaluate(() => {
  animals.length = 1;
  Object.assign(animals[0], { gy: 0.96, gyT: 0.96, hs: 0.3, x: 760, psi: Math.PI, face: Math.PI, dir: -1, sc: 1, m: 1, mode: "walk", timer: 1e9, turnT: 1e9, depthT: 1e9 });
  window.update = () => {};
});
for (const [i, ph] of [0, 0.25, 0.5, 0.75].entries()) {
  await p.evaluate((ph) => { animals[0].ph = ph; }, ph);
  await p.waitForTimeout(80);
  await p.screenshot({ path: `hero_${i}.png`, clip: { x: 300, y: 430, width: 1100, height: 370 } });
}
await b.close();
