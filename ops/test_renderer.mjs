// Renderer smoke test. Runs in JSDOM. Fast (~1s) and dependency-light.
//
// What it verifies:
//   1. The rendered HTML parses and the bootstrap script does not throw.
//   2. Every step viz advertised by SKILL §3.1 dispatches to a distinct
//      renderer that produces non-empty SVG (so a future edit can not
//      silently drop a case from the switch in `renderStep`).
//   3. `pickStepViz` classifies common shapes when `viz` is absent.
//   4. The prev/next nav buttons disable correctly at flow boundaries.
//
// Run:
//   node ops/test_renderer.mjs
//
// CI gate: exits non-zero on the first failed assertion.

import pkg from "jsdom";
const { JSDOM, VirtualConsole } = pkg;
import { execFileSync } from "node:child_process";
import { readFileSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const FIXTURE = resolve(HERE, "test_renderer.fixture.json");

const out = mkdtempSync(join(tmpdir(), "codestory-test-")) + "/render.html";
execFileSync("python3", [resolve(ROOT, "ops/render.py"),
  "--theme", "cococream", "--data", FIXTURE, "--out", out],
  { stdio: ["ignore", "ignore", "inherit"] });

const errors = [];
const dom = new JSDOM(readFileSync(out, "utf8"), {
  runScripts: "dangerously",
  pretendToBeVisual: true,
  url: "http://localhost/codestory.html",
  virtualConsole: new VirtualConsole().on("jsdomError", (e) => errors.push(String(e))),
});
const proto = dom.window.SVGElement?.prototype;
if (proto) {
  if (!proto.getTotalLength) proto.getTotalLength = function () { return 100; };
  if (!proto.getPointAtLength) proto.getPointAtLength = function () { return { x: 0, y: 0 }; };
}
await new Promise((r) => setTimeout(r, 50));
const w = dom.window, doc = w.document;

const fails = [];
const ok = (cond, msg) => { if (!cond) fails.push(msg); };

// 1. Bootstrap did not throw.
ok(errors.length === 0, "renderer threw during init: " + errors.join(" | "));

// 2. Home page rendered four chapter cards.
ok(doc.querySelectorAll(".cat").length === 4, "expected 4 chapter cards");

// 3. Nav buttons exist.
ok(doc.getElementById("btn-prev") && doc.getElementById("btn-next"),
   "prev/next buttons missing from player toolbar");

// 4. Walk every scene of `all-viz`, confirm each step produces a non-empty
//    SVG group and emits the expected `data-viz` badge in switch order.
function visit(hash) {
  w.location.hash = hash;
  w.dispatchEvent(new w.HashChangeEvent("hashchange"));
}
function step(n) {
  for (let i = 0; i < n; i++) {
    w.dispatchEvent(new w.KeyboardEvent("keydown", { key: "ArrowRight" }));
  }
}

const EXPECTED = ["hop","self","queue","broadcast","notification","db-write","db-read","pipeline","state","screenshot"];
visit("#flow=all-viz");
await new Promise((r) => setTimeout(r, 20));
// Nav buttons should be disabled in the overview view.
ok(doc.getElementById("btn-prev").disabled, "prev should be disabled in overview");
ok(doc.getElementById("btn-next").disabled, "next should be disabled in overview");

const seen = [];
for (let i = 0; i < EXPECTED.length + 1; i++) {
  step(1);
  const viz = doc.getElementById("step-label")?.dataset?.viz;
  const sceneSvg = doc.getElementById("scene-content");
  ok(sceneSvg && sceneSvg.children.length > 0, `scene ${i + 1} produced empty SVG (viz=${viz})`);
  if (viz && viz !== "intro" && viz !== "outro") seen.push(viz);
}
for (const v of EXPECTED) {
  ok(seen.includes(v), `viz '${v}' was never dispatched (saw: ${seen.join(", ")})`);
}

// 5. Chooser test: walk `chooser-test` whose steps omit `viz`, confirm
//    `pickStepViz` picks db-write, db-read, queue, notification in order.
visit("#flow=chooser-test");
await new Promise((r) => setTimeout(r, 20));
const chooser = [];
for (let i = 0; i < 4; i++) {
  step(1);
  const viz = doc.getElementById("step-label")?.dataset?.viz;
  if (viz && viz !== "intro" && viz !== "outro") chooser.push(viz);
}
const want = ["db-write", "db-read", "queue", "notification"];
ok(JSON.stringify(chooser) === JSON.stringify(want),
   `chooser misfired: got ${JSON.stringify(chooser)}, want ${JSON.stringify(want)}`);

// 6. Nav buttons gate at flow boundaries.
visit("#flow=all-viz");
await new Promise((r) => setTimeout(r, 20));
step(1); // overview → scene 0
ok(!doc.getElementById("btn-prev").disabled, "prev should be enabled at scene 0");
ok(!doc.getElementById("btn-next").disabled, "next should be enabled mid-flow");
step(100); // walk past the end
ok(doc.getElementById("btn-next").disabled, "next should be disabled at the outro");

if (fails.length) {
  console.error("FAIL:");
  fails.forEach((f) => console.error("  -", f));
  process.exit(1);
}
console.log(`ok: renderer smoke (${EXPECTED.length} viz types dispatched, ${chooser.length} chooser cases)`);
