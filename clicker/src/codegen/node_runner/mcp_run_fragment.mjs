/**
 * Валидация фрагмента codegen через [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp):
 * Stdio MCP client → tools browser_navigate + browser_run_code (+ опционально screenshot при ошибке).
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { readFileSync, writeFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const mcpCli = join(__dirname, "node_modules", "@playwright", "mcp", "cli.js");

const startUrl = process.env.CODEGEN_START_URL || "";
const w = parseInt(process.env.CODEGEN_VIEWPORT_W || "1920", 10);
const h = parseInt(process.env.CODEGEN_VIEWPORT_H || "1080", 10);
const failShot = process.env.CODEGEN_FAILSHOT || "";
/** Playwright MCP --browser: chrome | firefox */
const mcpBrowser =
  (process.env.CODEGEN_BROWSER || "chrome").toLowerCase().trim() === "firefox"
    ? "firefox"
    : "chrome";
const scriptPath = process.argv[2];

if (!scriptPath) {
  console.error("script path required");
  process.exit(2);
}

const body = readFileSync(scriptPath, "utf8");
// expect в sandbox browser_run_code: postinstall scripts/patch-mcp-runexpect.cjs (динамический import() в vm нельзя).
const runCode = `async (page) => {
  const context = page.context();
  const request = context.request;
${body}
}`;

function toolText(res) {
  const parts = res?.content || [];
  return parts
    .filter((c) => c.type === "text")
    .map((c) => c.text)
    .join("\n");
}

/** Тело секции ### Result в ответе Playwright MCP — без markdown «Ran Playwright code». */
function extractMcpResultSection(fullText) {
  const marker = "### Result";
  const idx = fullText.indexOf(marker);
  if (idx < 0) return null;
  let body = fullText.slice(idx + marker.length).replace(/^\s*\n?/, "");
  const next = body.search(/\n### /);
  if (next >= 0) body = body.slice(0, next);
  body = body.trim();
  return body || null;
}

async function writeAccessibilitySnapshot(client, failShot) {
  if (!failShot || !client) return;
  try {
    const snap = await client.callTool({
      name: "browser_snapshot",
      arguments: {},
    });
    if (snap.isError) return;
    const raw = toolText(snap) || "";
    if (!raw) return;
    const maxLen = 120_000;
    const text =
      raw.length > maxLen
        ? `${raw.slice(0, maxLen)}\n...truncated (${raw.length} chars)`
        : raw;
    const outPath = failShot.replace(/\.(jpe?g|png)$/i, "") + ".a11y.txt";
    writeFileSync(outPath, text, "utf8");
  } catch {
    /* optional */
  }
}

/**
 * Снимок через Playwright Page API (не browser_take_screenshot MCP — тот же визуальный рендер, что у исполняемого кода).
 */
async function writePlaywrightPageFailshot(client, failShot) {
  if (!failShot || !client) return;
  const abs = failShot;
  try {
    const run = await client.callTool({
      name: "browser_run_code",
      arguments: {
        code: `async (page) => {
  await page.screenshot({ path: ${JSON.stringify(abs)}, type: "jpeg", quality: 72 });
}`,
      },
    });
    if (run.isError) {
      /* fallback: MCP screenshot if page.screenshot failed */
      await client.callTool({
        name: "browser_take_screenshot",
        arguments: { type: "jpeg", filename: failShot },
      });
    }
  } catch {
    try {
      await client.callTool({
        name: "browser_take_screenshot",
        arguments: { type: "jpeg", filename: failShot },
      });
    } catch {
      /* ignore */
    }
  }
}

/** Серийный HTML страницы после ошибки (page.content) — sidecar для LLM repair. */
async function writePageHtmlDump(client, failShot) {
  if (!failShot || !client) return;
  try {
    const run = await client.callTool({
      name: "browser_run_code",
      arguments: {
        code: `async (page) => {
  const html = await page.content();
  const max = 500000;
  if (html.length > max) {
    return html.slice(0, max) + "\\n...truncated (" + html.length + " chars total)";
  }
  return html;
}`,
      },
    });
    if (run.isError) return;
    const raw = toolText(run) || "";
    if (!raw) return;
    const html = extractMcpResultSection(raw) ?? raw;
    const outPath = failShot.replace(/\.(jpe?g|png)$/i, "") + ".page.html";
    writeFileSync(outPath, html, "utf8");
  } catch {
    /* optional */
  }
}

async function writeRepairSidecars(client, failShot) {
  await writeAccessibilitySnapshot(client, failShot);
  await writePageHtmlDump(client, failShot);
}

const MCP_CONNECT_TIMEOUT_MS = parseInt(process.env.CODEGEN_MCP_CONNECT_TIMEOUT_MS || "30000", 10);
const MCP_TOOL_TIMEOUT_MS = parseInt(process.env.CODEGEN_MCP_TOOL_TIMEOUT_MS || "120000", 10);

function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`${label} timed out after ${ms}ms`)), ms),
    ),
  ]);
}

let client;
try {
  const chromeDesktopUa = String(process.env.PLAYWRIGHT_MCP_USER_AGENT || "").trim();
  const mcpArgs = [
    mcpCli,
    "--headless",
    "--browser",
    mcpBrowser,
    "--no-sandbox",
    "--isolated",
    "--viewport-size",
    `${w}x${h}`,
  ];
  if (mcpBrowser === "chrome" && chromeDesktopUa) {
    mcpArgs.push("--user-agent", chromeDesktopUa);
  }
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: mcpArgs,
    env: { ...process.env },
  });
  client = new Client({ name: "bugbuster-codegen", version: "1.0.0" });
  await withTimeout(client.connect(transport), MCP_CONNECT_TIMEOUT_MS, "client.connect");

  const nav = await withTimeout(
    client.callTool({ name: "browser_navigate", arguments: { url: startUrl || "about:blank" } }),
    MCP_TOOL_TIMEOUT_MS,
    "browser_navigate",
  );
  if (nav.isError) {
    console.error(toolText(nav) || "browser_navigate failed");
    process.exit(1);
  }

  const run = await withTimeout(
    client.callTool({ name: "browser_run_code", arguments: { code: runCode } }),
    MCP_TOOL_TIMEOUT_MS,
    "browser_run_code",
  );
  if (run.isError) {
    const msg = toolText(run) || "browser_run_code failed";
    if (failShot) {
      await writePlaywrightPageFailshot(client, failShot);
      await writeRepairSidecars(client, failShot);
    }
    console.error(msg);
    process.exit(1);
  }
  if (failShot) {
    await writePageHtmlDump(client, failShot);
  }
  await client.close();
  process.exit(0);
} catch (e) {
  const msg = e?.message || e?.toString?.() || String(e);
  if (failShot && client) {
    await writePlaywrightPageFailshot(client, failShot);
    await writeRepairSidecars(client, failShot);
    try {
      await client.close();
    } catch {
      /* ignore */
    }
  }
  console.error(msg);
  process.exit(1);
}
