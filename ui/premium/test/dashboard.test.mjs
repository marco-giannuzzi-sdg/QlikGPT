import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cube, measureIds, sessionDefinitions, rows } from '../src/data.mjs';
import { esc, trendSvg, renderDashboard } from '../src/render.mjs';
const cell=(qText,qNum,qElemNumber=0)=>({qText,qNum,qElemNumber});
test('all data bindings use existing master items, with no inline expressions',()=>{
  const props=[cube(measureIds),...sessionDefinitions().map(d=>d.props)];
  assert.ok(!JSON.stringify(props).includes('"qDef"'));
  assert.equal(sessionDefinitions().length,5);
  assert.equal(cube(measureIds).qMeasures.length,4);
  for(const d of sessionDefinitions()){
    if(d.props.qListObjectDef) assert.ok(d.props.qListObjectDef.qLibraryId.startsWith('qlikgpt_d_'));
  }
});
test('selection identity survives sorting and missing numeric cells',()=>{
  const input={qHyperCube:{qDataPages:[{qMatrix:[[cell('Italy',2,77),cell('10',10)],[cell('null',0,5),cell('-',NaN)]]}]}};
  assert.deepEqual(rows(input).map(d=>d.elem),[77]);
  assert.match(trendSvg(rows(input),'test'),/data-trend="77"/);
});
test('empty and negative values have finite coordinates and explicit empty state',()=>{
  assert.match(trendSvg([],'x'),/Nessun dato/);
  for(const values of [[0],[-5],[5,-5]]){
    const html=trendSvg(values.map((value,i)=>({name:'Month',value,sort:i,elem:i,text:String(value)})),'test');
    assert.ok(!/NaN|Infinity/.test(html));
  }
});
test('untrusted labels are escaped in markup and tooltip attributes',()=>{
  assert.equal(esc('<img x="a">&'), '&lt;img x=&quot;a&quot;&gt;&amp;');
  const html=trendSvg([{name:'<script>',value:1,sort:1,elem:9,text:'" onclick="bad'}],'x');
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('&quot; onclick=&quot;bad'));
});
test('render uses Qlik formatted KPI texts and never invents comparisons',()=>{
  const layout={qHyperCube:{qDataPages:[{qMatrix:[measureIds.map((_,i)=>cell('VALORE '+i,i))]}]}};
  const html=renderDashboard(layout,{});
  for(let i=0;i<4;i++) assert.ok(html.includes('VALORE '+i));
  assert.ok(html.includes('data-filter="year"'));
  assert.ok(!html.includes('vs last'));
  assert.ok(!html.includes('Visualizzazione non valida'));
});

test('all measure and dimension IDs exist in the versioned semantic catalog',async()=>{
  const {readFileSync}=await import('node:fs');
  const base=new URL('../../../semantic-models/sales/catalog/',import.meta.url);
  const knownMeasures=new Set(JSON.parse(readFileSync(new URL('measures.json',base))).measures.map(d=>d.id));
  const knownDimensions=new Set(JSON.parse(readFileSync(new URL('dimensions.json',base))).dimensions.map(d=>d.id));
  for(const id of measureIds)assert.ok(knownMeasures.has(id),id);
  for(const def of sessionDefinitions()){
    const cube=def.props.qHyperCubeDef;
    if(cube)for(const dim of cube.qDimensions)assert.ok(knownDimensions.has(dim.qLibraryId),dim.qLibraryId);
    const list=def.props.qListObjectDef;
    if(list)assert.ok(knownDimensions.has(list.qLibraryId),list.qLibraryId);
  }
});
