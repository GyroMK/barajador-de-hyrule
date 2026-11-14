// Pistas de una semilla a partir de su código (OOT2-…), con el mismo motor y el mismo azar que la web.
// uso: node pistas.js <código> [idioma]  ->  JSON {n, pistas: [{tipo, texto}]}   (idioma: es, en…; nombres oficiales del juego)
const path = require("path");
const E = require(path.join(__dirname, "..", "web", "engine.js"));
const D = require(path.join(__dirname, "..", "web", "datos.json"));
const code = process.argv[2], lang = process.argv[3] || "es";
const {plac, opciones} = E.decodeCode(D, code);
const R = D.remake, N = R.nombres[lang] || R.nombres.en, EN = R.nombres.en;
const itemName = (i) => N.items[i] || EN.items[i] || R.item_es[i] || i;
const zoneKey = (i) => R.locs[i].tipo === "regalo" ? R.locs[i].zona : R.locs[i].scene;
const zoneOf = (i) => { const k = zoneKey(i); return N.scenes[k] || EN.scenes[k] || R.scene_es[k] || k; };
const Rr = new E.Rando(D, opciones);
const n = opciones.pistas ?? 12;
const H = Rr.hints(plac, E.rngFrom(code + "#pistas"), zoneOf, itemName, n, E.HINT_FMT[lang] || E.HINT_FMT.en);
process.stdout.write(JSON.stringify({n, pistas: H.hints.slice(0, n)}));
