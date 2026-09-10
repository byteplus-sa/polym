import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import { parseArgs as parseNodeArgs } from "node:util";


function parseArgs(argv) {
  return parseNodeArgs({
    args: argv,
    options: {
      source: { type: "string" },
      slides: { type: "string" },
      output: { type: "string" },
    },
    allowPositionals: false,
    strict: true,
  }).values;
}


function requiredString(args, key) {
  const value = args[key];
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`Missing required --${key}`);
  }
  return value;
}


function selectedSlideNumbers(value) {
  const numbers = value.split(",").map((item) => Number.parseInt(item.trim(), 10));
  if (numbers.length === 0 || numbers.some((number) => !Number.isInteger(number) || number < 1)) {
    throw new Error("--slides must be a comma-separated list of positive slide numbers");
  }
  return numbers;
}


async function artifactTool() {
  const nodeModules = process.env.RUNTIME_NODE_MODULES;
  if (!nodeModules || !path.isAbsolute(nodeModules)) {
    throw new Error("RUNTIME_NODE_MODULES must be an absolute path");
  }
  const requireFromRuntime = createRequire(path.join(nodeModules, "__runtime__.cjs"));
  const entrypoint = requireFromRuntime.resolve("@oai/artifact-tool");
  return import(pathToFileURL(entrypoint).href);
}


async function main() {
  const args = parseArgs(process.argv.slice(2));
  const skillDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const source = path.resolve(
    args.source ?? path.join(skillDirectory, "assets", "BytePlus Presentation Template_FEB 2026.pptx"),
  );
  const output = path.resolve(requiredString(args, "output"));
  const numbers = selectedSlideNumbers(requiredString(args, "slides"));
  const sourceStat = await fs.stat(source).catch(() => undefined);
  if (!sourceStat?.isFile()) {
    throw new Error(`Missing source template: ${source}`);
  }
  if (await fs.stat(output).catch(() => undefined)) {
    throw new Error(`Refusing to overwrite existing output: ${output}`);
  }
  const { FileBlob, PresentationFile } = await artifactTool();
  const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
  const originals = [...presentation.slides.items];
  const invalid = numbers.filter((number) => number > originals.length);
  if (invalid.length > 0) {
    throw new Error(`Slide numbers exceed template count ${originals.length}: ${invalid.join(",")}`);
  }
  const selected = numbers.map((number) => originals[number - 1].duplicate());
  originals.forEach((slide) => slide.delete());
  selected.forEach((slide, index) => slide.moveTo(index));
  await fs.mkdir(path.dirname(output), { recursive: true });
  await (await PresentationFile.exportPptx(presentation)).save(output);
  process.stdout.write(`${JSON.stringify({ source, output, selectedSlides: numbers, slideCount: selected.length }, null, 2)}\n`);
}


main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || String(error)}\n`);
  process.exit(1);
});
