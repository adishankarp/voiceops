#!/usr/bin/env node
"use strict";

const path = require("path");
const fs = require("fs");

const sharp = require("sharp");

const LOGO_DIR = __dirname;
const PROJECT_ROOT = path.resolve(LOGO_DIR, "..");
const SVG_PATH = path.join(LOGO_DIR, "logo.svg");
const PNG_PATH = path.join(LOGO_DIR, "logo.png");
const FAVICON_ROOT = path.join(PROJECT_ROOT, "favicon.ico");
const FAVICON_PUBLIC = path.join(PROJECT_ROOT, "voiceops", "frontend", "public", "favicon.ico");

const SIZES = [256, 128, 64, 48, 32, 16];

async function main() {
  console.log("Generating logo.png (512x512) from logo.svg...");
  await sharp(SVG_PATH)
    .resize(512, 512)
    .png()
    .toFile(PNG_PATH);
  console.log("Created", PNG_PATH);

  console.log("Generating favicon.ico with sizes:", SIZES.join(", "));
  const sizePaths = [];
  for (const size of SIZES) {
    const p = path.join(LOGO_DIR, `logo-${size}.png`);
    await sharp(PNG_PATH).resize(size, size).png().toFile(p);
    sizePaths.push(p);
  }
  const pngToIco = (await import("png-to-ico")).default;
  const ico = await pngToIco(sizePaths);
  fs.writeFileSync(FAVICON_ROOT, ico);
  console.log("Created", FAVICON_ROOT);

  const publicDir = path.dirname(FAVICON_PUBLIC);
  if (fs.existsSync(publicDir)) {
    fs.writeFileSync(FAVICON_PUBLIC, ico);
    console.log("Updated", FAVICON_PUBLIC);
  }

  sizePaths.forEach((p) => {
    try {
      fs.unlinkSync(p);
    } catch (_) {}
  });
  console.log("Done.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
