import { chromium } from "playwright";
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1400, height: 800 }, deviceScaleFactor: 1 });
p.on("pageerror", (e) => console.log("ERR", e.message));
await p.goto("http://127.0.0.1:5199/index.html");
await p.waitForTimeout(1200);
await p.evaluate(() => {
  animals.length = 1;
  Object.assign(animals[0], { gy: 0.96, gyT: 0.96, hs: 0.3, x: 760, psi: Math.PI, face: Math.PI, dir: -1, sc: 1, m: 1, mode: "walk", timer: 1e9, turnT: 1e9, depthT: 1e9 });
  window.update = () => {};
});
for (let i = 0; i < 8; i++) {
  await p.evaluate((ph) => { animals[0].ph = ph; }, i / 8);
  await p.waitForTimeout(60);
  await p.screenshot({ path: `tail_${i}.png`, clip: { x: 900, y: 520, width: 480, height: 200 } });
}
await b.close();
