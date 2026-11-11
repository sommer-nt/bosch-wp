// Prüfprotokoll zum Bestellvorschlag aus index.html (mfhkern) für test_texte.py ausführen.
const fs = require('fs'), vm = require('vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const block = id => html.match(new RegExp(`<script id="${id}">([\\s\\S]*?)</script>`))[1];
const ctx = {};
vm.createContext(ctx);
vm.runInContext(block('daten') + ';this.GERAETE_DATEN=GERAETE_DATEN;this.KATALOG_DATEN=KATALOG_DATEN;this.MFH_DATEN=MFH_DATEN;this.HYDRAULIK_DATEN=HYDRAULIK_DATEN;', ctx);
vm.runInContext(block('rechenkern') + ';this.RK=RK;', ctx);
vm.runInContext(block('mfhkern') + ';this.MFK=MFK;', ctx);
vm.runInContext(block('schemasvg') + ';this.schemaZahl=schemaZahl;', ctx);
vm.runInContext(block('hdbkern') + ';this.HDB=HDB;', ctx);
const ein = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
process.stdout.write(JSON.stringify(ein.map(([e, ie]) => ctx.MFK.dokumentation(e, ctx.MFK.rechneMitMuster(e, ctx.GERAETE_DATEN, ctx.KATALOG_DATEN, ctx.MFH_DATEN), ctx.MFH_DATEN, ctx.HYDRAULIK_DATEN, ie))));
