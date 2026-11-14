/* Motor del randomizer del OoT remake (Switch 2) en JavaScript.
   Port del generador en Python (rando/logic.py + rando/generate.py). Lógica: datos del OoTR (MIT).
   Funciona en navegador y en Node (module.exports). */
(function (root) {
"use strict";

// ---------------------------------------------------------------- analizador de reglas
function tokenize(s) {
  const t = []; let i = 0;
  while (i < s.length) {
    const c = s[i];
    if (/\s/.test(c)) { i++; continue; }
    if (c === "'" || c === '"') { let j = i + 1; while (s[j] !== c) j++; t.push({k: "str", v: s.slice(i + 1, j)}); i = j + 1; continue; }
    if (/[0-9]/.test(c)) { let j = i; while (/[0-9.]/.test(s[j])) j++; t.push({k: "num", v: Number(s.slice(i, j))}); i = j; continue; }
    if (/[A-Za-z_]/.test(c)) { let j = i; while (j < s.length && /[A-Za-z0-9_]/.test(s[j])) j++; t.push({k: "id", v: s.slice(i, j)}); i = j; continue; }
    const two = s.slice(i, i + 2);
    if (["==", "!=", "<=", ">="].includes(two)) { t.push({k: "op", v: two}); i += 2; continue; }
    if ("()[],<>".includes(c)) { t.push({k: "op", v: c}); i++; continue; }
    throw new Error("carácter inesperado en regla: " + c + " en " + s);
  }
  t.push({k: "eof"});
  return t;
}
function parse(src) {
  const t = tokenize(src); let p = 0;
  const peek = () => t[p], next = () => t[p++];
  const isId = (v) => t[p].k === "id" && t[p].v === v, isOp = (v) => t[p].k === "op" && t[p].v === v;
  function expect(v) { if (!isOp(v)) throw new Error("se esperaba " + v + " en " + src); p++; }
  function orE() { const xs = [andE()]; while (isId("or")) { p++; xs.push(andE()); } return xs.length > 1 ? {t: "or", xs} : xs[0]; }
  function andE() { const xs = [notE()]; while (isId("and")) { p++; xs.push(notE()); } return xs.length > 1 ? {t: "and", xs} : xs[0]; }
  function notE() { if (isId("not")) { p++; return {t: "not", x: notE()}; } return cmpE(); }
  function cmpE() {
    const l = prim();
    if (t[p].k === "op" && ["==", "!=", "<", "<=", ">", ">="].includes(t[p].v)) { const op = next().v; return {t: "cmp", op, l, r: prim()}; }
    if (isId("in")) { p++; return {t: "cmp", op: "in", l, r: prim()}; }
    if (isId("not") && t[p + 1].k === "id" && t[p + 1].v === "in") { p += 2; return {t: "cmp", op: "notin", l, r: prim()}; }
    return l;
  }
  function prim() {
    const k = peek();
    if (k.k === "op" && k.v === "(") {
      p++; const first = orE();
      if (isOp(",")) { const xs = [first]; while (isOp(",")) { p++; xs.push(orE()); } expect(")"); return {t: "tuple", xs}; }
      expect(")"); return first;
    }
    if (k.k === "str") { p++; return {t: "str", v: k.v}; }
    if (k.k === "num") { p++; return {t: "num", v: k.v}; }
    if (k.k === "id") {
      p++; let node = {t: "name", v: k.v};
      if (isOp("(")) {
        p++; const args = [];
        if (!isOp(")")) { args.push(orE()); while (isOp(",")) { p++; args.push(orE()); } }
        expect(")"); node = {t: "call", f: k.v, args};
      }
      while (isOp("[")) { p++; const key = orE(); expect("]"); node = {t: "sub", x: node, key}; }
      return node;
    }
    throw new Error("token inesperado en " + src);
  }
  const e = orE();
  if (t[p].k !== "eof") throw new Error("sobra texto en regla: " + src);
  return e;
}

// ---------------------------------------------------------------- compilador
const STONES = ["Kokiri Emerald", "Goron Ruby", "Zora Sapphire"];
const MEDALLIONS = ["Forest Medallion", "Fire Medallion", "Water Medallion", "Shadow Medallion", "Spirit Medallion", "Light Medallion"];
const BOTTLES = ["Bottle", "Bottle with Milk", "Bottle with Red Potion", "Bottle with Green Potion", "Bottle with Blue Potion",
  "Bottle with Fairy", "Bottle with Fish", "Bottle with Blue Fire", "Bottle with Bugs", "Bottle with Poe", "Bottle with Big Poe", "Rutos Letter"];
const CONSTANT_NAMES = new Set(["child", "adult", "both", "either", "Forest", "Fire", "Water", "Shadow", "Spirit", "Light"]);
const escape = (n) => n.replace(/ /g, "_").replace(/-/g, "_").replace(/[^A-Za-z0-9_]/g, "");

class State {
  constructor() { this.items = new Map(); }
  count(n) { return this.items.get(n) || 0; }
  has(n, k = 1) { if (this.gate && this.gate[n] && !this.count(this.gate[n])) return false; return this.count(n) >= k; }
  add(n, k = 1) { this.items.set(n, this.count(n) + k); }
  set(n, k) { this.items.set(n, k); }
}

class Compiler {
  constructor(helpers, itemNames, settings, world) {
    this.items = new Map(itemNames.map((n) => [escape(n), n]));
    this.S = settings; this.world = world; this.cache = new Map(); this.helpers = new Map();
    for (const [k, v] of Object.entries(helpers)) {
      const m = k.match(/^(\w+)\((.*)\)$/);
      const name = m ? m[1] : k, params = m ? m[2].split(",").map((x) => x.trim()).filter(Boolean) : [];
      this.helpers.set(name, {params, body: parse(v)});
    }
  }
  compile(rule) { if (!this.cache.has(rule)) this.cache.set(rule, this.c(parse(rule), {})); return this.cache.get(rule); }
  setting(n) { return Object.prototype.hasOwnProperty.call(this.S, n); }
  defaultSetting(n) { return /^(logic_|glitch_|adv_|shuffle_)/.test(n) ? false : undefined; }
  itemOf(id) { return this.items.get(id) || id.replace(/_/g, " "); }
  rawname(n, env) {
    if (n.t === "name") return env[n.v] ? this.rawname(env[n.v], {}) : n.v;
    if (n.t === "str" || n.t === "num") return n.v;
    return null;
  }
  target(n, env) {
    if (n.t === "name" && env[n.v]) return this.target(env[n.v], {});
    if (n.t === "str") return n.v;
    if (n.t === "name") {
      const h = this.helpers.get(n.v);
      if (h && !h.params.length) { if (h.body.t === "name") return this.target(h.body, {}); if (h.body.t === "str") return h.body.v; }
      return this.itemOf(n.v);
    }
    throw new Error("objetivo raro");
  }
  val(n, env) {
    if (n.t === "str" || n.t === "num") { const v = n.v; return () => v; }
    if (n.t === "name") {
      if (env[n.v]) return this.val(env[n.v], {});
      if (n.v === "age") return (st, age) => age;
      if (this.setting(n.v)) { const v = this.S[n.v]; return () => v; }
      if (CONSTANT_NAMES.has(n.v)) { const v = n.v; return () => v; }
      const h = this.helpers.get(n.v);
      if (h && !h.params.length) return this.val(h.body, {});
      const d = this.defaultSetting(n.v); if (d !== undefined) return () => d;
      const v = n.v; return () => v;
    }
    return this.c(n, env);
  }
  c(n, env) {
    switch (n.t) {
      case "or": { const fs = n.xs.map((x) => this.c(x, env)); return (st, a) => fs.some((f) => f(st, a)); }
      case "and": { const fs = n.xs.map((x) => this.c(x, env)); return (st, a) => fs.every((f) => f(st, a)); }
      case "not": { const f = this.c(n.x, env); return (st, a) => !f(st, a); }
      case "str": { const v = n.v; return (st) => st.has(v); }
      case "num": { const v = n.v; return () => v; }
      case "tuple": { const it = this.target(n.xs[0], env), k = this.val(n.xs[1], env); return (st, a) => st.count(it) >= k(st, a); }
      case "cmp": return this.cmp(n, env);
      case "name": return this.name(n.v, env);
      case "call": return this.call(n, env);
      case "sub": { const b = this.val(n.x, env), key = this.rawname(n.key, env); return (st, a) => b(st, a)[key]; }
    }
    throw new Error("nodo no soportado " + n.t);
  }
  cmp(n, env) {
    const ln = this.rawname(n.l, env), rn = this.rawname(n.r, env);
    const special = (x) => this.setting(x) || x === "age" || x === "starting_age" || CONSTANT_NAMES.has(x);
    if (n.l.t === "name" && n.r.t === "name" && !special(ln) && !special(rn) && (n.op === "==" || n.op === "!=")) {
      const res = n.op === "==" ? ln === rn : ln !== rn; return () => res;
    }
    const l = this.val(n.l, env), r = this.val(n.r, env);
    const O = {"==": (a, b) => a === b, "!=": (a, b) => a !== b, "<": (a, b) => a < b, "<=": (a, b) => a <= b, ">": (a, b) => a > b,
      ">=": (a, b) => a >= b, "in": (a, b) => (Array.isArray(b) ? b.includes(a) : String(b).includes(a)),
      "notin": (a, b) => !(Array.isArray(b) ? b.includes(a) : String(b).includes(a))}[n.op];
    return (st, a) => O(l(st, a), r(st, a));
  }
  name(id, env) {
    if (env[id]) return this.c(env[id], {});
    if (id === "True" || id === "False") { const v = id === "True"; return () => v; }
    if (id === "starting_age") { const v = this.S.starting_age; return () => v; }
    const h = this.helpers.get(id);
    if (h && !h.params.length) {
      const key = "helper:" + id;
      if (!this.cache.has(key)) { this.cache.set(key, null); this.cache.set(key, this.c(h.body, {})); }
      const f = this.cache.get(key);
      if (f === null) { const it = this.itemOf(id); return (st) => st.has(it); }
      return (st, a) => this.cache.get(key)(st, a);
    }
    if (this.setting(id)) { const v = !!this.S[id] && !(Array.isArray(this.S[id]) && !this.S[id].length); return () => v; }
    if (/^(logic_|glitch_|adv_)/.test(id)) return () => false;
    if (id === "at_day" || id === "at_night" || id === "at_dampe_time") return () => true;
    if (id === "has_bottle") return (st) => BOTTLES.some((b) => st.has(b));
    if (CONSTANT_NAMES.has(id)) return () => id;
    if (id.startsWith("shuffle_")) return () => false;
    const it = this.itemOf(id); return (st) => st.has(it);
  }
  call(n, env) {
    const f = n.f, args = n.args, h = this.helpers.get(f);
    if (h && h.params.length) {
      const sub = {}; h.params.forEach((p, i) => { const a = args[i]; sub[p] = a.t === "name" && env[a.v] ? env[a.v] : a; });
      return this.c(h.body, sub);
    }
    if (f === "here") return this.c(args[0], env);
    if (f === "at") {
      const region = this.rawname(args[0], env), g = this.c(args[1], env), W = this.world;
      return (st) => ["child", "adult"].some((a) => W.reach[a].has(region) && g(st, a));
    }
    if (["can_live_dmg", "has_soul", "has_all_notes_for_song", "has_ocarina_buttons", "has_item_goal"].includes(f)) return () => true;
    if (f === "region_has_shortcuts") return () => false;
    if (f === "has_hearts") { const k = this.val(args[0], env); return (st, a) => 3 + st.count("Heart Container") + Math.floor(st.count("Piece of Heart") / 4) >= k(st, a); }
    if (["has_stones", "has_medallions", "has_dungeon_rewards"].includes(f)) {
      const k = this.val(args[0], env), g = f === "has_stones" ? STONES : f === "has_medallions" ? MEDALLIONS : STONES.concat(MEDALLIONS);
      return (st, a) => g.filter((x) => st.has(x)).length >= k(st, a);
    }
    throw new Error("función desconocida " + f);
  }
}

// ---------------------------------------------------------------- PRNG con semilla (mulberry32 sobre un hash de la cadena)
// Frases de las pistas por idioma (las de las piedras chismosas y la hoja de pistas)
const HINT_FMT = {
  es: {camino: (z) => `${z} está en el camino del héroe.`, inutil: (z) => `Buscar en ${z} es perder el tiempo.`,
       objeto: (n, z) => `${n} ${/^(Botas|Guantes|Flechas|Bombchus|Palos|Nueces|Bombas|Gafas)\b/i.test(n) ? "están" : "está"} en ${z}.`},
  en: {camino: (z) => `${z} is on the way of the hero.`, inutil: (z) => `${z} is a foolish choice.`,
       objeto: (n, z) => `${n} can be found in ${z}.`},
};
function rngFrom(seed) {
  let h = 1779033703 ^ String(seed).length;
  for (const ch of String(seed)) { h = Math.imul(h ^ ch.charCodeAt(0), 3432918353); h = (h << 13) | (h >>> 19); }
  let a = h >>> 0;
  const next = () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  return {next, int: (n) => Math.floor(next() * n), choice(xs) { return xs[Math.floor(next() * xs.length)]; },
    shuffle(xs) { for (let i = xs.length - 1; i > 0; i--) { const j = Math.floor(next() * (i + 1)); [xs[i], xs[j]] = [xs[j], xs[i]]; } return xs; }};
}

// ---------------------------------------------------------------- mundo + generador (v2: cofres + regalos + canciones)
const SOLO_COFRE_O_JEFE = new Set(["Obj_Heart_Container"]);
const NO_SUELO = new Set(["Item_Ocarina_Fairy", "Item_Ocarina_Time"]);
const NO_SUELO_PREFIJOS = ["Item_BombBag", "Item_Quiver", "Item_BulletBag", "Item_Scale", "Item_Gauntlet", "Item_Wallet", "Item_FairyBless_MP", "Armor_Child_Gauntlet"];   // mejoras: sin probar cogidas del suelo (core.py)
const noSuelo = (x) => NO_SUELO.has(x) || NO_SUELO_PREFIJOS.some((p) => (x || "").startsWith(p));   // la ocarina solo entra en la cruceta si se consigue con un evento
const TOPE_TIENDA = 3;   // máximo de objetos de progreso por tienda (core.TOPE_TIENDA)
const LLAVES = new Set(["Item_Dungeon_SmallKey", "Item_Dungeon_BossKey"]);   // llaves de mazmorra (opción "llaves")
class Rando {
  constructor(data, opts = {}) {
    this.D = data; this.R = data.remake;
    this.opts = Object.assign({tricks: [], excluded: [], junk: "original", regalos: false, canciones: false, cancionesTodo: false, inicio: [], corazones: 3, rupias: 0, escenas: [], suelo: "no", bosque: "cerrado", kakariko: "cerrada", fuente: "cerrada", puerta: "cerrada", puente: "normal", jefes: false, mapas: "no", recompensas: "no", tiendas: false, llaves: "no", skulltulas: true, piezas: false, precios: "originales"}, opts);
    if (this.opts.mapas === true) this.opts.mapas = "mazmorra"; if (!this.opts.mapas) this.opts.mapas = "no";
    if (!this.opts.recompensas) this.opts.recompensas = "no";
    // recompensas barajadas: la piedra/medallón cuenta solo con su jefe vencido (el juego puede abrir por pasos de historia)
    this.gate = this.opts.recompensas !== "no" ? (this.R.gate || null) : null;
    const S = Object.assign({}, data.settings);
    for (const t of this.opts.tricks) S[t] = true;
    S.open_forest = {cerrado: "closed", arbol_cerrado: "closed_deku", abierto: "open"}[this.opts.bosque] || "closed";
    S.open_kakariko = this.opts.kakariko === "abierta" ? "open" : "closed";
    S.zora_fountain = this.opts.fuente === "abierta" ? "open" : "closed";
    S.open_door_of_time = this.opts.puerta === "abierta" ? "open" : "stones_oot_sot";
    S.bridge = this.opts.puente === "abierto" ? "open" : "vanilla";
    this.regions = new Map(data.regions.map((r) => [r.region_name, r]));
    this.reach = {child: new Set(), adult: new Set()};
    const comp = new Compiler(data.helpers, data.item_names, S, this);
    this.exits = []; this.locsO = []; this.events = [];
    for (const [rn, r] of this.regions) {
      for (const [t, rule] of Object.entries(r.exits || {})) this.exits.push([rn, t, comp.compile(rule)]);
      for (const [l, rule] of Object.entries(r.locations || {})) this.locsO.push([rn, l, comp.compile(rule)]);
      for (const [e, rule] of Object.entries(r.events || {})) this.events.push([rn, e, comp.compile(rule)]);
    }
    // ubicaciones activas
    this.active = this.R.ids.filter((i) => {
      const l = this.R.locs[i];
      if (l.tipo === "regalo") return (l.grupo === "cancion" && this.opts.canciones) || (l.grupo === "regalo" && this.opts.regalos && !(this.opts.skulltulas === false && l.flow === "GatheringTokenGold")) || (l.grupo === "recompensa" && this.opts.recompensas !== "no");
      if (l.tipo === "suelo") return this.opts.suelo === "relleno" || this.opts.suelo === "todo";
      if (l.llave_suelta) return this.opts.llaves === "fuera" && this.opts.sueltas !== false;   // llaves sueltas (core.LLAVES_SUELTAS)
      if (l.tipo === "jefe") return !!this.opts[l.opcion || "jefes"];
      if (l.tipo === "tienda") return this.opts.tiendas === "todas" ? l.modo === "todas" : (!!this.opts.tiendas && l.modo === "kokiri");   // true/"kokiri": solo la Kokiri
      if (l.grupo === "mapa") return this.opts.mapas !== "no";
      if (this.esCofreLlave(l)) return this.opts.llaves === "fuera";
      return l.class !== "FIJA";
    });
    // precios aleatorios (core.fijar_precios): precio de cada estante activo = precioAleatorio(sal, clave_precio)
    this.precios = new Map(); this.salDada = this.opts.sal != null ? this.opts.sal >>> 0 : null;
    if (PRECIOS_CON_SAL.includes(this.opts.precios) && this.salDada != null) this.fijarPrecios(this.salDada);
    // llaves fuera de su mazmorra (core.py): el cofre de la llave es un sitio de la mazmorra (clase MAZMORRA) y cada llave
    // lleva su mazmorra en el nombre ("Item_Dungeon_SmallKey@ForestTemple"); no se entra en una mazmorra sin TODAS sus llaves
    this.over = new Map(); this.totalLlaves = new Map(); this.totalGran = new Set(); this.extraLlaves = []; this.bloqueadas = new Set();
    if (this.opts.llaves === "fuera") for (const i of this.active) {
      const l = this.R.locs[i]; if (!this.esCofreLlave(l)) continue;
      this.over.set(i, Object.assign({}, l, {class: "MAZMORRA", dungeon: this.R.dungeons[l.scene]}));
      if (l.vanilla === "Item_Dungeon_BossKey") { this.totalGran.add(l.scene); this.extraLlaves.push("RBGran@" + l.scene); }
      else { this.totalLlaves.set(l.scene, (this.totalLlaves.get(l.scene) || 0) + 1); this.extraLlaves.push("RBLlave@" + l.scene); }
    }
    // lógica por salas de Switch 2 (rando/salas.py; truco logic_zz_salas_switch2): las ubicaciones de esas mazmorras son EXACTA de
    // su sala; sus llaves se cuentan por puerta (sin el bloqueo de «todas las llaves»); las llaves que no se barajan (cofres de
    // llave fuera del reparto) cuentan al llegar a su sala.
    this.salasInfo = (this.opts.tricks || []).includes("logic_zz_salas_switch2") ? (this.R.salas || {}) : {};
    this.llavesFijas = [];
    if (this.opts.llaves !== "fuera") this.salasInfo = Object.fromEntries(Object.entries(this.salasInfo).filter(([sc, inf]) => inf.vale_llaves_no));
    this.salasClasicas = this.salasInfo === this.R.salas || !(this.opts.tricks || []).includes("logic_zz_salas_switch2") ? [] :
      Object.entries(this.R.salas || {}).filter(([sc]) => !this.salasInfo[sc]).map(([sc, inf]) => inf.completa);   // mazmorras que vuelven a la lógica clásica
    for (const [sc, inf] of Object.entries(this.salasInfo)) {
      for (const [i, on] of Object.entries(inf.ubicaciones)) {
        const l = this.R.locs[i]; if (!l) continue;
        this.over.set(i, Object.assign({}, l, {class: "EXACTA", ootr: on, salida: undefined}));
        if (this.esCofreLlave(l) && !this.active.includes(i)) this.llavesFijas.push([i, (l.vanilla === "Item_Dungeon_BossKey" ? "RBGran@" : "RBLlave@") + sc]);
      }
      this.totalLlaves.delete(sc); this.totalGran.delete(sc);
    }
    this.locRegion = new Map();
    for (const [rn, r] of this.regions) for (const l of Object.keys(r.locations || {})) this.locRegion.set(l, rn);
    const shuffledO = new Set(this.active.filter((i) => ["regalo", "jefe", "tienda"].includes(this.R.locs[i].tipo)).map((i) => this.R.locs[i].ootr));
    this.ootrPlac = new Map();
    for (const [n, v] of Object.entries(data.loctable)) if (v.v && v.t !== "Chest" && !shuffledO.has(n)) this.ootrPlac.set(n, v.v);
    this.dungeonChests = new Map();
    for (const [n, v] of Object.entries(data.loctable)) {
      if (v.t === "Chest" && !n.includes(" MQ ") && v.c) { if (!this.dungeonChests.has(v.c)) this.dungeonChests.set(v.c, new Set()); this.dungeonChests.get(v.c).add(n); }
    }
    const gc = this.dungeonChests.get("Ganon's Castle") || new Set();
    for (const n of this.dungeonChests.get("Ganon's Tower") || []) gc.add(n);
    this.dungeonChests.set("Ganon's Castle", gc);
    this.zonas = new Map(Object.entries(this.R.zonas || {}).map(([z, v]) => [z, new Set(v)]));
    this.base = new Map(Object.entries(data.start_items));
    for (const d of data.dungeon_keys) { this.base.set(`Small Key (${d})`, 20); this.base.set(`Boss Key (${d})`, 1); }
    for (const id of this.opts.inicio) for (const it of (this.R.inicio[id] || {logico: []}).logico) this.base.set(it, (this.base.get(it) || 0) + 1);
    for (const c of this.salasClasicas || []) this.base.set(c, 1);   // su lógica OoTR interna queda abierta como siempre
    this.orderCache = new Map();
    this.noProg = new Set(this.R.no_progreso);
    this.salidaObj = this.R.salida_obj || [];
    this.salas = new Map();   // sala sin salida sin objeto a distancia -> sus ubicaciones activas
    for (const i of this.active) { const s = this.R.locs[i].salida; if (s) { if (!this.salas.has(s)) this.salas.set(s, []); this.salas.get(s).push(i); } }
  }
  logicItem(x) { const k = llaveDe(x); if (k[1]) return (k[0] === "Item_Dungeon_BossKey" ? "RBGran@" : "RBLlave@") + k[1]; return this.R.logic_items[x]; }
  loc(i) { return this.over.get(i) || this.R.locs[i]; }
  esCofreLlave(l) { return (l.tipo === "cofre" || l.llave_suelta) && LLAVES.has(l.vanilla) && (this.R.dungeon_scenes || []).includes(l.scene); }
  nombreLogico(sc) { return String(this.R.dungeons[sc] || sc).replace(/'/g, ""); }
  sitioLlave(i, sc, grande) {   // ¿puede ir aquí una llave de la mazmorra 'sc'? (core.sitio_llave; pequeñas no en vasija/jefe)
    const l = this.loc(i);
    if (!["cofre", "regalo", "suelo"].includes(l.tipo) || l.scene === sc) return false;   // vasija sí (probado); jefe aún no
    if (l.class === "MAZMORRA" && l.dungeon === this.R.dungeons[sc]) return false;
    const rn = this.locRegion.get(l.ootr);
    return !(rn && this.regions.get(rn).dungeon === this.nombreLogico(sc));
  }
  vendible(x) {   // ¿se puede vender como artículo fabricado? (remake_tienda.vendible)
    const T = this.R.tienda || {no_prefijos: [], no: []};
    return /^(Item_|Weapon_)/.test(x) && !T.no_prefijos.some((p) => x.startsWith(p)) && !T.no.includes(x) && !/^Item_(DekuStick|DekuNut|DekuSeed|ScrubBusinessSeed)/.test(x);
  }
  cabeEnTienda(x) {
    const T = this.R.tienda || {valiosos: [], valiosos_prefijos: []};
    return this.vendible(x) || (!this.isProgress(x) && !T.valiosos.includes(x) && !T.valiosos_prefijos.some((p) => x.startsWith(p)));
  }
  esArticulo(x) { return !!(this.R.articulos && this.R.articulos[x]); }
  fijarPrecios(sal) {
    this.opts.sal = sal >>> 0; this.precios = new Map();
    for (const i of this.active) { const l = this.R.locs[i]; if (l.tipo === "tienda") this.precios.set(i, precioModo(this.opts.precios, this.opts.sal, l.clave_precio, l.precio)); }
  }
  precio(i) { return this.precios.has(i) ? this.precios.get(i) : (this.R.locs[i].precio || 0); }   // lo que cobra el estante
  compraOk(x, i, st) {   // reglas de compra de OoTR (core.compra_ok)
    const C = this.R.carteras || [200, 500, 1000], p = this.precio(i);   // precio del ESTANTE (lo que cobra el juego)
    const need = C.findIndex((m) => p <= m); if (st.count("Progressive Wallet") < (need < 0 ? C.length : need)) return false;   // cartera del remake
    for (const r of this.R.articulos[x]) {
      if (r === "botella" && !([...st.items.keys()].some((k) => k.startsWith("Bottle") && st.count(k) > 0) || st.count("Rutos Letter") >= 2)) return false;
      if (r === "bombchus" && !st.count("Bomb Bag")) return false;
      if (r === "adulto" && !this.reach.adult.has(this.locRegion.get(this.R.locs[i].ootr))) return false;
    }
    return true;
  }
  cabe(x, i) {
    const t = this.R.locs[i].tipo;
    if (this.esArticulo(x)) return t === "tienda" && !(x.startsWith("Shop_Armor_") && (this.R.solo_nino || []).includes(this.R.locs[i].scene));
    if (this.municionReq(x) && t !== "suelo") return false;   // munición solo en suelo (core.cabe, 2026-11-11)
    // mapa/brújula fuera de su mazmorra: patch2 da un "portador" (regalos, cofres y vasijas); jefe/tienda aún no
    if ((x === "Item_Dungeon_Map" || x === "Item_Dungeon_Compass") && !["regalo", "cofre", "suelo"].includes(t)) return false;
    if (t === "tienda" && !this.cabeEnTienda(x)) return false;
    if (t === "tienda" && this.precio(i) > (this.R.carteras || [200])[0] && this.isProgress(x)) return false;   // cartera (core.cabe)
    if (SOLO_COFRE_O_JEFE.has(x) && !["cofre", "jefe"].includes(t)) return false;
    if (this.R.locs[i].solo_relleno && this.isProgress(x) && x !== this.R.locs[i].vanilla) return false;   // COLOCADOS2 (core.cabe)
    if ((this.R.solo_regalo || []).includes(x) && t !== "regalo") return false;   // túnicas Obj_Armor_* y espada de Biggoron (core.cabe)
    if (t === "regalo" && /^(TBox_|Tbox_)/.test(x) && !x.startsWith("TBox_Rupee_")) return false;   // sin versión de regalo: sería rupia roja (core.cabe, 2026-11-11)
    if (!this.vendeOk(x, i)) return false;
    const k = llaveDe(x); if (LLAVES.has(k[0]) && (!k[1] || !this.sitioLlave(i, k[1], k[0] === "Item_Dungeon_BossKey"))) return false;
    return true;
  }
  vendeOk(x, i) { const l = this.R.locs[i]; return !l.vende || x === l.vanilla || (this.vendible(x) && !this.municionReq(x) && !String(x).startsWith("Item_Dungeon_")); }   // Medigoron (core.vende_ok)
  municionReq(x) { const m = (this.R.municion || []).find(([k]) => String(x || "").includes(k)); return m ? m[1] : null; }
  isProgress(x) { const lo = this.logicItem(x); return !!lo && lo !== "Piece of Heart" && !this.noProg.has(x); }
  bfs(st, age) {
    const seen = new Set(["Root"]); let changed = true;
    while (changed) { changed = false; for (const [rn, t, f] of this.exits) if (seen.has(rn) && !seen.has(t) && this.regions.has(t) && f(st, age) && !(this.bloqueadas.size && this.bloqueadas.has(this.regions.get(t).dungeon))) { seen.add(t); changed = true; } }
    return seen;
  }
  locReachable(i, reachO, st, plac, optimista = false) {   // optimista: zona/mazmorra cuenta al llegar a ALGO de ella
    const l = this.loc(i);
    if (l.salida) {   // hay que llegar de niño y tener tirachinas/bumerán, o que esté dentro de la propia sala
      if (!st || !this.reach.child.has(l.salida)) return false;
      if (!this.salidaObj.some((x) => st.has(x)) && !(this.salas.get(l.salida) || []).some((j) => plac && plac.has(j) && this.salidaObj.includes(this.logicItem(plac.get(j))))) return false;
    }
    if (optimista && l.class === "RELLENO") return true;   // sin lógica: se supone que no pide nada
    if (l.class === "EXACTA") return reachO.has(l.ootr);
    if (l.class === "MAZMORRA") { const need = this.dungeonChests.get(l.dungeon); if (!need || !need.size) return false; if (optimista) { for (const x of need) if (reachO.has(x)) return true; return false; } for (const x of need) if (!reachO.has(x)) return false; return true; }
    if (l.class === "ZONA") { const need = this.zonas.get(l.zona); if (!need || !need.size) return false; if (optimista) { for (const x of need) if (reachO.has(x)) return true; return false; } for (const x of need) if (!reachO.has(x)) return false; return true; }
    return false;
  }
  sweep(plac, extra = [], cap = {}) {
    const st = new State(); st.gate = this.gate;
    for (const [k, v] of this.base) st.add(k, v);
    for (const it of extra) st.add(it);
    const capped = () => { for (const [o, m] of Object.entries(cap)) if (st.count(o) > m) st.set(o, m); };
    const gotO = new Set(), gotV = new Set(), reachO = new Set(), reachV = new Set(), ages = ["child", "adult"];
    for (;;) {
      capped();
      this.bloqueadas = new Set([...this.totalLlaves].filter(([sc, n]) => st.count("RBLlave@" + sc) < n).map(([sc]) => sc)
        .concat([...this.totalGran].filter((sc) => !st.has("RBGran@" + sc))).map((sc) => this.nombreLogico(sc)));
      this.reach = {child: this.bfs(st, "child"), adult: this.bfs(st, "adult")};
      let neu = false;
      for (const [rn, e, f] of this.events) if (!st.has(e) && ages.some((a) => this.reach[a].has(rn) && f(st, a))) { st.add(e); neu = true; }
      for (const [rn, l, f] of this.locsO) {
        if (reachO.has(l)) continue;
        if (ages.some((a) => this.reach[a].has(rn) && f(st, a))) { reachO.add(l); const it = this.ootrPlac.get(l); if (it && !gotO.has(l)) { gotO.add(l); st.add(it); neu = true; capped(); } }
      }
      for (const [i, item] of plac) {
        if (gotV.has(i) || !this.locReachable(i, reachO, st, plac)) continue;
        if (this.esArticulo(item) && !this.compraOk(item, i, st)) continue;   // cartera/adulto/botella/bombchus
        gotV.add(i); reachV.add(i); const lo = this.logicItem(item); if (lo) { st.add(lo); neu = true; capped(); }
      }
      for (const [i, tok] of this.llavesFijas) if (!gotV.has(i) && this.locReachable(i, reachO, st, plac)) { gotV.add(i); st.add(tok); neu = true; capped(); }
      for (const [sc, inf] of Object.entries(this.salasInfo)) if (!st.has(inf.completa) && inf.regiones.every((r) => this.reach.child.has(r) || this.reach.adult.has(r))) { st.add(inf.completa); neu = true; }
      for (const i of this.active) if (!reachV.has(i) && !plac.has(i) && this.locReachable(i, reachO, st, plac)) reachV.add(i);
      if (!neu) { this.bloqueadas = new Set(); return {st, reachO, reachV}; }
    }
  }
  antesDe(obj) {   // abribles SIN 'obj' con criterio optimista (munición sin su bolsa: el juego da la bolsa, visto 2026-11-10)
    const k = "antes:" + obj;
    if (!this.orderCache.has(k)) {
      const todo = [...new Set(Object.values(this.R.logic_items))].filter((x) => x !== obj).concat(this.extraLlaves);
      const {st, reachO, reachV} = this.sweep(new Map(), todo, {[obj]: 0}); const r = new Set(reachV);
      for (const i of this.active) if (this.locReachable(i, reachO, st, new Map(), true)) r.add(i);
      this.orderCache.set(k, r);
    }
    return this.orderCache.get(k);
  }
  sinObjeto(obj) {   // ubicaciones alcanzables con TODO menos 'obj'
    const k = "sin:" + obj;
    if (!this.orderCache.has(k)) {
      const todo = [...new Set(Object.values(this.R.logic_items))].filter((x) => x !== obj).concat(this.extraLlaves);
      this.orderCache.set(k, this.sweep(new Map(), todo, {[obj]: 0}).reachV);
    }
    return this.orderCache.get(k);
  }
  allowedForOrder(item, cands) {
    if (!this.orderCache.has(item)) {
      const [obj, n] = this.R.order[item];
      const todo = [...new Set(Object.values(this.R.logic_items))].filter((x) => x !== obj).concat(this.extraLlaves);
      const {reachV} = this.sweep(new Map(), todo, {[obj]: n - 1});
      this.orderCache.set(item, new Set(cands.filter((i) => !reachV.has(i))));
    }
    return this.orderCache.get(item);
  }
  fill(rng, items, locs, plac, restLogic) {
    const remaining = items.slice();
    while (remaining.length) {
      const item = remaining.shift();
      const assumed = restLogic.concat(remaining.map((x) => this.logicItem(x)).filter(Boolean));
      let {reachV} = this.sweep(plac, assumed); const extra = new Set();
      if (this.salidaObj.includes(this.logicItem(item)) && this.salas.size) {   // el arma puede estar dentro de la sala sin salida...
        reachV = new Set(reachV); for (const i of this.sweep(plac, assumed.concat([this.logicItem(item)])).reachV) if (this.R.locs[i].salida && !reachV.has(i)) { extra.add(i); reachV.add(i); }
      }
      const allowed = this.R.order[item] ? this.allowedForOrder(item, locs) : null;
      const lleno = new Set();   // tope de objetos de progreso por tienda (core.TOPE_TIENDA, 2026-11-14)
      if (this.isProgress(item)) { const c = new Map(); for (const [j, v] of plac) if (this.R.locs[j] && this.R.locs[j].tipo === "tienda" && this.isProgress(v)) { const t = j.split(":")[1]; c.set(t, (c.get(t) || 0) + 1); }
        for (const [t, n] of c) if (n >= TOPE_TIENDA) lleno.add(t); }
      let cands = locs.filter((i) => !plac.has(i) && reachV.has(i) && !(this.R.locs[i].tipo === "tienda" && lleno.has(i.split(":")[1])) && (!allowed || allowed.has(i)) && !(this.R.locs[i].solo_relleno && this.isProgress(item) && item !== this.R.locs[i].vanilla) && !(noSuelo(item) && ["suelo", "jefe"].includes(this.R.locs[i].tipo)) && !(this.R.locs[i].tipo === "tienda" && !this.esArticulo(item) && (!this.cabeEnTienda(item) || this.precio(i) > (this.R.carteras || [200])[0])) && (!llaveDe(item)[1] || this.cabe(item, i)) && (!this.esArticulo(item) || this.cabe(item, i)) && (!(this.R.solo_regalo || []).includes(item) || this.R.locs[i].tipo === "regalo") && this.vendeOk(item, i));
      if (!cands.length) return "sin sitio para " + item;
      if (extra.size && cands.some((i) => !extra.has(i))) {   // ...pero la sala entera cuenta como UN sitio (si no, casi siempre te la regala)
        const dentro = cands.filter((i) => extra.has(i)); cands = cands.filter((i) => !extra.has(i)).concat(dentro.slice(0, 1));
      }
      plac.set(rng.choice(cands), item);
    }
    return null;
  }
  generateOnce(rng) {
    const excl = new Set(this.opts.excluded);
    // canciones "con todo": sus sitios y las canciones entran en el reparto general
    const mezclar = this.opts.canciones && this.opts.cancionesTodo;
    const canciones = mezclar ? [] : this.active.filter((i) => this.R.locs[i].grupo === "cancion");
    const recomp = this.opts.recompensas === "jefes" ? this.active.filter((i) => this.R.locs[i].grupo === "recompensa") : [];
    const resto = this.active.filter((i) => (mezclar || this.R.locs[i].grupo !== "cancion") && !recomp.includes(i));
    const progLocs = resto.filter((i) => ["EXACTA", "MAZMORRA", "ZONA"].includes(this.loc(i).class) && !excl.has(i) && (this.R.locs[i].tipo !== "suelo" || this.opts.suelo === "todo"));
    const itemsResto = resto.map((i) => this.R.locs[i].vanilla + (this.opts.llaves === "fuera" && this.esCofreLlave(this.R.locs[i]) ? "@" + this.R.locs[i].scene : ""));   // solo las llaves llevan su mazmorra
    let prog = itemsResto.filter((x) => this.isProgress(x)), junk = itemsResto.filter((x) => !this.isProgress(x));
    if (this.opts.junk === "generoso") junk = junk.map((j) => (j.startsWith("TBox_Rupee") ? rng.choice(["TBox_Rupee_Red", "TBox_Rupee_Purple", "TBox_Rupee_Purple", "TBox_Rupee_Gold"]) : j));
    else if (this.opts.junk === "tacano") junk = junk.map((j) => (j.startsWith("TBox_Rupee") ? "TBox_Rupee_Green" : j));
    const plac = new Map();
    if (canciones.length) {
      const songs = rng.shuffle(canciones.map((i) => this.R.locs[i].vanilla));
      // 2026-11-11: primero las canciones con menos sitios (Tiempo y Nana: solo sitios de niño), como rando/core.py
      const pc = (x) => (x === "Item_Melody_TimeSong" || x === "Item_Melody_ZeldaLullaby") ? 0 : 1; songs.sort((a, b) => pc(a) - pc(b));
      const err = this.fill(rng, songs, canciones, plac, prog.map((x) => this.logicItem(x)).concat(recomp.map((i) => this.logicItem(this.R.locs[i].vanilla))));
      if (err) return {ok: false, msg: err};
    }
    if (recomp.length) {   // piedras y medallones entre los sitios de recompensa
      const rews = rng.shuffle(recomp.map((i) => this.R.locs[i].vanilla));
      // 2026-11-11: piedras primero (solo caben en jefes de niño), como rando/core.py
      const pr = (x) => x.startsWith("Item_Stone_") ? 0 : 1; rews.sort((a, b) => pr(a) - pr(b));
      const err = this.fill(rng, rews, recomp, plac, prog.map((x) => this.logicItem(x)));
      if (err) return {ok: false, msg: err};
    }
    // mapas y brújulas «en su mazmorra»: ANTES de los objetos clave (2026-11-12: después, el Árbol Deku se quedaba sin cofre
    // libre y fallaban los 50 intentos de algunas semillas). No cuentan para la lógica: solo se les guarda sitio.
    const mapasPuestos = [];
    for (const i of resto.filter((i) => this.R.locs[i].grupo === "mapa" && this.opts.mapas === "mazmorra").sort((a, b) => (BigInt(a) < BigInt(b) ? -1 : 1))) {
      const it = this.R.locs[i].vanilla, dg = this.R.locs[i].dungeon;
      const cands = resto.filter((j) => !plac.has(j) && this.R.locs[j].tipo === "cofre" && this.R.locs[j].dungeon === dg && (this.R.dungeon_scenes || []).includes(this.R.locs[j].scene));
      if (!cands.length) return {ok: false, msg: `sin cofre en ${dg} para ${it}`};
      plac.set(rng.choice(cands), it); mapasPuestos.push(it);
    }
    rng.shuffle(prog);
    // mejoras con orden: las de 2.º nivel tienen pocos sitios -> primero (2026-11-11, como rando/core.py PRIORIDAD_MEJORAS)
    const pri = {Item_Gauntlet_Gold: 0, Item_BombBag_Large: 0, Item_Quiver_Large: 0, Item_Wallet_Large: 0, Item_Scale_Gold: 0,
                 Item_Gauntlet_Silver: 1, Item_Longshot: 1, Item_BombBag_Medium: 1, Item_BulletBag_Medium: 1, Item_Quiver_Medium: 1};
    const prio = (x) => (this.esArticulo(x) || (this.R.solo_regalo || []).includes(x) ? -1 : (pri[x] ?? 2));   // artículos de tienda primero (solo caben en estantes)
    prog = prog.map((x, i) => [x, i]).sort((a, b) => (prio(a[0]) - prio(b[0])) || (a[1] - b[1])).map((x) => x[0]);
    const err = this.fill(rng, prog, progLocs, plac, []);
    if (err) return {ok: false, msg: err};
    let libres = resto.filter((i) => !plac.has(i)); rng.shuffle(junk);
    for (const it of mapasPuestos) junk.splice(junk.indexOf(it), 1);
    libres.forEach((i, k) => plac.set(i, junk[k]));
    for (const i of libres) {   // tiendas: nada valioso que no se pueda vender (el estante enseñaría su artículo original)
      if (this.R.locs[i].tipo !== "tienda" || this.cabeEnTienda(plac.get(i))) continue;
      const j = libres.find((x) => this.R.locs[x].tipo !== "tienda" && this.cabeEnTienda(plac.get(x)) && !(SOLO_COFRE_O_JEFE.has(plac.get(i)) && !["cofre", "jefe"].includes(this.R.locs[x].tipo)));
      if (j !== undefined) { const t = plac.get(i); plac.set(i, plac.get(j)); plac.set(j, t); }
      else if (this.cabe("TBox_Rupee_Red", i)) plac.set(i, "TBox_Rupee_Red");   // no hay sitio que pida su bolsa/arma: rupia
    }
    for (const i of libres) {   // cualquier otra cosa que no quepa donde ha caído (mapas fuera de mazmorra...): se cambia
      if (this.cabe(plac.get(i), i)) continue;
      const j = libres.find((x) => this.cabe(plac.get(x), i) && this.cabe(plac.get(i), x));
      if (j !== undefined) { const t = plac.get(i); plac.set(i, plac.get(j)); plac.set(j, t); }
      else if (this.municionReq(plac.get(i)) && this.cabe("TBox_Rupee_Red", i)) plac.set(i, "TBox_Rupee_Red");   // munición sin sitio de suelo: rupia (core._fill)
    }
    for (const i of libres) {   // el contenedor de corazón solo en cofres o salas de jefe (sin probar en vasijas/personajes)
      if (!SOLO_COFRE_O_JEFE.has(plac.get(i)) || ["cofre", "jefe"].includes(this.R.locs[i].tipo)) continue;
      const j = libres.find((x) => ["cofre", "jefe"].includes(this.R.locs[x].tipo) && !SOLO_COFRE_O_JEFE.has(plac.get(x)));
      if (j === undefined) return {ok: false, msg: "sin cofre para el contenedor de corazón"};
      const t = plac.get(i); plac.set(i, plac.get(j)); plac.set(j, t);
    }
    // munición que sin su bolsa/arma se pierde (0/0: bombchus sin bolsa de bombas, visto en juego) -> solo donde ya se tiene
    // (2026-11-11) con ESTA colocación, no con el antesDe optimista (que deja 0 vasijas después del arco/la bolsa): core._fill
    const antesC = new Map(), antes = (req) => {
      if (!antesC.has(req)) {
        const {st, reachO, reachV} = this.sweep(plac, [], {[req]: 0}); const r = new Set(reachV);
        for (const i of this.active) if (this.locReachable(i, reachO, st, plac, true)) r.add(i);
        antesC.set(req, r);
      }
      return antesC.get(req);
    };
    for (const i of libres) {
      const req = this.municionReq(plac.get(i)); if (!req || !antes(req).has(i)) continue;
      const j = libres.find((x) => !antes(req).has(x) && !this.municionReq(plac.get(x)) && this.cabe(plac.get(x), i) && this.cabe(plac.get(i), x));
      if (j !== undefined) { const t = plac.get(i); plac.set(i, plac.get(j)); plac.set(j, t); }
      else if (this.cabe("TBox_Rupee_Red", i)) plac.set(i, "TBox_Rupee_Red");   // no hay sitio que pida su bolsa/arma: rupia
    }
    if (!this.sweep(plac).reachO.has("Ganon")) return {ok: false, msg: "Ganon no alcanzable"};
    return {ok: true, vplac: plac};
  }
  generate(seed, tries = 50) {
    let last = "";
    // precios aleatorios: la sal sale de la semilla (salvo que venga dada) y va en el código (encodeCode con {sal: r.sal})
    if (PRECIOS_CON_SAL.includes(this.opts.precios)) this.fijarPrecios(this.salDada != null ? this.salDada : salPrecios(seed));
    const extra = PRECIOS_CON_SAL.includes(this.opts.precios) ? {sal: this.opts.sal} : {};
    for (let k = 0; k < tries; k++) { const r = this.generateOnce(rngFrom(seed + "#" + k)); if (r.ok) return Object.assign(r, {seed, subseed: k}, extra); last = r.msg; }
    return {ok: false, msg: last || "no se encontró reparto válido"};
  }
  beatable(plac) { return this.sweep(plac).reachO.has("Ganon"); }
  wayOfTheHero(plac) {
    const out = [];
    for (const [i, it] of plac) { if (!this.isProgress(it)) continue; const w = new Map(plac); w.set(i, "TBox_Rupee_Green"); if (!this.beatable(w)) out.push([i, it]); }
    return out;
  }
  barrenZones(plac, woth, zoneOf) {
    const req = new Set(woth.map(([i]) => i)), zones = new Map();
    for (const i of plac.keys()) { const z = zoneOf(i); if (!zones.has(z)) zones.set(z, false); if (req.has(i)) zones.set(z, true); }
    return [...zones].filter(([, has]) => !has).map(([z]) => z);
  }
  hints(plac, rng, zoneOf, itemName, count = 12, fmt = HINT_FMT.es) {
    const woth = this.wayOfTheHero(plac), barren = this.barrenZones(plac, woth, zoneOf), out = [];
    const wothZones = rng.shuffle([...new Set(woth.map(([i]) => zoneOf(i)))]); rng.shuffle(barren);
    for (const z of wothZones.slice(0, 4)) out.push({tipo: "camino", texto: fmt.camino(z)});
    for (const z of barren.slice(0, 3)) out.push({tipo: "inutil", texto: fmt.inutil(z)});
    const prog = rng.shuffle([...plac].filter(([, it]) => this.isProgress(it)));
    for (const [i, it] of prog) { if (out.length >= count) break; out.push({tipo: "objeto", texto: fmt.objeto(itemName(it), zoneOf(i))}); }
    return {hints: out.slice(0, count), woth, barren};
  }
  trackerReach(logicalItems) {
    const {reachV, reachO, st} = this.sweep(new Map(), logicalItems);
    // solo tracker (2026-11-12, usuaria «jefe junto»): corazones de jefe y objetos colocados son RELLENO para el reparto
    // (nunca objeto clave), pero tienen su regla OoTR: si se llega a ella, salen «al alcance» junto a la recompensa del jefe
    for (const i of this.active) { const l = this.loc(i); if (l.class === "RELLENO" && l.ootr && reachO.has(l.ootr)) reachV.add(i); }
    return {reach: reachV, st};
  }
  spheres(plac) {
    const out = [], have = new Map(), prog = new Map([...plac].filter(([, x]) => this.isProgress(x)));
    while (prog.size) {
      const {reachV} = this.sweep(new Map([...plac].filter(([i]) => have.has(i))));
      const got = [...prog.keys()].filter((i) => reachV.has(i));
      if (!got.length) break;
      out.push(got.map((i) => [i, prog.get(i)]));
      for (const i of got) { have.set(i, prog.get(i)); prog.delete(i); }
    }
    return out;
  }
}

// ---------------------------------------------------------------- código de semilla v2
const b64u = {
  enc(bytes) { let s = ""; for (const b of bytes) s += String.fromCharCode(b); return (typeof btoa !== "undefined" ? btoa(s) : Buffer.from(bytes).toString("base64")).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); },
  dec(str) { const s = str.replace(/-/g, "+").replace(/_/g, "/"); const bin = typeof atob !== "undefined" ? atob(s + "===".slice((s.length + 3) % 4)) : Buffer.from(s, "base64").toString("binary"); return Uint8Array.from(bin, (c) => c.charCodeAt(0)); },
};
// ---------------------------------------------------------------- precios aleatorios (igual que remake_tienda.precio_aleatorio)
const utf8 = (s) => (typeof TextEncoder !== "undefined" ? [...new TextEncoder().encode(String(s))] : [...Buffer.from(String(s), "utf8")]);
function fmix32(h) { h ^= h >>> 16; h = Math.imul(h, 0x85EBCA6B); h ^= h >>> 13; h = Math.imul(h, 0xC2B2AE35); h ^= h >>> 16; return h >>> 0; }
function salPrecios(seed) { return crc32(utf8("precios#" + seed)); }
// Beta(1.5, 2) como el OoTR (World.py:725): 0..295 en múltiplos de 5, aquí con mínimo 5. F(x) = 2.5·x^1.5 − 1.5·x^2.5
// Modos (= remake_tienda.precio_modo; 2026-11-11): aleatorios (Beta del OoTR), faciles (5..20, nunca más que el original),
// decentes (50..150 % del original, redondeo a 5, mínimo 5). Bits del código: flags2 16 = hay sal, 32 = fáciles, 64 = decentes.
const PRECIOS_CON_SAL = ["aleatorios", "faciles", "decentes"];
function uPrecio(sal, clave) { return fmix32((crc32(utf8(clave)) ^ (sal >>> 0)) >>> 0) / 4294967296; }
function precioModo(modo, sal, clave, original) {
  if (modo === "aleatorios") return precioAleatorio(sal, clave);
  const u = uPrecio(sal, clave);
  if (modo === "faciles") return Math.max(5, Math.min(original, 5 * (1 + Math.floor(u * 4))));
  if (modo === "decentes") return Math.max(5, 5 * Math.floor(original * (0.5 + u) / 5 + 0.5));
  return original;
}
function precioAleatorio(sal, clave) {
  const u = uPrecio(sal, clave);
  let k = 0;
  while (k < 59) { const x = (k + 1) / 60, r = Math.sqrt(x); if (2.5 * x * r - 1.5 * x * x * r > u) break; k++; }
  return Math.max(5, 5 * k);
}
function crc32(bytes) { let c, crc = 0xFFFFFFFF; for (const b of bytes) { c = (crc ^ b) & 0xFF; for (let k = 0; k < 8; k++) c = c & 1 ? (c >>> 1) ^ 0xEDB88320 : c >>> 1; crc = (crc >>> 8) ^ c; } return (crc ^ 0xFFFFFFFF) >>> 0; }
const bits = (list, sel) => { const b = new Uint8Array(Math.ceil(list.length / 8)); for (const x of sel) { const i = list.indexOf(x); if (i >= 0) b[i >> 3] |= 1 << (i & 7); } return [...b]; };
const unbits = (list, b) => list.filter((x, i) => b[i >> 3] & (1 << (i & 7)));
// Formato v5 (v3 + mundo + pistas tras rupias): ver, flags(regalos|canciones<<1|cancionesTodo<<2), escenas (16 bits), corazones, rupias(2B), nInicio, bits inicio, nTrucos, bits trucos, nUbic, índice de objeto por ubicación (255 = sin cambiar), crc32
// precios aleatorios (flags2 bit 16): 4 bytes de sal (big endian) justo después de flags2; sin el bit, nada (códigos de antes)
function salBytes(o) {
  if (!PRECIOS_CON_SAL.includes(o.precios)) return [];
  if (o.sal == null) throw new Error("Precios con sal sin sal: pasa {sal: r.sal} del resultado de generate");
  const v = o.sal >>> 0; return [v >>> 24, (v >>> 16) & 255, (v >>> 8) & 255, v & 255];
}
function encodeCode(data, plac, o) {
  const R = data.remake, ini = Object.keys(R.inicio), tb = bits(data.tricks, o.tricks || []), ib = bits(ini, o.inicio || []);
  const esc = (data.remake.escenas || []).reduce((a, [k], i) => a | ((o.escenas || []).includes(k) ? 1 << i : 0), 0);
  const body = [data.code_version, (o.regalos ? 1 : 0) | (o.canciones ? 2 : 0) | (o.canciones && o.cancionesTodo ? 4 : 0) | (o.suelo === "relleno" ? 8 : 0) | (o.suelo === "todo" ? 16 : 0) | (o.jefes ? 32 : 0) | (o.mapas === "mazmorra" || o.mapas === true ? 64 : 0) | (o.recompensas === "jefes" ? 128 : 0), esc & 255, (esc >> 8) & 255, Math.max(0, ["cerrado", "arbol_cerrado", "abierto"].indexOf(o.bosque || "cerrado")) | (o.kakariko === "abierta" ? 4 : 0) | (o.fuente === "abierta" ? 8 : 0) | (o.puerta === "abierta" ? 16 : 0) | (o.puente === "abierto" ? 32 : 0) | (o.mapas === "cualquiera" ? 64 : 0) | (o.recompensas === "cualquiera" ? 128 : 0), o.corazones || 3, (o.rupias || 0) >> 8, (o.rupias || 0) & 255, Math.max(0, Math.min(40, o.pistas ?? 12)), (o.tiendas ? 1 : 0) | (o.llaves === "fuera" ? 2 : 0) | (o.tiendas === "todas" ? 4 : 0) | (o.skulltulas === false ? 8 : 0) | (PRECIOS_CON_SAL.includes(o.precios) ? 16 : 0) | (o.precios === "faciles" ? 32 : 0) | (o.precios === "decentes" ? 64 : 0) | (o.piezas ? 128 : 0),
    ...salBytes(o), ib.length, ...ib, tb.length, ...tb, R.ids.length >> 8, R.ids.length & 255, ...R.ids.map((i) => (plac.has(i) ? R.items.indexOf(plac.get(i)) : 255))];
  const c = crc32(body);
  return "OOT2-" + b64u.enc(Uint8Array.from([...body, c >>> 24, (c >>> 16) & 255, (c >>> 8) & 255, c & 255]));
}
function decodeCode(data, code) {
  const m = String(code).trim().match(/^OOT2-([A-Za-z0-9_-]+)$/);
  if (!m) throw new Error("El código debe empezar por OOT2-");
  const b = b64u.dec(m[1]); if (b.length < 12) throw new Error("El código está incompleto o mal copiado.");
  const body = b.slice(0, -4), c = crc32(body);
  if (((b[b.length - 4] << 24) | (b[b.length - 3] << 16) | (b[b.length - 2] << 8) | b[b.length - 1]) >>> 0 !== c) throw new Error("Código dañado (no cuadra la suma de control)");
  const ver = body[0];
  if (ver !== data.code_version && ver !== 5) throw new Error("Código de otra versión del randomizer");
  const R = data.remake, ini = Object.keys(R.inicio); let p = 1;
  const flags = body[p++], esc = body[p++] | (body[p++] << 8), mundo = body[p++], corazones = body[p++], rupias = (body[p++] << 8) | body[p++], pistas = body[p++];
  const flags2 = ver >= 6 ? body[p++] : 0;   // v6: byte de opciones nuevas (bit 1 = tiendas)
  let sal = null; if (flags2 & 16) { sal = ((body[p] << 24) | (body[p + 1] << 16) | (body[p + 2] << 8) | body[p + 3]) >>> 0; p += 4; }   // precios aleatorios
  const il = body[p++], inicio = unbits(ini, body.slice(p, p + il)); p += il;
  const tl = body[p++], tricks = unbits(data.tricks, body.slice(p, p + tl)); p += tl;
  const n = (body[p++] << 8) | body[p++];
  // n_anteriores: códigos de versiones anteriores (mismas ubicaciones en el mismo orden, sin las añadidas después)
  if (n !== R.ids.length && !(R.n_anteriores || []).includes(n)) throw new Error("Código de otra versión del randomizer");
  const plac = new Map(); R.ids.slice(0, n).forEach((i, k) => { const v = body[p + k]; if (v !== 255) plac.set(i, R.items[v]); });
  return {plac, opciones: {regalos: !!(flags & 1), canciones: !!(flags & 2), cancionesTodo: !!(flags & 4), bosque: ["cerrado", "arbol_cerrado", "abierto"][mundo & 3] || "cerrado", kakariko: mundo & 4 ? "abierta" : "cerrada", fuente: mundo & 8 ? "abierta" : "cerrada", puerta: mundo & 16 ? "abierta" : "cerrada", puente: mundo & 32 ? "abierto" : "normal", suelo: flags & 16 ? "todo" : (flags & 8 ? "relleno" : "no"), jefes: !!(flags & 32), mapas: mundo & 64 ? "cualquiera" : (flags & 64 ? "mazmorra" : "no"), recompensas: mundo & 128 ? "cualquiera" : (flags & 128 ? "jefes" : "no"), tiendas: flags2 & 4 ? "todas" : (flags2 & 1 ? "kokiri" : false), llaves: flags2 & 2 ? "fuera" : "no", skulltulas: !(flags2 & 8), piezas: !!(flags2 & 128), escenas: (data.remake.escenas || []).filter((e, i) => esc & (1 << i)).map((e) => e[0]), corazones, rupias, pistas, inicio, tricks, ...(R.ids.slice(0, n).some((i) => (R.locs[i] || {}).llave_suelta) ? {} : {sueltas: false}), ...(sal != null ? {precios: flags2 & 32 ? "faciles" : (flags2 & 64 ? "decentes" : "aleatorios"), sal} : {})}};
}
const HASH_ICONS = ["Espada", "Escudo", "Ocarina", "Bumerán", "Gancho", "Arco", "Bomba", "Martillo", "Botas", "Lente", "Botella", "Corazón",
  "Rupia", "Hada", "Trifuerza", "Máscara", "Canción", "Llave", "Mapa", "Brújula", "Piedra", "Medallón", "Flecha", "Tirachinas", "Guantelete",
  "Nuez", "Palo", "Pez", "Bicho", "Poe", "Cuco", "Huevo"];
function seedHash(code) { const c = crc32(Array.from(code, (ch) => ch.charCodeAt(0))); return [0, 1, 2, 3, 4].map((i) => HASH_ICONS[(c >>> (i * 6)) & 31]); }

function llaveDe(x) { const s = String(x || ""); const k = s.indexOf("@"); return k < 0 ? [s, null] : [s.slice(0, k), s.slice(k + 1)]; }
const api = {parse, Compiler, State, Rando, rngFrom, HINT_FMT, encodeCode, decodeCode, seedHash, crc32, salPrecios, precioAleatorio, precioModo, PRECIOS_CON_SAL};
if (typeof module !== "undefined" && module.exports) module.exports = api; else root.OoTRando = api;
})(typeof window !== "undefined" ? window : globalThis);
