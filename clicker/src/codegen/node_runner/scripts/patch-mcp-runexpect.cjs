/**
 * Playwright MCP `browser_run_code` исполняет строку в `vm.createContext({ page, __end__ })`.
 * В sandbox нет `require`/`import`, поэтому артефакты с `expect()` из @playwright/test дают
 * ReferenceError. Подмешиваем `expect` в объект контекста (загрузка в Node, не в VM).
 */
const fs = require("fs");
const path = require("path");

const PATCH_TAG = "BUGBUSTER_EXPECT_PATCH";
const target = path.join(
  __dirname,
  "..",
  "node_modules",
  "playwright",
  "lib",
  "mcp",
  "browser",
  "tools",
  "runCode.js",
);

const NEEDLE = `    const __end__ = new import_utils.ManualPromise();
    const context = {
      page: tab.page,
      __end__
    };
    import_vm.default.createContext(context);`;

const REPLACEMENT = `    const __end__ = new import_utils.ManualPromise();
    // ${PATCH_TAG}: expect для codegen/playwright_js (иначе ReferenceError в VM)
    const { expect } = require("@playwright/test");
    const context = {
      page: tab.page,
      __end__,
      expect
    };
    import_vm.default.createContext(context);`;

function main() {
  if (!fs.existsSync(target)) {
    console.error("patch-mcp-runexpect: missing", target);
    process.exit(1);
  }
  let s = fs.readFileSync(target, "utf8");
  if (s.includes(PATCH_TAG)) {
    return;
  }
  if (!s.includes(NEEDLE)) {
    console.error(
      "patch-mcp-runexpect: runCode.js layout changed; update NEEDLE in patch-mcp-runexpect.cjs",
    );
    process.exit(1);
  }
  s = s.replace(NEEDLE, REPLACEMENT);
  fs.writeFileSync(target, s, "utf8");
}

main();
