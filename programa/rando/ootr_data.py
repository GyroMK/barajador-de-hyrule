"""Carga de los datos de lógica del OoTR (MIT, https://github.com/OoTRandomizer/OoT-Randomizer).
Solo se leen ficheros de datos; no se ejecuta código del OoTR.
"""
import ast, json, os, re

REF = os.environ.get("OOTR_REF", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "referencia", "ootr"))

def read_logic_json(path):
    """JSON del OoTR: admite comentarios '#' de línea completa y cadenas multilínea."""
    text = open(path, encoding="utf-8").read()
    # quitar comentarios '#' fuera de cadenas
    out, in_str, i = [], False, 0
    while i < len(text):
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\": out.append(text[i + 1]); i += 2; continue
            if c == '"': in_str = False
        elif c == '"':
            in_str = True; out.append(c)
        elif c == "#":
            while i < len(text) and text[i] != "\n": i += 1
            continue
        else:
            out.append(c)
        i += 1
    text = "".join(out)
    text = re.sub(r",(\s*[}\]])", r"\1", text)          # comas finales
    try:
        data = json.loads(text, strict=False)
    except json.JSONDecodeError as e:
        raise SystemExit(f"{os.path.basename(path)}: {e}\n...{text[max(0, e.pos - 120):e.pos + 60]!r}")
    def clean(x):
        if isinstance(x, str): return " ".join(x.split())
        if isinstance(x, dict): return {k: clean(v) for k, v in x.items()}
        if isinstance(x, list): return [clean(v) for v in x]
        return x
    return clean(data)

def load_helpers():
    return read_logic_json(os.path.join(REF, "data", "LogicHelpers.json"))

def load_world(include_mq=False):
    """Lista de regiones de todos los JSON de data/World (sin Master Quest por defecto)."""
    regions = []
    wdir = os.path.join(REF, "data", "World")
    for f in sorted(os.listdir(wdir)):
        if not f.endswith(".json"): continue
        if " MQ" in f and not include_mq: continue
        for r in read_logic_json(os.path.join(wdir, f)):
            r["_file"] = f
            regions.append(r)
    for (rn, nombre), regla in REGLAS_REMAKE.items():   # salida o ubicación de la región
        r = next(r for r in regions if r["region_name"] == rn)
        sitio = next((k for k in ("exits", "locations", "events") if nombre in (r.get(k) or {})), "locations")
        assert nombre in (r.get(sitio) or {}), (rn, nombre)
        r[sitio][nombre] = regla
    # Lógica por salas de Switch 2 (opción experimental, rando/salas.py): regiones nuevas por sala; sin la opción no cambia nada.
    import salas as SALAS, remake as _RM
    SALAS.inyectar(regions, lambda esc: _RM.DUNGEONS[esc].replace("'", ""))
    # Salas de jefe (auditoría 2026-11-13): en Switch 2 no se sale sin vencer al jefe (Gohma por Dm_Deku_0003, Barinade, Ganon
    # Fantasma, Morfa, Twinrova por el reto; Rey Dodongo, Volvagia, Bongo se entra cayendo) y no hay save warp. Con «llaves: fuera»
    # la gran llave puede llegar antes de tiempo -> entrar en la sala pide además lo que pide vencerlo («Defeat X»).
    jefes = {r["region_name"]: next(v for k, v in r["events"].items() if k.startswith("Defeat "))
             for r in regions if r["region_name"].endswith(" Boss Room") and any(k.startswith("Defeat ") for k in (r.get("events") or {}))}
    for r in regions:
        for destino, regla in list((r.get("exits") or {}).items()):
            if destino in jefes and r["region_name"] not in jefes and regla != "False":
                r["exits"][destino] = f"({regla}) and ({jefes[destino]})"
    return regions

# Reglas de OoTR que en Switch 2 son distintas. Cada una va con la prueba en juego que la justifica.
REGLAS_REMAKE = {
    # Tumba de la Canción del Sol (la de los ReDead): en el remake su cofre (Obj_TBox_A_06 16912540161937823130, el del escudo) está
    # SIEMPRE; la usuaria lo abrió sin ocarina el 2026-11-13 (corrige 2026-11-11, que confundió las dos tumbas).
    # OoTR pedía can_play(Suns_Song). Entrar en la tumba sigue pidiendo lo de OoTR (adulto o de noche).
    ("Graveyard Heart Piece Grave", "Graveyard Heart Piece Grave Chest"): "True",
    # PROBADO por la usuaria el 2026-11-09 (semilla web-e703b1fd): el Deku Scrub de la sala de antes del tirachinas
    # no muere con su nuez rebotada; el escudo lo para, pero hay que golpearlo. OoTR: here(has_shield).
    # can_child_damage (no can_child_attack): el bumerán solo aturde (OoTR LogicHelpers.json:44-45). 2026-11-10.
    ("Deku Tree Lobby", "Deku Tree Slingshot Room"): "here(has_shield and (is_adult or can_child_damage))",
    # Visto por la usuaria el 2026-11-10: para llegar a la sala de la brújula hay que trepar una enredadera con Skulltulas
    # que siempre te tiran. Sin arma no se pasa (OoTR: True; para la Skulltula dorada de esa sala ya pide is_adult or
    # can_child_attack). Se pide lo mismo para los dos cofres de esa sala.
    ("Deku Tree Lobby", "Deku Tree Compass Chest"): "is_adult or can_child_damage",
    ("Deku Tree Lobby", "Deku Tree Compass Room Side Chest"): "is_adult or can_child_damage",
    # Auditoría de los AINB 2026-11-10 (leído en los ficheros, SIN PROBAR EN JUEGO). En el remake, la puerta del desierto,
    # la guardia del Centro de Instrucción y el tiro con arco a caballo dependen de SageOfSpirit > Step01 (carpinteros
    # rescatados: GerudoFortress_Common_1d80, GerudoFortress_Level_Exterior_01_a401, MiniGame_HorsebackArchery_8380), no de la
    # tarjeta (solo GerudoFortress_Common_35d7 mira IsGet.Item_Token_Gerudo). OoTR solo pide la tarjeta.
    ("Gerudo Fortress", "GF Gate Open"): "is_adult and Gerudo_Membership_Card and can_finish_GerudoFortress",
    ("Gerudo Fortress", "Gerudo Training Ground Lobby"): "is_adult and Gerudo_Membership_Card and can_finish_GerudoFortress",
    ("Gerudo Fortress", "GF HBA 1000 Points"): "Gerudo_Membership_Card and can_finish_GerudoFortress and can_ride_epona and Bow and at_day",
    ("Gerudo Fortress", "GF HBA 1500 Points"): "Gerudo_Membership_Card and can_finish_GerudoFortress and can_ride_epona and Bow and at_day",
    # Tienda de bombchus: Market_Child_Prefab_0c76 pide de noche Y Get_StoneOfFire_IsCompleted_Exp (OoTR: solo at_night).
    ("Market Back Alley", "Market Bombchu Shop"): "at_night and 'Defeat King Dodongo'",
    # Tanda 4 (2026-11-10): en el remake la pieza «de la lluvia» la da el minijuego NUEVO de los bichos (MiniGame_FrogTenors
    # InsectRepellent); no sé qué lo abre -> por prudencia la misma regla que el juego de canciones (la más exigente).
    ("Zora River", "ZR Frogs in the Rain"): "is_child and can_play(Zeldas_Lullaby) and can_play(Eponas_Song) and "
        "can_play(Sarias_Song) and can_play(Suns_Song) and can_play(Song_of_Time) and can_play(Song_of_Storms)",
    # 2026-11-11 (flujos.piedras_huida, PROBADO en juego): la huida de Zelda (y con ella el foso: Ocarina del Tiempo y Canción del
    # Tiempo) sale cuando Impa te despide (DoorOfTime_SendOff) y ya tienes las 3 piedras: hay que haber estado en el jardín de
    # Zelda de niño. OoTR: is_child and has_all_stones.
    ("Hyrule Field", "HF Ocarina of Time Item"): "is_child and has_all_stones and at('HC Garden', is_child)",
    ("Hyrule Field", "Song from Ocarina of Time"): "is_child and has_all_stones and at('HC Garden', is_child)",
    # 2026-11-12: OoTR pide las notas de la ocarina como objetos (Ocarina_A_Button...: opción de barajar notas, que aquí no
    # existe) -> nadie las daba y el juego de memoria salía inalcanzable siempre (tracker de la usuaria). En el remake es la
    # «sesión» de los Skull Kid (Npc_SkullKid_Child_02: 6 notas = rupia azul, 8 = roja, más = el premio barajado, una vez).
    ("Lost Woods", "LW Ocarina Memory Game"): "is_child and Ocarina",
    # 2026-11-13 (leído en los ficheros + partida de la usuaria): el Sheik del Preludio lo llama Logic/Market_Adult_Prefab_edc2
    # = jugador en la zona Area_4729 (Market_Adult_Static, junto a Sheik) Y SageOfForest_IsCompleted_Exp (Step_SageOfForest =
    # Complete). NO basta el Medallón del Bosque: con el medallón barajado de otro sitio y el Bosque sin hacer
    # (SageOfForest=Step02) no sale nada (probado por la usuaria). OoTR: Forest_Medallion and is_adult.
    ("Beyond Door of Time", "Sheik at Temple"): "is_adult and 'Defeat Phantom Ganon'",
    # 2026-11-13 (auditoría «nunca atrapado», aprobado por la usuaria): el final del remake pide más que las flechas de luz.
    # Ganondorf: «use the Hookshot on the climbing wall» (Nintendo Life). Huida (CrumblingGanonCastle): «equip the Longshot and
    # hook onto the wheel-shaped target» (Apocanow; Banc: Obj_CrumblingGanonCastle_HookShotTarget_A_01) + 3 muros de escombros
    # (Obj_CrumblingGanonCastle_CrackWall_A_01; martillo, ⚠️ bombas sin comprobar). Ganon sin Espada Maestra: «Megaton Hammer or
    # Biggoron Sword» (NL, Apocanow): el martillo ya lo cubre. OoTR: can_use(Light_Arrows). SIN PROBAR EN JUEGO.
    # --- Auditoría «nunca atrapado» 2026-11-13 (informes en Cuaderno/Trampas/; aprobado por la usuaria: «sin regalar nada») ---
    # Jabu sala del bumerán (R9): la puerta de vuelta y el cofre abren al matar 4 Stingers (Room_09_32ab); el bumerán no les hace
    # daño (Life/DamageParameters/Enemy_Stinger: Boomerang 0).
    ("Jabu Jabus Belly Main", "Jabu Jabus Belly Boomerang Chest"): "can_child_damage",
    # Fondo del Pozo: se cae al sótano por agujeros invisibles y la salida pide las rupias plateadas, una tras rocas de explosivos
    # (guías R, G8, QD + auditoría ninio). OoTR: is_child and (can_child_attack or Nuts).
    ("Bottom of the Well", "Bottom of the Well Main Area"): "is_child and (can_child_attack or Nuts) and has_explosives",
    # Tumba real: la 1.ª sala cierra sus 2 puertas hasta matar 4 Keese (RoyalFamilyTomb_Common_eea8 #9/#10). OoTR: solo la Nana.
    ("Graveyard", "Graveyard Royal Familys Tomb"): "can_play(Zeldas_Lullaby) and (is_adult or can_child_damage)",
    # Carrera de Dampé: al ganar, la reja de la meta se cierra (UnderTheGrave_Prefab_6971 #7) y en el remake la salida al molino
    # pide gancho (se quitó el bloque de la Canción del Tiempo; ZW). OoTR: is_adult.
    ("Graveyard", "Graveyard Dampes Grave"): "is_adult and Progressive_Hookshot",
    # Templo de las Sombras, sala de la Mano Muerta (la de las botas): el pasillo 26 se hunde al cruzarlo y para volver hacen falta
    # las botas levitadoras (…B1F_B_Prefab_e203). Decisión de la usuaria: solo lógica (el suelo no se toca).
    ("Shadow Temple Beginning", "Shadow Temple Hover Boots Chest"): "Hover_Boots",
    # Barca de las Sombras: un solo sentido (TG «Get off the ship before it sinks»; Beyond Boat sin vuelta). Subir pide poder acabar
    # el templo: cruzar (arco o espantapájaros lejano), la torre (explosivos o martillo; NL bomba, G8 martillo), botas levitadoras,
    # Lente y vencer a Bongo. Las llaves no: con «llaves: fuera» la mazmorra ya pide todas, y dentro se consiguen después.
    ("Shadow Temple Boat", "Shadow Temple Beyond Boat"): "can_play(Zeldas_Lullaby) and (Bow or can_use(Distant_Scarecrow)) and "
        "(has_explosives or can_use(Megaton_Hammer)) and Hover_Boots and (can_use(Lens_of_Truth) or logic_lens_bongo) and can_use(Bow)",
    # Bongo Bongo: el gancho no le hace daño (DamageParameters); NL pide arco. OoTR aceptaba gancho o tirachinas.
    ("Bongo Bongo Boss Room", "Defeat Bongo Bongo"): "(Kokiri_Sword or is_adult) and can_use(Bow) and (can_use(Lens_of_Truth) or logic_lens_bongo)",
    # Guanteletes de plata: de niño hay que vencer al Nudillo de Hierro (sala 11 se cierra; NL Spirit); espada Kokiri o palos.
    ("Spirit Temple Central Chamber", "Spirit Temple Silver Gauntlets Chest"): "((Small_Key_Spirit_Temple, 5) or (has_explosives and Longshot and (Small_Key_Spirit_Temple, 3))) and (is_adult or Kokiri_Sword or Sticks)",
    # Réquiem y Bolero: de niño no se vuelve del Coloso ni del Cráter a pie (auditoría exterior T3/T4); de adulto, del Cráter solo con
    # gancho o botas levitadoras. Solo cuentan si hay otra canción de viaje segura (Minueto, Serenata, Nocturno, Preludio).
    ("Root Exits", "Requiem of Spirit Warp"): "can_play(Requiem_of_Spirit) and can_leave_forest and (is_adult or can_play(Minuet_of_Forest) or "
        "can_play(Serenade_of_Water) or can_play(Nocturne_of_Shadow) or can_play(Prelude_of_Light))",
    ("Root Exits", "Bolero of Fire Warp"): "can_play(Bolero_of_Fire) and can_leave_forest and ((is_adult and (Hookshot or Hover_Boots)) or "
        "can_play(Minuet_of_Forest) or can_play(Serenade_of_Water) or can_play(Nocturne_of_Shadow) or can_play(Prelude_of_Light))",
    # (Darunia 2026-11-13: la regla «Cueva de los Dodongos solo tras el baile» se quitó: rompía las semillas ya generadas y el tracker
    #  de su run; va junto con la roca física en una fase aparte. El regalo ya no caduca: flujos.darunia_regalo.)
    ("Ganondorf Boss Room", "Ganon"): "can_use(Light_Arrows) and can_use(Longshot) and can_use(Megaton_Hammer)",
}

def load_location_table():
    """Lee LocationList.py con ast (sin ejecutarlo). Devuelve {nombre: dict}."""
    src = open(os.path.join(REF, "LocationList.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    table = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) == 2 and isinstance(node.elts[0], ast.Constant) \
                and isinstance(node.elts[0].value, str) and isinstance(node.elts[1], ast.Tuple) \
                and len(node.elts[1].elts) == 6:
            name = node.elts[0].value
            vals = []
            for i, e in enumerate(node.elts[1].elts):
                try:
                    vals.append(ast.literal_eval(e))
                except ValueError:
                    vals.append(None)       # p.ej. shop_address(0, 0): no nos hace falta
            typ, scene, default, addresses, vanilla, cats = vals
            if not isinstance(typ, str):
                continue
            table[name] = {"type": typ, "scene": scene, "default": default,
                           "vanilla": vanilla, "categories": cats}
    return table

if __name__ == "__main__":
    h = load_helpers(); w = load_world(); t = load_location_table()
    print("helpers", len(h), "| regiones", len(w), "| ubicaciones", len(t))
    import collections
    print(collections.Counter(v["type"] for v in t.values()).most_common())
