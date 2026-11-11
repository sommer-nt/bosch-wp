// Hydraulik-Auswahl aus index.html (<script id="hydkern">) für test_hydraulik.py ausführen.
const fs = require('fs'), vm = require('vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const block = id => html.match(new RegExp(`<script id="${id}">([\\s\\S]*?)</script>`))[1];
const ctx = {};
vm.createContext(ctx);
vm.runInContext(block('daten') + ';this.GERAETE_DATEN=GERAETE_DATEN;this.KATALOG_DATEN=KATALOG_DATEN;this.MFH_DATEN=MFH_DATEN;this.HYDRAULIK_DATEN=HYDRAULIK_DATEN;', ctx);
vm.runInContext(block('rechenkern') + ';this.RK=RK;', ctx);
vm.runInContext(block('mfhkern') + ';this.MFK=MFK;', ctx);
vm.runInContext(block('hydkern') + ';this.HYD=HYD;', ctx);
const f = JSON.parse(fs.readFileSync(process.argv[3], 'utf8')), lib = ctx.HYDRAULIK_DATEN;
const out = {
  auswahl: f.eingaben.map(e => {
    const r = ctx.MFK.rechneMitMuster(e, ctx.GERAETE_DATEN, ctx.KATALOG_DATEN, ctx.MFH_DATEN);
    return {schemata: ctx.HYD.schemata(e, r, lib), gewaehlt: ctx.HYD.gewaehlt(e, r, lib), loesungen: ctx.HYD.loesungen(e, r, lib).map(L => L.id)};
  }),
  uebernehmen: f.loesungen.map(id => ctx.HYD.uebernehmen(JSON.parse(JSON.stringify(f.neu)), lib.loesungen.find(L => L.id === id))),
};
process.stdout.write(JSON.stringify(out));
