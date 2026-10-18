import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import extra from '../cs2-backend/mvp/dashboard/src/i18n-extra.js';
import {t,setLanguage,locale,systemText} from '../cs2-backend/mvp/dashboard/src/i18n.js';
globalThis.document={documentElement:{lang:''}};
// Read the base dictionaries in an isolated context to check every translation's placeholders.
const source=fs.readFileSync(new URL('../cs2-backend/mvp/dashboard/src/i18n.js',import.meta.url),'utf8');
const base=vm.runInNewContext(source.slice(source.indexOf('const DICT='),source.indexOf('// Only known system formats')).replace('const DICT=','var DICT=')+';DICT');
const slots=s=>[...s.matchAll(/\{(\w+)\}/g)].map(m=>m[1]).sort();
for(const lang of ['zh','es']){
 const dict={...base[lang],...extra[lang]};
 for(const [key,value] of Object.entries(dict))assert.deepEqual(slots(value),slots(key),`${lang}: ${key}`);
 setLanguage(lang);
 for(const key of ['Ticket queue','Your next act of support.','Accept responsibility','Summary pending','Set priority','No tickets yet.'])assert.notEqual(t(key),key,`${lang}: ${key}`);
 assert.equal(systemText('Caller ••1234'),t('Caller ••{x}',{x:'1234'}));
 assert.ok(systemText('Approximate (address lookup): 123 Main St').endsWith('123 Main St'));
 assert.equal(systemText('Unrecognized note {verbatim}'),'Unrecognized note {verbatim}');
 assert.equal(locale(),lang==='zh'?'zh-CN':'es-ES');
}
setLanguage('en');assert.equal(t('Ticket queue'),'Ticket queue');
setLanguage('invalid');assert.equal(locale(),'en-US');
console.log('PASS: zh/es placeholder parity, page labels, locale switching, known system formats and verbatim fallback');
