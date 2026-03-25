const path = require('path');
const { spawnSync } = require('child_process');
const result = spawnSync('cargo', ['check'], {
  cwd: __dirname,
  encoding: 'utf8',
  shell: true
});
console.log('EXIT CODE:', result.status);
if (result.stdout) console.log('STDOUT:\n' + result.stdout);
if (result.stderr) console.log('STDERR:\n' + result.stderr);
if (result.error) console.log('ERROR:', result.error);
