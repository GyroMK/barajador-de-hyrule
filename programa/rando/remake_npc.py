"""Regalos de personajes, minijuegos, Grandes Hadas y canciones del remake, y su ubicación del OoTR.

Cada regalo es un parámetro de texto dentro de un flujo de eventos (Event/EventFlow/<flujo>.bfevfl.zs):
  (flujo, clave del parámetro, objeto original)  ->  ubicación del OoTR
Claves: ActorName (escenas Dm_*), ReveiveItem/ReceiveItem (minijuegos y personajes),
TakenRewardActor (casa de las Skulltulas).
'grupo' decide con qué se puede mezclar: 'cancion' solo entre canciones; 'regalo' con todo lo demás.
"""
NPC = [
    # --- canciones (solo se mezclan entre ellas) ---
    ("Dm_MelodyGet_Zelda", "ActorName", "Item_Melody_ZeldaLullaby", "Song from Impa", "cancion"),
    ("Dm_MelodyGet_Epona", "ActorName", "Item_Melody_EponaSong", "Song from Malon", "cancion"),
    ("Dm_MelodyGet_Saria", "ActorName", "Item_Melody_SariaSong", "Song from Saria", "cancion"),
    ("Dm_MelodyGet_Storm", "ActorName", "Item_Melody_StormSong", "Song from Windmill", "cancion"),
    ("Dm_MelodyGet_Sun_03", "ActorName", "Item_Melody_SunSong", "Song from Royal Familys Tomb", "cancion"),
    ("Dm_MelodyGet_Time", "ActorName", "Item_Melody_TimeSong", "Song from Ocarina of Time", "cancion"),
    ("Dm_MelodyGet_Forest", "ActorName", "Item_Melody_ForestMinuet", "Sheik in Forest", "cancion"),
    ("Dm_MelodyGet_Fire", "ActorName", "Item_Melody_FireBolero", "Sheik in Crater", "cancion"),
    ("Dm_MelodyGet_Water", "ActorName", "Item_Melody_WaterSerenade", "Sheik in Ice Cavern", "cancion"),
    ("Dm_MelodyGet_Shadow", "ActorName", "Item_Melody_ShadowNocturne", "Sheik in Kakariko", "cancion"),
    ("Dm_MelodyGet_Spilit", "ActorName", "Item_Melody_SpiritRequiem", "Sheik at Colossus", "cancion"),
    ("Dm_MelodyGet_Shine", "ActorName", "Item_Melody_LightPrelude", "Sheik at Temple", "cancion"),
    # --- regalos de historia ---
    ("Dm_Kokiri_0155", "ActorName", "Item_Ocarina_Fairy", "LW Gift from Saria", "regalo"),
    ("Dm_Goron_0030", "ActorName", "Item_Gauntlet_Goron", "GC Darunias Joy", "regalo"),
    ("Dm_HrlCastle_0050", "ActorName", "Item_ZeldaLetter", "HC Zeldas Letter", "regalo"),
    ("Dm_Gerudo_0025", "ActorName", "Item_Token_Gerudo", "Hideout Gerudo Membership Card", "regalo"),
    ("Dm_TimeTemple_0130", "ActorName", "Item_Arrow_Light", "ToT Light Arrows Cutscene", "regalo"),
    # --- Grandes Hadas ---
    ("Dm_FairyFountain_Din", "ActorName", "Item_DinFire", "HC Great Fairy Reward", "regalo"),
    ("Dm_FairyFountain_Frore", "ActorName", "Item_FaroreWind", "ZF Great Fairy Reward", "regalo"),
    ("Dm_FairyFountain_Nayru", "ActorName", "Item_NayruLove", "Colossus Great Fairy Reward", "regalo"),
    ("Dm_FairyFountain_Power", "ActorName", "Item_FairyBless_MP", "DMT Great Fairy Reward", "regalo"),
    ("Dm_FairyFountain_Wisdom", "ActorName", "Item_FairyBless_MPDouble", "DMC Great Fairy Reward", "regalo"),
    ("Dm_FairyFountain_Courage", "ActorName", "Item_FairyBless_DefenseDouble", "OGC Great Fairy Reward", "regalo"),
    # --- minijuegos y personajes ---
    ("MiniGame_Fishing", "ReveiveItem", "Item_Scale_Gold", "LH Adult Fishing", "regalo"),
    ("MiniGame_Fishing", "ReveiveItem", "Obj_Heart_Piece", "LH Child Fishing", "regalo"),
    ("MiniGame_BombchuBowling", "ReveiveItem", "Obj_Heart_Piece", "Market Bombchu Bowling Second Prize", "regalo"),
    ("Minigame_CatchCucco", "ReveiveItem", "Item_Bottle", "Kak Anju as Child", "regalo"),
    ("SubEvent_FindRichard", "ReveiveItem", "Obj_Heart_Piece", "Market Lost Dog", "regalo"),
    # --- casa de las Skulltulas ---
    ("GatheringTokenGold", "TakenRewardActor", "Item_AgonyStone", "Kak 20 Gold Skulltula Reward", "regalo"),
    ("GatheringTokenGold", "TakenRewardActor", "Item_BombchuBundle_Large", "Kak 40 Gold Skulltula Reward", "regalo"),
    ("GatheringTokenGold", "TakenRewardActor", "Obj_Heart_Piece", "Kak 50 Gold Skulltula Reward", "regalo"),
]

# objeto del remake -> objeto lógico del OoTR (para los que no están en remake.ITEMS)
NPC_ITEMS = {
    "Item_Melody_ZeldaLullaby": "Zeldas Lullaby", "Item_Melody_EponaSong": "Eponas Song", "Item_Melody_SariaSong": "Sarias Song",
    "Item_Melody_StormSong": "Song of Storms", "Item_Melody_SunSong": "Suns Song", "Item_Melody_TimeSong": "Song of Time",
    "Item_Melody_ForestMinuet": "Minuet of Forest", "Item_Melody_FireBolero": "Bolero of Fire",
    "Item_Melody_WaterSerenade": "Serenade of Water", "Item_Melody_ShadowNocturne": "Nocturne of Shadow",
    "Item_Melody_SpiritRequiem": "Requiem of Spirit", "Item_Melody_LightPrelude": "Prelude of Light",
    "Item_Ocarina_Fairy": "Ocarina", "Item_Gauntlet_Goron": "Progressive Strength Upgrade", "Item_ZeldaLetter": "Zeldas Letter",
    "Item_Token_Gerudo": "Gerudo Membership Card", "Item_Arrow_Light": "Light Arrows", "Item_DinFire": "Dins Fire",
    "Item_FaroreWind": "Farores Wind", "Item_NayruLove": "Nayrus Love", "Item_FairyBless_MP": "Magic Meter",
    "Item_FairyBless_MPDouble": "Magic Meter", "Item_FairyBless_DefenseDouble": "Double Defense",
    "Item_Scale_Gold": "Progressive Scale", "Item_Bottle": "Bottle", "Item_AgonyStone": "Stone of Agony",
    "Item_BombchuBundle_Large": "Bombchus (20)",
}
# no son progresión en la lógica (o solo ayudan): se tratan como útiles, no como clave
NPC_NO_PROGRESO = {"Item_FairyBless_DefenseDouble", "Item_BombchuBundle_Large", "Item_AgonyStone"}

NPC_ES = {
    "Song from Impa": "Castillo de Hyrule: canción de Impa", "Song from Malon": "Rancho Lon Lon: canción de Malon",
    "Song from Saria": "Prado Sagrado: canción de Saria", "Song from Windmill": "Kakariko: canción del molino",
    "Song from Royal Familys Tomb": "Cementerio: canción de la tumba real", "Song from Ocarina of Time": "Campo de Hyrule: Ocarina del Tiempo (canción)",
    "Sheik in Forest": "Prado Sagrado: Sheik (minueto)", "Sheik in Crater": "Cráter: Sheik (bolero)",
    "Sheik in Ice Cavern": "Caverna de Hielo: Sheik (serenata)", "Sheik in Kakariko": "Kakariko: Sheik (nocturno)",
    "Sheik at Colossus": "Coloso del Desierto: Sheik (réquiem)", "Sheik at Temple": "Templo del Tiempo: Sheik (preludio)",
    "LW Gift from Saria": "Puente del Bosque Kokiri: regalo de Saria", "GC Darunias Joy": "Ciudad Goron: alegría de Darunia",
    "HC Zeldas Letter": "Castillo de Hyrule: carta de Zelda", "Hideout Gerudo Membership Card": "Fortaleza Gerudo: tarjeta de socio",
    "ToT Light Arrows Cutscene": "Templo del Tiempo: flechas de luz", "HC Great Fairy Reward": "Castillo de Hyrule: Gran Hada",
    "ZF Great Fairy Reward": "Fuente Zora: Gran Hada", "Colossus Great Fairy Reward": "Coloso del Desierto: Gran Hada",
    "DMT Great Fairy Reward": "Montaña de la Muerte: Gran Hada", "DMC Great Fairy Reward": "Cráter: Gran Hada",
    "OGC Great Fairy Reward": "Fuera del Castillo de Ganon: Gran Hada", "LH Adult Fishing": "Lago Hylia: pesca de adulto",
    "LH Child Fishing": "Lago Hylia: pesca de niño", "Market Bombchu Bowling Second Prize": "Mercado: bolos bombchu (2.º premio)",
    "Kak Anju as Child": "Kakariko: cucos de Anju", "Market Lost Dog": "Mercado: el perro perdido",
    "Kak 20 Gold Skulltula Reward": "Casa de las Skulltulas: 20", "Kak 40 Gold Skulltula Reward": "Casa de las Skulltulas: 40",
    "Kak 50 Gold Skulltula Reward": "Casa de las Skulltulas: 50",
}
NPC_ITEM_ES = {
    "Item_Melody_ZeldaLullaby": "Nana de Zelda", "Item_Melody_EponaSong": "Canción de Epona", "Item_Melody_SariaSong": "Canción de Saria",
    "Item_Melody_StormSong": "Canción de la tormenta", "Item_Melody_SunSong": "Canción del Sol", "Item_Melody_TimeSong": "Canción del Tiempo",
    "Item_Melody_ForestMinuet": "Minueto del bosque", "Item_Melody_FireBolero": "Bolero del fuego",
    "Item_Melody_WaterSerenade": "Serenata del agua", "Item_Melody_ShadowNocturne": "Nocturno de la sombra",
    "Item_Melody_SpiritRequiem": "Réquiem del espíritu", "Item_Melody_LightPrelude": "Preludio de la luz",
    "Item_Ocarina_Fairy": "Ocarina de las hadas", "Item_Gauntlet_Goron": "Brazalete Goron", "Item_ZeldaLetter": "Carta de Zelda",
    "Item_Token_Gerudo": "Tarjeta Gerudo", "Item_Arrow_Light": "Flechas de luz", "Item_DinFire": "Fuego de Din",
    "Item_FaroreWind": "Viento de Farore", "Item_NayruLove": "Amor de Nayru", "Item_FairyBless_MP": "Magia",
    "Item_FairyBless_MPDouble": "Magia doble", "Item_FairyBless_DefenseDouble": "Defensa doble", "Item_Scale_Gold": "Escama de oro",
    "Item_Bottle": "Botella", "Item_AgonyStone": "Piedra de la Agonía", "Item_BombchuBundle_Large": "Bombchus (20)",
    "Obj_Rupee_Green": "Rupia verde", "Obj_Rupee_Blue": "Rupia azul", "Obj_Rupee_Red": "Rupia roja",
    "Obj_Rupee_Purple": "Rupia morada", "Obj_Rupee_Gold": "Rupia dorada",
}

def npc_id(flow, key, value):
    return f"{flow}:{key}:{value}"

def para_regalo(item):
    """Nombre de actor válido para que lo dé un personaje (los de cofre llevan prefijo TBox_)."""
    if item.startswith("TBox_Rupee_"): return "Obj_Rupee_" + item.split("_")[-1]
    if item.startswith(("TBox_", "Tbox_")): return "Obj_Rupee_Red"     # munición de cofre: no tiene versión de regalo
    if item.startswith("Obj_Rupee_") or item == "Obj_Heart_Piece": return item
    if item.startswith(("Obj_", "Animal_")): return "Obj_Rupee_Green"   # relleno de suelo (corazón, bicho, hada…)
    return item
