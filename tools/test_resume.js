const fs = require('fs');

function harness() {
  const store = {};
  const listeners = {};
  const els = {};
  const mk = (id) => (els[id] = { id, hidden: true, addEventListener(){}, dataset:{} });
  ['resume','resumego','resumeno','resumeclose','helppanel','helpbtn','helpclose','pbar','readerbar'].forEach(mk);
  els.pbar.style = {}; els.readerbar.classList = { add(){}, remove(){} };

  const state = { scrollY: 0, docHeight: 40000, winHeight: 800 };
  const win = {
    get scrollY(){ return state.scrollY; },
    innerHeight: state.winHeight,
    addEventListener: (t,f)=>{ (listeners[t] ||= []).push(f); },
    scrollTo(){}, scrollBy(){},
    matchMedia: () => ({ matches:false, addEventListener(){}, addListener(){} }),
    requestAnimationFrame: (f)=>f(),
    localStorage: {
      getItem:(k)=>k in store?store[k]:null,
      setItem:(k,v)=>{store[k]=String(v);},
      removeItem:(k)=>{delete store[k];}
    },
  };
  const doc = {
    documentElement:{ get scrollHeight(){ return state.docHeight; }, setAttribute(){} },
    getElementById:(id)=>els[id]||null,
    querySelector:()=>null, querySelectorAll:()=>[],
    addEventListener:(t,f)=>{ (listeners[t] ||= []).push(f); },
    currentScript:{ dataset:{ chapter:'ch01', prev:'', next:'' } },
    visibilityState:'visible',
  };
  const history = { scrollRestoration:'auto' };
  return { store, listeners, state, els, win, doc, history,
    fire:(t)=> (listeners[t]||[]).forEach(f=>f({target:{}})) };
}

function run(h) {
  const src = fs.readFileSync('assets/js/reader.js','utf8');
  const fn = new Function('window','document','localStorage','history','setTimeout',
                          'clearTimeout','requestAnimationFrame','matchMedia', src);
  fn(h.win, h.doc, h.win.localStorage, h.history,
     (f)=>{ if(f.name!=='') {} return 0; }, ()=>{}, (f)=>f(), h.win.matchMedia);
}

let pass = 0, fail = 0;
const check = (name, cond, detail='') => {
  if (cond) { console.log(`  PASS  ${name}`); pass++; }
  else { console.log(`  FAIL  ${name}  ${detail}`); fail++; }
};

console.log('\nTEST 1 — leaving a chapter from 35% saves the position');
{
  const h = harness();
  run(h);
  h.state.scrollY = Math.round(0.35 * (h.state.docHeight - h.win.innerHeight));
  h.fire('pagehide');
  check('position stored', h.store['fw:pos:ch01'] !== undefined, `got ${h.store['fw:pos:ch01']}`);
  check('stored value ≈0.35', Math.abs(parseFloat(h.store['fw:pos:ch01']) - 0.35) < 0.01,
        `got ${h.store['fw:pos:ch01']}`);
}

console.log('\nTEST 2 — THE BUG: returning to the top must not erase it');
{
  const h = harness();
  h.store['fw:pos:ch01'] = '0.3500';
  run(h);
  h.state.scrollY = 0;          // reader arrives back at the top of the chapter
  h.fire('pagehide');           // ...and navigates away without scrolling
  check('bookmark survives', h.store['fw:pos:ch01'] === '0.3500',
        `expected 0.3500, got ${h.store['fw:pos:ch01']}`);
}

console.log('\nTEST 3 — resume prompt appears when a position is stored');
{
  const h = harness();
  h.store['fw:pos:ch01'] = '0.3500';
  run(h);
  check('prompt shown', h.els.resume.hidden === false, `hidden=${h.els.resume.hidden}`);
}

console.log('\nTEST 4 — no prompt for a first-time reader');
{
  const h = harness();
  run(h);
  check('prompt stays hidden', h.els.resume.hidden === true);
}

console.log('\nTEST 5 — no prompt for someone who finished the chapter');
{
  const h = harness();
  h.store['fw:pos:ch01'] = '0.9900';
  run(h);
  check('prompt stays hidden', h.els.resume.hidden === true);
}

console.log('\nTEST 6 — browser scroll restoration disabled so we control position');
{
  const h = harness();
  run(h);
  check('scrollRestoration set to manual', h.history.scrollRestoration === 'manual',
        `got ${h.history.scrollRestoration}`);
}

console.log(`\n${pass} passed, ${fail} failed\n`);
process.exit(fail ? 1 : 0);
