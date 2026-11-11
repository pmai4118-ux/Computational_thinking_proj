/* Cache only render assets declared by the original Stitch exports. */
const fs = require('node:fs');
const path = require('node:path');
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');
const run = promisify(execFile);
const sourceDir = path.join(__dirname, 'demo-web');
const output = path.join(__dirname, 'stitch-assets.json');
const assets = fs.existsSync(output) ? JSON.parse(fs.readFileSync(output, 'utf8')) : {};
const requests = new Map();
const decode = value => value.replaceAll('&amp;', '&');
const allowedHosts = new Set(['cdn.tailwindcss.com', 'fonts.googleapis.com', 'fonts.gstatic.com', 'lh3.googleusercontent.com']);
const userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36';

function request(url) {
  if (requests.has(url)) return requests.get(url);
  const parsed = new URL(url);
  if (parsed.protocol !== 'https:' || !allowedHosts.has(parsed.hostname)) throw Error('Unexpected asset host: ' + parsed.hostname);
  const pending = run('curl.exe', ['-fsSL', '--max-time', '25', '-A', userAgent, url], {
    encoding: 'buffer', maxBuffer: 16 * 1024 * 1024, windowsHide: true
  }).then(({ stdout }) => stdout);
  requests.set(url, pending);
  return pending;
}

async function bundle(url) {
  if (assets[url]) return;
  const buffer = await request(url);
  const host = new URL(url).hostname;
  if (host === 'cdn.tailwindcss.com') {
    assets[url] = { script: buffer.toString('utf8') };
  } else if (host === 'fonts.googleapis.com') {
    const css = buffer.toString('utf8');
    const fonts = [...new Set([...css.matchAll(/url\((https:\/\/fonts\.gstatic\.com\/[^)]+)\)/g)].map(match => match[1]))];
    const dataFonts = await Promise.all(fonts.map(async font => [font, 'data:font/woff2;base64,' + (await request(font)).toString('base64')]));
    let inlineCss = css;
    for (const [font, data] of dataFonts) inlineCss = inlineCss.replaceAll(font, data);
    assets[url] = { css: inlineCss };
  } else {
    const type = buffer[0] === 0xff ? 'jpeg' : buffer.subarray(0, 4).toString() === 'RIFF' ? 'webp' : 'png';
    assets[url] = { image: 'data:image/' + type + ';base64,' + buffer.toString('base64') };
  }
}

async function main() {
  const urls = new Set();
  for (const folder of fs.readdirSync(sourceDir)) {
    const file = path.join(sourceDir, folder, 'code.html');
    if (!fs.existsSync(file)) continue;
    const html = fs.readFileSync(file, 'utf8');
    for (const match of html.matchAll(/https:\/\/(?:cdn\.tailwindcss\.com|fonts\.googleapis\.com\/css2|lh3\.googleusercontent\.com\/)[^"'<> )\s\\]*/g)) {
      urls.add(decode(match[0]));
    }
  }
  const results = await Promise.allSettled([...urls].map(bundle));
  fs.writeFileSync(output, JSON.stringify(assets));
  const failures = results.flatMap((result, index) => result.status === 'rejected' ? [[...urls][index] + ': ' + result.reason.message] : []);
  console.log('Cached ' + Object.keys(assets).length + '/' + urls.size + ' render assets.');
  if (failures.length) throw Error(failures.join('\n'));
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
