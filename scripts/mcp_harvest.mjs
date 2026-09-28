#!/usr/bin/env node
// Enumerate every registry's items through the official shadcn MCP server
// (`npx shadcn mcp`, tool `list_items_in_registries`, limit 0 = all).
// Registries must be declared in components.json (generated from
// https://ui.shadcn.com/r/registries.json -> data/raw/public_registries_index.json).
//
// Output: data/raw/mcp/<handle>.json  { handle, ok, error, total, rawText, fetchedAt }
// Resumable: skips handles whose file already has ok=true (pass --force to redo).
// Usage: node scripts/mcp_harvest.mjs [--only @a,@b] [--force] [--concurrency 6]
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const OUT = path.join(ROOT, "data/raw/mcp");
const args = process.argv.slice(2);
const flag = (n) => args.includes(n);
const opt = (n, d) => (args.includes(n) ? args[args.indexOf(n) + 1] : d);
const CONC = Number(opt("--concurrency", 6));
const only = opt("--only", null)?.split(",");

const cj = JSON.parse(fs.readFileSync(path.join(ROOT, "components.json"), "utf8"));
let handles = Object.keys(cj.registries);
if (only) handles = handles.filter((h) => only.includes(h));
if (!flag("--force"))
  handles = handles.filter((h) => {
    const f = path.join(OUT, `${h.slice(1)}.json`);
    return !(fs.existsSync(f) && JSON.parse(fs.readFileSync(f, "utf8")).ok);
  });
fs.mkdirSync(OUT, { recursive: true });
console.log(`harvesting ${handles.length} registries via shadcn MCP (concurrency ${CONC})`);

const transport = new StdioClientTransport({ command: "npx", args: ["shadcn@latest", "mcp"], cwd: ROOT, stderr: "ignore" });
const client = new Client({ name: "registry-harvest", version: "1.0.0" });
await client.connect(transport);

let done = 0, ok = 0;
async function harvest(h) {
  const rec = { handle: h, ok: false, error: null, total: null, rawText: "", fetchedAt: new Date().toISOString() };
  try {
    const r = await client.callTool(
      { name: "list_items_in_registries", arguments: { registries: [h], limit: 0 } },
      undefined,
      { timeout: 120000 }
    );
    const text = (r.content || []).map((p) => p.text || "").join("\n");
    rec.rawText = text;
    const m = text.match(/^Found (\d+) items/m);
    if (r.isError || !m) rec.error = text.slice(0, 500) || "empty response";
    else { rec.ok = true; rec.total = Number(m[1]); }
  } catch (e) {
    rec.error = String(e?.message || e).slice(0, 500);
  }
  fs.writeFileSync(path.join(OUT, `${h.slice(1)}.json`), JSON.stringify(rec, null, 1));
  done++; if (rec.ok) ok++;
  console.log(`[${done}/${handles.length}] ${h} ${rec.ok ? rec.total + " items" : "ERR " + rec.error.split("\n")[0].slice(0, 120)}`);
}

const queue = [...handles];
await Promise.all(Array.from({ length: CONC }, async () => { while (queue.length) await harvest(queue.shift()); }));
await client.close();
console.log(`done: ${ok}/${handles.length} ok`);
