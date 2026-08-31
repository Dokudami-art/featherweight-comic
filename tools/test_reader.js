/* Behaviour tests for the chapter reader.
   Run with:  node tools/test_reader.js                                  */
const fs = require('fs');

function harness() {
  const store = {}, listeners = {}, els = {}, scrollCalls = [], scrollByCalls = [];
  const mk = (id) => (els[id] = { id, hidden: true, dataset: {} });
  ['helppanel','helpbtn','helpclose','pbar','readerbar'].forEach(mk);
  Object.values(els).forEach(e => {
    e._h = {};
    e.addEventListener = (t, f) => { (e._h[t] ||= []).push(f); };
    e.click = () => (e._h.click || []).forEach(f => f({ preventDefault(){} }));
  });
  els.pbar.style = {};
  const cls = new Set();
  els.readerbar.classList = { add:(c)=>cls.add(c), remove:(c)=>cls.delete(c), has:(c)=>cls.has(c) };

  const totop = { _h:{}, addEventListener:(t,f)=>{ (totop._h[t] ||= []).push(f); },
                  click:()=> (totop._h.click||[]).forEach(f=>f({preventDefault(){}})) };

  const state = { scrollY: 0, docHeight: 40000, winHeight: 800 };
  const win = {
    get scrollY(){ return state.scrollY; },
    innerHeight: state.winHeight,
    addEventListener: (t,f)=>{ (listeners[t] ||= []).push(f); },
    scrollTo:(o)=>scrollCalls.push(o),
    scrollBy:(o)=>scrollByCalls.push(o),
    matchMedia: () => ({ matches:false, addEventListener(){}, addListener(){} }),
    requestAnimationFrame: (f)=>f(),
    localStorage: { getItem:(k)=>k in store?store[k]:null,
                    setItem:(k,v)=>{store[k]=String(v);}, removeItem:(k)=>{delete store[k];} },
  };
  const doc = {
    documentElement:{ get scrollHeight(){ return state.docHeight; }, setAttribute(){} },
    getElementById:(id)=>els[id]||null,
    querySelector:(s)=> s === ".totop" ? totop : null,
    querySelectorAll:()=>[],
    addEventListener:(t,f)=>{ (listeners[t] ||= []).push(f); },
    currentScript:{ dataset:{ chapter:'ch01', prev:'', next:'' } },
    visibilityState:'visible',
  };
  const history = { scrollRestoration:'auto' };
  return { store, listeners, state, els, win, doc, history, totop, scrollCalls, scrollByCalls, cls,
           fire:(t,e)=> (listeners[t]||[]).forEach(f=>f(e||{target:{}})) };
}

function run(h) {
  const src = fs.readFileSync('assets/js/reader.js','utf8');
  new Function('window','document','localStorage','history','requestAnimationFrame','location', src)
    (h.win, h.doc, h.win.localStorage, h.history, (f)=>f(), { href:'' });
}

let pass=0, fail=0;
const check=(n,c,d='')=>{ c ? (console.log(`  PASS  ${n}`), pass++) : (console.log(`  FAIL  ${n}  ${d}`), fail++); };

console.log('\nTEST 1 — Back to top jumps instantly');
{
  const h = harness(); run(h);
  h.state.scrollY = 20000;
  h.totop.click();
  const c = h.scrollCalls[h.scrollCalls.length-1];
  check('scrollTo called', !!c);
  check('targets the top', c && c.top === 0, `got ${c && c.top}`);
  check('behavior is "instant"', c && c.behavior === 'instant',
        `got ${c && c.behavior} — "auto"/"smooth" is silently ignored over long distances`);
}

console.log('\nTEST 2 — progress bar tracks scroll position');
{
  const h = harness(); run(h);
  h.state.scrollY = Math.round(0.5 * (h.state.docHeight - h.win.innerHeight));
  h.fire('scroll');
  check('bar is ~50%', parseFloat(h.els.pbar.style.width) > 49 && parseFloat(h.els.pbar.style.width) < 51,
        `got ${h.els.pbar.style.width}`);
}

console.log('\nTEST 3 — header hides scrolling down, returns scrolling up');
{
  const h = harness(); run(h);
  h.state.scrollY = 1000; h.fire('scroll');
  check('hidden after scrolling down', h.cls.has('hidden'));
  h.state.scrollY = 900;  h.fire('scroll');
  check('shown again after scrolling up', !h.cls.has('hidden'));
}

console.log('\nTEST 4 — reading position is no longer stored anywhere');
{
  const h = harness(); run(h);
  h.state.scrollY = 15000;
  h.fire('scroll'); h.fire('pagehide');
  check('nothing written to storage', Object.keys(h.store).length === 0,
        `found ${JSON.stringify(h.store)}`);
  check('browser scroll restoration left alone', h.history.scrollRestoration === 'auto',
        `got ${h.history.scrollRestoration}`);
}

console.log('\nTEST 5 — J and K scroll by roughly one screen');
{
  const h = harness(); run(h);
  h.fire('keydown', { key:'j', target:{}, preventDefault(){} });
  const c = h.scrollByCalls[0];
  check('J scrolls down', c && c.top > 0, `got ${c && c.top}`);
  check('roughly one screen', c && Math.abs(c.top - h.win.innerHeight*0.88) < 2, `got ${c && c.top}`);
  h.fire('keydown', { key:'k', target:{}, preventDefault(){} });
  const c2 = h.scrollByCalls[1];
  check('K scrolls up', c2 && c2.top < 0, `got ${c2 && c2.top}`);
}

console.log(`\n${pass} passed, ${fail} failed\n`);
process.exit(fail ? 1 : 0);
