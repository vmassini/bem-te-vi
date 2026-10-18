// Gera www/index.html (documento completo, usado pelo app Android) a partir de src/jogo.html.
// src/jogo.html é um fragmento: tudo antes de <canvas> vai para o <head>, o resto para o <body>.
// O Three.js vem de node_modules e é copiado para www/vendor, para o app funcionar sem internet.
import { readFileSync, writeFileSync, mkdirSync, copyFileSync, existsSync, readdirSync } from 'node:fs';

const CDN_THREE = 'https://cdn.jsdelivr.net/npm/three@0.149.0/build/three.min.js';
const here = p => new URL(p, import.meta.url);

let frag = readFileSync(here('./src/jogo.html'), 'utf8');
const cut = frag.indexOf('<canvas');
if (cut < 0) throw new Error('src/jogo.html precisa ter um <canvas>');

mkdirSync(here('./www/vendor/'), { recursive: true });
const localThree = here('./node_modules/three/build/three.min.js');
if (existsSync(localThree)) {
  copyFileSync(localThree, here('./www/vendor/three.min.js'));
  frag = frag.replace(CDN_THREE, 'vendor/three.min.js');
} else {
  console.warn('Aviso: rode "npm install" para embutir o Three.js; usando o CDN por enquanto.');
}

const html = `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#173a26">
${frag.slice(0, cut).trim()}
</head>
<body>
${frag.slice(cut).trim()}
</body>
</html>
`;

writeFileSync(here('./www/index.html'), html);

// modelos 3D gerados pelo Blender (arte/saida/*.glb) -> www/modelos/
mkdirSync(here('./www/modelos/'), { recursive: true });
const saida = here('./arte/saida/');
const glbs = existsSync(saida) ? readdirSync(saida).filter(f => f.endsWith('.glb')) : [];
for (const f of glbs) copyFileSync(new URL(f, saida), here('./www/modelos/' + f));
// os mesmos modelos em base64 num .js (o link publicado não serve arquivos .glb)
const embutidos = Object.fromEntries(glbs.map(f => [f.replace('.glb', ''), readFileSync(new URL(f, saida)).toString('base64')]));
writeFileSync(here('./www/modelos.js'), 'window.BTV_MODELOS = ' + JSON.stringify(embutidos) + ';\n');
console.log('www/index.html gerado; modelos:', glbs.join(', ') || 'nenhum');
