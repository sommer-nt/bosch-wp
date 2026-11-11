// MFH-Musterlösungen aus index.html (mfhkern) für test_mfh.py ausführen.
// Aufruf: node mfh_html.js index.html faelle.json  -> JSON auf stdout
const fs = require('fs'), vm = require('vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const block = id => html.match(new RegExp(`<script id="${id}">([\\s\\S]*?)</script>`))[1];
const ctx = {};
vm.createContext(ctx);
vm.runInContext(block('daten') + ';this.GERAETE_DATEN=GERAETE_DATEN;this.KATALOG_DATEN=KATALOG_DATEN;this.MFH_DATEN=MFH_DATEN;', ctx);
vm.runInContext(block('rechenkern') + ';this.RK=RK;', ctx);
vm.runInContext(block('mfhkern') + ';this.MFK=MFK;', ctx);
const f = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const M = ctx.MFH_DATEN;
const out = {
  vorschlag: f.eingaben.map(e => {
    const r = ctx.RK.rechne(e, ctx.GERAETE_DATEN, ctx.KATALOG_DATEN);
    return ctx.MFK.vorschlag(e, r, M, ctx.GERAETE_DATEN, ctx.KATALOG_DATEN);
  }),
  rechne: f.eingaben.map(e => { const r = ctx.MFK.rechneMitMuster(e, ctx.GERAETE_DATEN, ctx.KATALOG_DATEN, M); return {g: r.gewaehlt && [r.gewaehlt.geraet, r.gewaehlt.n], wp: r.mfh_wp}; }),
  folgen: f.folgen.map(([e, k]) => { ctx.MFK.eingabenFolgen(e, k); return e; }),
};
process.stdout.write(JSON.stringify(out));
