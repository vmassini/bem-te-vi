// Regera os modelos (aves e cenário da praça) no Blender (sem abrir a interface): node arte/gerar_modelos.mjs [espécie...]
// Usa a variável BLENDER se existir; senão procura o Blender instalado em "C:\Program Files\Blender Foundation".
import { execFileSync } from 'node:child_process';
import { existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const arte = fileURLToPath(new URL('.', import.meta.url));
const saida = join(arte, 'saida');

function acharBlender() {
  if (process.env.BLENDER) return process.env.BLENDER;
  const base = 'C:\\Program Files\\Blender Foundation';
  if (existsSync(base)) {
    const versoes = readdirSync(base).filter(d => d.startsWith('Blender')).sort().reverse();
    for (const v of versoes) { const exe = join(base, v, 'blender.exe'); if (existsSync(exe)) return exe; }
  }
  return 'blender';
}

const TAREFAS = {
  bemtevi: ['modelar_passaro.py', 'bemtevi'],
  pirata: ['modelar_passaro.py', 'pirata'],
  filhote: ['modelar_filhote.py'],
  tucano: ['modelar_tucano.py'],
  gaviao: ['modelar_gaviao.py'],
  praca: ['modelar_praca.py'],
  flores: ['modelar_flores.py'],
};
const blender = acharBlender();
const pedidas = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(TAREFAS);
for (const nome of pedidas) {
  const [script, ...extra] = TAREFAS[nome] || [];
  if (!script) { console.error('Espécie desconhecida:', nome); process.exitCode = 1; continue; }
  console.log(`Modelando ${nome}…`);
  const out = execFileSync(blender, ['-b', '--factory-startup', '-P', join(arte, script), '--', saida, ...extra], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  for (const linha of out.split(/\r?\n/)) if (/EXPORTADO|FOLHA|Error/.test(linha)) console.log('  ' + linha.trim());
}
