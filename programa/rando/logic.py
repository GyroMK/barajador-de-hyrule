"""Motor de lógica propio que interpreta las reglas de los JSON del OoTR (data/World + LogicHelpers).

Reglas = expresiones tipo Python. Se compilan a funciones f(st, age) -> valor.
  Nombre de objeto (Kokiri_Sword)      -> st.has('Kokiri Sword')
  'Cadena entre comillas'              -> st.has('Cadena')   (eventos u objetos)
  (Objeto, n)                          -> st.count(Objeto) >= n
  ajuste == 'valor'                    -> comparación con SETTINGS
  helper / helper(args)                -> se sustituye su definición
  at('Región', regla), here(regla)     -> regla evaluada en otra región / aquí
"""
import ast, collections, re
import ootr_data as D

# --------------------------------------------------------------------------- ajustes "juego normal"
SETTINGS = {
    "open_forest": "closed", "open_kakariko": "closed", "open_door_of_time": "stones_oot_sot",
    "zora_fountain": "closed", "gerudo_fortress": "normal", "bridge": "vanilla",
    "bridge_stones": 3, "bridge_medallions": 6, "bridge_rewards": 9, "bridge_tokens": 100, "bridge_hearts": 20,
    "lacs_condition": "vanilla", "lacs_stones": 3, "lacs_medallions": 6, "lacs_rewards": 9, "lacs_tokens": 100, "lacs_hearts": 20,
    "ganon_bosskey_stones": 3, "ganon_bosskey_medallions": 6, "ganon_bosskey_rewards": 9, "ganon_bosskey_tokens": 100,
    "ganon_bosskey_hearts": 20, "shuffle_ganon_bosskey": "vanilla",
    "starting_age": "child", "damage_multiplier": "normal", "deadly_bonks": "none",
    "skipped_trials": {"Forest": False, "Fire": False, "Water": False, "Shadow": False, "Spirit": False, "Light": False},
    "big_poe_count": 10, "chicken_count": 7, "scarecrow_behavior": "vanilla",
    "shuffle_gerudo_fortress_heart_piece": "keep", "dungeon_shortcuts": [], "keysanity": False,
    "shuffle_tcgkeys": "vanilla", "hints": "none", "triforce_goal_per_world": 0,
    "selected_adult_trade_item": "Claim Check", "adult_trade_shuffle": False,
    "entrance_shuffle": False, "free_bombchu_drops": False, "complete_mask_quest": False,
    "plant_beans": False, "warp_songs": False, "skip_child_zelda": False, "skip_reward_from_rauru": "not_free",
    "shuffle_silver_rupees": "vanilla",
}
# palabras sueltas que el OoTR usa como "constantes" (edades, enemigos, pruebas...)
CONSTANT_NAMES = {"child", "adult", "both", "either", "Forest", "Fire", "Water", "Shadow", "Spirit", "Light"}

def _default_setting(name):
    if name.startswith(("logic_", "glitch_", "adv_", "shuffle_")): return False
    return None

# --------------------------------------------------------------------------- estado
# objetos iniciales implícitos (como hace el OoTR con llaves en su sitio, ItemPool.py)
START_ITEMS = {"Small Key (Fire Temple)": 1}

class State:
    def __init__(self, start=True):
        self.items = collections.Counter(START_ITEMS if start else {})
    def has(self, name, n=1):
        return self.items[name] >= n
    def count(self, name):
        return self.items[name]
    def copy(self):
        s = State(); s.items = self.items.copy(); return s

def escape(name):
    return re.sub(r"[^A-Za-z0-9_]", "", name.replace(" ", "_").replace("-", "_"))

# --------------------------------------------------------------------------- compilador
class Compiler:
    def __init__(self, helpers, item_names, world):
        self.items = {escape(n): n for n in item_names}
        self.world = world          # se usa para at()
        self.helpers = {}
        for k, v in helpers.items():
            m = re.match(r"^(\w+)\((.*)\)$", k)
            name, params = (m.group(1), [p.strip() for p in m.group(2).split(",") if p.strip()]) if m else (k, [])
            self.helpers[name] = (params, ast.parse(v, mode="eval").body)
        self.cache = {}

    def compile(self, rule):
        if rule not in self.cache:
            self.cache[rule] = self.c(ast.parse(rule, mode="eval").body, {})
        return self.cache[rule]

    # nombre "crudo" de un nodo (para comparaciones item == Bow)
    def rawname(self, n, env):
        if isinstance(n, ast.Name):
            if n.id in env: return self.rawname(env[n.id], {})
            return n.id
        if isinstance(n, ast.Constant): return n.value
        return None

    def item_of(self, ident):
        if ident in self.items: return self.items[ident]
        return ident.replace("_", " ")

    def c(self, n, env):
        if isinstance(n, ast.BoolOp):
            fs = [self.c(v, env) for v in n.values]
            if isinstance(n.op, ast.And): return lambda st, age, fs=fs: all(f(st, age) for f in fs)
            return lambda st, age, fs=fs: any(f(st, age) for f in fs)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            f = self.c(n.operand, env); return lambda st, age: not f(st, age)
        if isinstance(n, ast.Constant):
            v = n.value
            if isinstance(v, str): return lambda st, age, v=v: st.has(v)
            return lambda st, age, v=v: v
        if isinstance(n, ast.Tuple):                          # (Objeto, n)
            item = self.name_target(n.elts[0], env)
            cnt = self.c_value(n.elts[1], env)
            return lambda st, age: st.count(item) >= cnt(st, age)
        if isinstance(n, ast.Compare):
            return self.c_compare(n, env)
        if isinstance(n, ast.Name):
            return self.c_name(n.id, env)
        if isinstance(n, ast.Call):
            return self.c_call(n, env)
        if isinstance(n, ast.Subscript):                      # skipped_trials[Forest]
            base = self.c_value(n.value, env); key = self.rawname(n.slice, env)
            return lambda st, age: base(st, age)[key]
        raise ValueError(f"nodo no soportado: {ast.dump(n)[:120]}")

    def name_target(self, n, env):
        """Nombre de objeto/evento al que se refiere un nodo (para tuplas y has_soul...)."""
        if isinstance(n, ast.Name) and n.id in env: return self.name_target(env[n.id], {})
        if isinstance(n, ast.Constant): return n.value
        if isinstance(n, ast.Name):
            if n.id in self.helpers and not self.helpers[n.id][0]:
                body = self.helpers[n.id][1]
                if isinstance(body, ast.Name): return self.name_target(body, {})
                if isinstance(body, ast.Constant): return body.value
            return self.item_of(n.id)
        raise ValueError("objetivo raro")

    def c_value(self, n, env):
        """Valor (no booleano): ajustes, números, cadenas."""
        if isinstance(n, ast.Constant): return lambda st, age, v=n.value: v
        if isinstance(n, ast.Name):
            if n.id in env: return self.c_value(env[n.id], {})
            if n.id == "age": return lambda st, age: age
            if n.id in SETTINGS: return lambda st, age, v=SETTINGS[n.id]: v
            if n.id in CONSTANT_NAMES: return lambda st, age, v=n.id: v
            if n.id in self.helpers and not self.helpers[n.id][0]:
                return self.c_value(self.helpers[n.id][1], {})
            d = _default_setting(n.id)
            if d is not None: return lambda st, age, v=d: v
            return lambda st, age, v=n.id: v
        if isinstance(n, ast.Subscript): return self.c(n, env)
        return self.c(n, env)

    def c_compare(self, n, env):
        assert len(n.ops) == 1
        l, r, op = n.left, n.comparators[0], n.ops[0]
        # item == Bow (comparación de nombres en tiempo de compilación)
        ln, rn = self.rawname(l, env), self.rawname(r, env)
        if isinstance(l, ast.Name) and isinstance(r, ast.Name) and ln not in SETTINGS and rn not in SETTINGS \
                and ln not in ("age", "starting_age") and rn not in ("age", "starting_age") \
                and ln not in CONSTANT_NAMES and rn not in CONSTANT_NAMES:
            res = (ln == rn) if isinstance(op, ast.Eq) else (ln != rn)
            return lambda st, age, res=res: res
        lf, rf = self.c_value(l, env), self.c_value(r, env)
        ops = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: a < b,
               ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b,
               ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}
        o = ops[type(op)]
        return lambda st, age: o(lf(st, age), rf(st, age))

    def c_name(self, ident, env):
        if ident in env:
            return self.c(env[ident], {})
        if ident in ("True", "False"): return lambda st, age, v=(ident == "True"): v
        if ident == "starting_age": return lambda st, age: SETTINGS["starting_age"]
        if ident in self.helpers and not self.helpers[ident][0]:
            key = ("helper", ident)
            if key not in self.cache:
                self.cache[key] = None
                self.cache[key] = self.c(self.helpers[ident][1], {})
            f = self.cache[key]
            if f is None:   # recursión (alias de objeto a sí mismo): tratar como objeto
                item = self.item_of(ident); return lambda st, age: st.has(item)
            return f
        if ident in SETTINGS:
            v = SETTINGS[ident]; return lambda st, age, v=v: bool(v)
        if ident.startswith(("logic_", "glitch_", "adv_")): return lambda st, age: False
        if ident in ("at_day", "at_night", "at_dampe_time"): return lambda st, age: True
        if ident == "has_bottle":
            return lambda st, age: any(st.has(b) for b in BOTTLES)
        if ident in CONSTANT_NAMES: return lambda st, age, v=ident: v
        d = _default_setting(ident)
        if d is not None and ident.startswith("shuffle_"): return lambda st, age, v=d: v
        item = self.item_of(ident)
        return lambda st, age: st.has(item)

    def c_call(self, n, env):
        fn = n.func.id
        args = n.args
        if fn in self.helpers and self.helpers[fn][0]:
            params, body = self.helpers[fn]
            sub = dict(zip(params, [env.get(a.id, a) if isinstance(a, ast.Name) else a for a in args]))
            return self.c(body, sub)
        if fn == "here": return self.c(args[0], env)
        if fn == "at":
            region = self.rawname(args[0], env); f = self.c(args[1], env)
            world = self.world
            return lambda st, age: any(region in world.reach[a] and f(st, a) for a in ("child", "adult"))
        if fn in ("can_live_dmg", "has_soul", "has_all_notes_for_song", "has_ocarina_buttons", "has_item_goal"):
            return lambda st, age: True
        if fn == "region_has_shortcuts": return lambda st, age: False
        if fn in ("has_stones", "has_medallions", "has_dungeon_rewards", "has_hearts"):
            cnt = self.c_value(args[0], env)
            group = {"has_stones": STONES, "has_medallions": MEDALLIONS,
                     "has_dungeon_rewards": STONES + MEDALLIONS}.get(fn)
            if fn == "has_hearts":
                return lambda st, age: 3 + st.count("Heart Container") + st.count("Piece of Heart") // 4 >= cnt(st, age)
            return lambda st, age, g=group: sum(1 for x in g if st.has(x)) >= cnt(st, age)
        raise ValueError(f"función desconocida {fn}")

STONES = ["Kokiri Emerald", "Goron Ruby", "Zora Sapphire"]
MEDALLIONS = ["Forest Medallion", "Fire Medallion", "Water Medallion", "Shadow Medallion", "Spirit Medallion", "Light Medallion"]
BOTTLES = ["Bottle", "Bottle with Milk", "Bottle with Red Potion", "Bottle with Green Potion", "Bottle with Blue Potion",
           "Bottle with Fairy", "Bottle with Fish", "Bottle with Blue Fire", "Bottle with Bugs", "Bottle with Poe",
           "Bottle with Big Poe", "Rutos Letter"]

# --------------------------------------------------------------------------- mundo y búsqueda
class World:
    def __init__(self):
        self.regions = {r["region_name"]: r for r in D.load_world()}
        self.loctable = D.load_location_table()
        src = open(D.REF + "/ItemList.py", encoding="utf-8").read()
        names = set(re.findall(r"^\s*'([^']+)'\s*:\s*\(", src, flags=re.M))
        self.comp = Compiler(D.load_helpers(), names, self)
        self.reach = {"child": set(), "adult": set()}
        # precompilar
        self.exits, self.locs, self.events = [], [], []
        for rn, r in self.regions.items():
            for t, rule in (r.get("exits") or {}).items():
                self.exits.append((rn, t, self.comp.compile(rule)))
            for l, rule in (r.get("locations") or {}).items():
                self.locs.append((rn, l, self.comp.compile(rule)))
            for e, rule in (r.get("events") or {}).items():
                self.events.append((rn, e, self.comp.compile(rule)))
        self.loc_region = {l: rn for rn, l, _ in self.locs}

    def _bfs(self, st, age):
        seen = {"Root"}
        changed = True
        while changed:
            changed = False
            for rn, t, f in self.exits:
                if rn in seen and t not in seen and t in self.regions and f(st, age):
                    seen.add(t); changed = True
        return seen

    def sweep(self, st, placement, collect=True):
        """Repite: regiones alcanzables -> eventos -> ubicaciones -> recoger objetos, hasta el punto fijo.
        Devuelve el conjunto de ubicaciones alcanzables. Modifica st."""
        got = set()
        reachable_locs = set()
        while True:
            self.reach = {a: self._bfs(st, a) for a in ("child", "adult")}
            new = False
            for rn, e, f in self.events:
                if not st.has(e) and any(rn in self.reach[a] and f(st, a) for a in ("child", "adult")):
                    st.items[e] += 1; new = True
            for rn, l, f in self.locs:
                if l in reachable_locs: continue
                if any(rn in self.reach[a] and f(st, a) for a in ("child", "adult")):
                    reachable_locs.add(l)
                    it = placement.get(l)
                    if collect and it and l not in got:
                        got.add(l); st.items[it] += 1; new = True
            if not new:
                return reachable_locs
