// Builds demo/vyapaar_sathi_demo.html: ONE self-contained file (no install, no API keys) that runs the
// real parser / context / insights / readiness modules in the browser.
//   node scripts/build-demo.mjs
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const outDir = path.resolve(root, "../demo");

// dependency order matters: later modules use earlier ones' top-level names
const MODULES = ["dates", "numbers", "sanity", "ruleParser", "context", "readiness", "ledgerStats", "insightRules"];

const bundle = MODULES.map((name) => {
  const src = readFileSync(path.join(root, "lib/ai", `${name}.ts`), "utf8");
  const js = stripTypeScriptTypes(src, { mode: "strip" })
    .replace(/^import[^;]*;\s*$/gm, "") // single-statement imports (all ours are one-liners)
    .replace(/^export (?=(const|function|class|let|async))/gm, "");
  if (/^\s*(import|export)\b/m.test(js)) throw new Error(`${name}: leftover import/export after stripping`);
  return `// ---- ${name} ----\n${js}`;
}).join("\n");

const template = readFileSync(path.join(here, "demo.template.html"), "utf8");
if (!template.includes("/*__BUNDLE__*/")) throw new Error("template placeholder missing");
mkdirSync(outDir, { recursive: true });
const out = path.join(outDir, "vyapaar_sathi_demo.html");
writeFileSync(out, template.replace("/*__BUNDLE__*/", () => bundle));
console.log("wrote", out, `(${Math.round(bundle.length / 1024)} KB of logic)`);
