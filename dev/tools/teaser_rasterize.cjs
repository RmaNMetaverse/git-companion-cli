/* Rasterize genuine Textual SVG captures for the motion renderer. */
const fs = require('node:fs/promises');
const path = require('node:path');
const sharp = require(process.env.SHARP_PATH || 'sharp');

(async () => {
  const folder = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(__dirname, '../artifacts/teaser/screens');
  for (const name of await fs.readdir(folder)) {
    if (!name.endsWith('.svg')) continue;
    const svg = (await fs.readFile(path.join(folder, name), 'utf8'))
      .replaceAll('Fira Code', 'Consolas')
      .replaceAll('<text ', '<text lengthAdjust="spacingAndGlyphs" ');
    await sharp(Buffer.from(svg)).resize({ width: 1800 }).png().toFile(path.join(folder, name.replace('.svg', '.png')));
    process.stdout.write(`Rasterized ${name}\n`);
  }
})().catch(error => { console.error(error); process.exit(1); });
