/**
 * Одна сессия браузера: goto(start_url), затем исполнение тела скрипта (строки JS с await page...).
 * При ошибке — JPEG во временный путь из CODEGEN_FAILSHOT.
 */
import { chromium, firefox } from "playwright";
import { expect } from "@playwright/test";
import { readFileSync } from "fs";
import vm from "node:vm";

const url = process.env.CODEGEN_START_URL || "";
const w = parseInt(process.env.CODEGEN_VIEWPORT_W || "1920", 10);
const h = parseInt(process.env.CODEGEN_VIEWPORT_H || "1080", 10);
const failShot = process.env.CODEGEN_FAILSHOT || "";
const b = (process.env.CODEGEN_BROWSER || "chrome").toLowerCase().trim();
const useFirefox = b === "firefox";
const scriptPath = process.argv[2];

if (!url || !scriptPath) {
  console.error("CODEGEN_START_URL and script path required");
  process.exit(2);
}

const body = readFileSync(scriptPath, "utf8");
const browser = useFirefox
  ? await firefox.launch({ headless: true })
  : await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({ viewport: { width: w, height: h } });
const page = await context.newPage();

try {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });
  const sandbox = Object.create(null);
  Object.assign(sandbox, {
    page, context, expect,
    console, setTimeout, clearTimeout, setInterval, clearInterval,
    Promise, URL, URLSearchParams, Buffer, JSON, Math, Date,
    RegExp, Array, Object, String, Number, Boolean, Error, TypeError, RangeError,
    Map, Set, WeakMap, WeakSet, Symbol,
    parseInt, parseFloat, isNaN, isFinite, Infinity, NaN, undefined,
    encodeURIComponent, decodeURIComponent, encodeURI, decodeURI,
    atob, btoa,
  });
  vm.createContext(sandbox);
  await vm.runInNewContext(`
    (async () => {
      const request = context.request;
      ${body}
    })()
  `, sandbox);
  await browser.close();
  process.exit(0);
} catch (e) {
  const msg = e?.message || String(e);
  if (failShot) {
    try {
      await page.screenshot({ path: failShot, type: "jpeg", quality: 72 });
    } catch {
      /* ignore */
    }
  }
  console.error(msg);
  try {
    await browser.close();
  } catch {
    /* ignore */
  }
  process.exit(1);
}
