/**
 * Один прогон сценария codegen: чистый Playwright (без MCP), тот же combined runner, что раньше шёл в
 * ``browser_run_code``, плюс ``context.tracing`` в один заход — без второго прогона ``record_playwright_trace.mjs``.
 *
 * Результат: JSON ``_result.json`` в outputDir, ``traceZipPath`` — нативный trace.zip для видео.
 */
import { mkdirSync, readFileSync, writeFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import { createRequire } from "module";
import vm from "node:vm";
import { chromium, firefox } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

function safeName(uid) {
  return String(uid).replace(/[^a-zA-Z0-9_-]/g, "_");
}

function hasExecutableJs(block) {
  for (const ln of block.split(/\r?\n/)) {
    const t = ln.trim();
    if (!t || t.startsWith("//")) continue;
    return true;
  }
  return false;
}

/**
 * Один async (page) => { ... } со всеми шагами.
 * Все фрагменты шагов — в одной области видимости внутри общего try (не try на шаг):
 * иначе `const x = ...` из READ в одном try недоступен в `.fill(x)` следующего шага (блочная область).
 */
function buildCombinedRunnerCode({ outputDir, steps, postActionWaitSec, prefixCode }) {
  const waitMs = Math.round((postActionWaitSec || 0) * 1000);
  const lines = [];
  lines.push(`async (page) => {`);
  lines.push(`  const context = page.context();`);
  lines.push(`  const request = context.request;`);
  if (prefixCode) {
    lines.push(prefixCode);
  }
  lines.push(`  const __BUGBUSTER_STEP_TIMES = {};`);
  lines.push(`  let __bugbuster_failed_uid = null;`);
  lines.push(`  let __bugbuster_failed_index = -1;`);
  lines.push(`  let __bugbuster_after_abs = null;`);
  lines.push(`  try {`);
  for (let i = 0; i < steps.length; i++) {
    const step = steps[i];
    const su = step.step_uid;
    const codeBlock = step.code || "";
    const bAbs = join(outputDir, `b_${safeName(su)}.jpeg`);
    const aAbs = join(outputDir, `a_${safeName(su)}.jpeg`);
    const suKey = JSON.stringify(String(su));
    lines.push(`  __bugbuster_failed_uid = ${JSON.stringify(String(su))};`);
    lines.push(`  __bugbuster_failed_index = ${i};`);
    lines.push(`  const __t0_${i} = Date.now();`);
    lines.push(`  await page.screenshot({ path: ${JSON.stringify(bAbs)}, type: "jpeg" });`);
    lines.push(`  __bugbuster_after_abs = ${JSON.stringify(aAbs)};`);
    if (hasExecutableJs(codeBlock)) {
      lines.push(codeBlock);
      if (waitMs > 0) {
        lines.push(`  await page.waitForTimeout(${waitMs});`);
      }
    }
    lines.push(`  await page.screenshot({ path: ${JSON.stringify(aAbs)}, type: "jpeg" });`);
    lines.push(`  __BUGBUSTER_STEP_TIMES[${suKey}] = ((Date.now() - __t0_${i}) / 1000).toFixed(2);`);
  }
  lines.push(`  return { ok: true, step_times: __BUGBUSTER_STEP_TIMES };`);
  lines.push(`  } catch (__bugbusterErr) {`);
  lines.push(
    `  const __bugbusterMsg = __bugbusterErr?.stack || __bugbusterErr?.message || String(__bugbusterErr);`,
  );
  lines.push(`  try {`);
  lines.push(
    `    if (__bugbuster_after_abs) { await page.screenshot({ path: __bugbuster_after_abs, type: "jpeg" }); }`,
  );
  lines.push(`  } catch (_) { /* ignore screenshot errors after step failure */ }`);
  lines.push(`  return {`);
  lines.push(`    ok: false,`);
  lines.push(`    failed_step_uid: __bugbuster_failed_uid,`);
  lines.push(`    failed_step_index: __bugbuster_failed_index,`);
  lines.push(`    error: __bugbusterMsg,`);
  lines.push(`    step_times: __BUGBUSTER_STEP_TIMES,`);
  lines.push(`  };`);
  lines.push(`  }`);
  lines.push(`}`);
  return lines.join("\n");
}

const cfgPath = process.argv[2];
if (!cfgPath) {
  console.error("config json path required");
  process.exit(2);
}

const cfg = JSON.parse(readFileSync(cfgPath, "utf8"));
const {
  startUrl = "about:blank",
  outputDir,
  steps = [],
  postActionWaitSec = 0,
  prefixCode = "",
  browser: cfgBrowser = "chrome",
  desktopChromeUserAgent = "",
  traceZipPath = "",
} = cfg;

const mcpBrowser =
  String(cfgBrowser || "chrome").toLowerCase().trim() === "firefox"
    ? "firefox"
    : "chrome";
const viewportW = Number(cfg.viewportW);
const viewportH = Number(cfg.viewportH);

if (!outputDir || !steps.length) {
  console.error("outputDir and steps required");
  process.exit(2);
}

if (!traceZipPath || !String(traceZipPath).trim()) {
  console.error("traceZipPath required (native trace in same run as scenario)");
  process.exit(2);
}

mkdirSync(outputDir, { recursive: true });
mkdirSync(dirname(traceZipPath), { recursive: true });
const resultPath = join(outputDir, "_result.json");

function writeResult(obj) {
  writeFileSync(resultPath, JSON.stringify(obj, null, 0));
}

if (
  !Number.isFinite(viewportW) ||
  !Number.isFinite(viewportH) ||
  viewportW <= 0 ||
  viewportH <= 0
) {
  const msg = `viewportW and viewportH must be positive numbers from test case environment (got viewportW=${JSON.stringify(cfg.viewportW)}, viewportH=${JSON.stringify(cfg.viewportH)})`;
  writeResult({ ok: false, error: msg });
  console.error(msg);
  process.exit(2);
}

const chromeDesktopUa =
  String(desktopChromeUserAgent || "").trim() ||
  String(process.env.PLAYWRIGHT_MCP_USER_AGENT || "").trim();

const prefixTrim = String(prefixCode || "").trim();
const runCode = buildCombinedRunnerCode({
  outputDir,
  steps,
  postActionWaitSec,
  prefixCode: prefixTrim,
});

const shots = [];
for (const step of steps) {
  const su = step.step_uid;
  shots.push({
    step_uid: su,
    phase: "before",
    file: `b_${safeName(su)}.jpeg`,
  });
  shots.push({
    step_uid: su,
    phase: "after",
    file: `a_${safeName(su)}.jpeg`,
  });
}

let browser;
let context;
/** @type {import("playwright").Page | undefined} */
let page;

try {
  const { expect } = require("@playwright/test");
  globalThis.expect = expect;

  if (mcpBrowser === "firefox") {
    browser = await firefox.launch({ headless: true });
  } else {
    browser = await chromium.launch({
      channel: "chrome",
      headless: true,
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    });
  }

  const ctxOpts = {
    viewport: { width: viewportW, height: viewportH },
  };
  if (mcpBrowser === "chrome" && chromeDesktopUa) {
    ctxOpts.userAgent = chromeDesktopUa;
  }
  context = await browser.newContext(ctxOpts);

  await context.tracing.start({
    screenshots: true,
    snapshots: true,
    sources: true,
    screencastOptions: { width: viewportW, height: viewportH, quality: 90 },
  });

  page = await context.newPage();

  if (!prefixTrim) {
    await page.goto(startUrl || "about:blank", {
      waitUntil: "domcontentloaded",
      timeout: 120_000,
    });
  }

  let fn;
  try {
    const sandbox = Object.create(null);
    Object.assign(sandbox, {
      console, setTimeout, clearTimeout, setInterval, clearInterval,
      Promise, URL, URLSearchParams, Buffer, JSON, Math, Date,
      RegExp, Array, Object, String, Number, Boolean, Error, TypeError, RangeError,
      Map, Set, WeakMap, WeakSet, Symbol,
      parseInt, parseFloat, isNaN, isFinite, Infinity, NaN, undefined,
      encodeURIComponent, decodeURIComponent, encodeURI, decodeURI,
      atob, btoa, expect: globalThis.expect,
    });
    vm.createContext(sandbox);
    fn = vm.runInNewContext(`(${runCode})`, sandbox);
  } catch (e) {
    writeResult({ ok: false, error: `invalid runner: ${e?.message || e}` });
    process.exit(1);
  }

  const tRun0 = Date.now();
  const runnerResult = await fn(page);
  const runSec = (Date.now() - tRun0) / 1000;

  if (runnerResult && runnerResult.ok === false) {
    const tailMs = Number(process.env.PLAYWRIGHT_TRACE_TAIL_MS || 300);
    if (page && !page.isClosed() && tailMs > 0) {
      await new Promise((r) => setTimeout(r, tailMs));
    }

    await context.tracing.stop({ path: traceZipPath });
    await browser.close();

    const partial = runnerResult.step_times && typeof runnerResult.step_times === "object" && !Array.isArray(runnerResult.step_times)
      ? runnerResult.step_times
      : {};
    writeResult({
      ok: false,
      error: runnerResult.error || "step failed",
      failed_step_uid: runnerResult.failed_step_uid,
      failed_step_index: runnerResult.failed_step_index,
      shots,
      step_times: partial,
      run_sec_total: runSec,
      step_times_fallback: false,
    });
    process.exit(1);
  }

  const stepTimesRaw = runnerResult && runnerResult.step_times ? runnerResult.step_times : runnerResult;

  const n = steps.length;
  let stepTimes = stepTimesRaw;
  let stepTimesFallback = false;
  if (!stepTimes || typeof stepTimes !== "object" || Array.isArray(stepTimes) || Object.keys(stepTimes).length === 0) {
    stepTimesFallback = true;
    stepTimes = {};
    const per = n > 0 ? (runSec / n).toFixed(2) : "0.00";
    for (const step of steps) {
      stepTimes[String(step.step_uid)] = per;
    }
  }

  const tailMs = Number(process.env.PLAYWRIGHT_TRACE_TAIL_MS || 300);
  if (page && !page.isClosed() && tailMs > 0) {
    await new Promise((r) => setTimeout(r, tailMs));
  }

  await context.tracing.stop({ path: traceZipPath });
  await browser.close();

  writeResult({
    ok: true,
    shots,
    step_times: stepTimes,
    run_sec_total: runSec,
    step_times_fallback: stepTimesFallback,
  });
  process.exit(0);
} catch (e) {
  const msg = e?.stack || e?.message || String(e);
  console.error(msg);
  try {
    if (context) {
      await context.tracing.stop({ path: traceZipPath }).catch(() => {});
    }
  } catch {
    /* ignore */
  }
  try {
    if (browser) await browser.close();
  } catch {
    /* ignore */
  }
  writeResult({ ok: false, error: msg });
  process.exit(1);
}
