// Lets `node --experimental-strip-types` run the extensionless TS imports used in the Next.js code.
//   node --experimental-strip-types --import ./tests/register.mjs --test tests/*.test.ts
import { register } from "node:module";
register("./hooks.mjs", import.meta.url);
