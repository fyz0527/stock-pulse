const fs=require('fs');
const h=fs.readFileSync('index.html','utf8');
const m=h.match(/<script>([\s\S]*?)<\/script>/);
const code=m[1];
const vm=require('vm');
try{ new vm.Script(code); console.log('SYNTAX_OK'); }
catch(e){ console.log('SYNTAX_ERR', e.message); }
