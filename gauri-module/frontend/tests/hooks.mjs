import { existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export async function resolve(specifier, context, nextResolve) {
  let target = specifier;
  if (specifier.startsWith("@/")) target = pathToFileURL(path.join(root, specifier.slice(2))).href;
  else if (specifier.startsWith(".") && context.parentURL) target = new URL(specifier, context.parentURL).href;
  else return nextResolve(specifier, context);

  if (!/\.(m?js|ts|json)$/.test(target)) {
    for (const ext of [".ts", "/index.ts"]) {
      const p = fileURLToPath(target + ext);
      if (existsSync(p)) return nextResolve(pathToFileURL(p).href, context);
    }
  }
  return nextResolve(target, context);
}
