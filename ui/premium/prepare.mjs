import { readFileSync, writeFileSync } from 'node:fs';
writeFileSync(new URL('./src/styles.js', import.meta.url),
  'export default ' + JSON.stringify(readFileSync(new URL('./src/dashboard.css', import.meta.url), 'utf8')) + ';\n');
