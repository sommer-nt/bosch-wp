// Prüft die Druckseiten von index.html: kein Inhalt darf in die Fußzeile oder über die Seite hinaus laufen.
// Aufruf: node tools/druck_pruefen.js index.html   (Exit-Code 1 bei Überlauf)
const {chromium} = require('playwright'), pfad = require('path').resolve(process.argv[2] || 'index.html');
const FAELLE = {
  efh: E => { E.heizlast.vorgabe_kw = 12; E.tww.personen = 4; E.auswahl.geraet = 'CS5800/6800iAW 12 OR-T'; },
  verbrauch: E => { E.heizlast.methode = 'verbrauch'; E.heizlast.menge = 3000; E.tww.personen = 4; },
  huelle: E => { E.heizlast.methode = 'huelle'; E.heizlast.huell_a_m2 = 420; E.heizlast.ht = 0.45; E.heizlast.volumen_m3 = 480; E.tww.personen = 5; },
  sole: E => { E.waermequelle = 'sole'; E.heizlast.vorgabe_kw = 11; E.tww.personen = 4; },
  kaskade: E => { E.heizlast.vorgabe_kw = 25; E.tww.personen = 6; E.auswahl.geraet = 'CS8800iAW 15 O-T'; E.auswahl.anzahl = 2; },
};
(async () => {
  const b = await chromium.launch(); const p = await b.newPage(); let fehler = 0;
  for (const [name, fn] of Object.entries(FAELLE)) {
    await p.goto('file://' + pfad);
    await p.evaluate(`(${fn.toString()})(E); schreibeFelder(); aktualisiere();`);
    await p.emulateMedia({media: 'print'});
    await p.evaluate(() => baueDruck());
    const r = await p.evaluate(() => [...document.querySelectorAll('#druck .seite')].map((s, i) => {
      const f = s.querySelector('.dk-fuss'), fy = f.getBoundingClientRect().top; let max = 0;
      s.querySelectorAll('*').forEach(e => { if (e.closest('.dk-fuss')) return; const r = e.getBoundingClientRect(); if (r.height && r.bottom > max) max = r.bottom; });
      return max > fy ? `S${i + 1}: +${Math.round((max - fy) / 3.78)}mm` : null; }).filter(Boolean));
    console.log(name, r.length ? r.join(', ') : 'ok'); fehler += r.length;
    await p.emulateMedia({media: 'screen'});
  }
  await b.close();
  process.exit(fehler ? 1 : 0);
})();
