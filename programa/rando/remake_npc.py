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
    # 2026-11-12: en Switch 2 la hada del CASTILLO es Dm_FairyFountain_Power (magia) y la de la CIMA de la Montaña es
    # Dm_FairyFountain_Din (Fuego de Din, la primera: FirstTime, reto Meet_GreatFairy GoToTopOfMountain -> GoToHyruleCastle).
    # Pruebas: MapIconFacilityAnchor de HyruleCastle_Dynamic abre con HavePlayedEvent.Dm_FairyFountain_Power y el de
    # DeathMountainTrail con ...Din. Antes estaban al revés (al OoT de N64).
    ("Dm_FairyFountain_Din", "ActorName", "Item_DinFire", "DMT Great Fairy Reward", "regalo"),
    ("Dm_FairyFountain_Frore", "ActorName", "Item_FaroreWind", "ZF Great Fairy Reward", "regalo"),
    ("Dm_FairyFountain_Nayru", "ActorName", "Item_NayruLove", "Colossus Great Fairy Reward", "regalo"),
    ("Dm_FairyFountain_Power", "ActorName", "Item_FairyBless_MP", "HC Great Fairy Reward", "regalo"),
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

# Recompensas de mazmorra (piedras y medallones): las da la escena tras el jefe (o Rauru). Lista APARTE de NPC para no
# mover los ids de los códigos ya generados (export_web las añade al final). Opción "recompensas" (sin probar en juego).
RECOMPENSAS = [
    ("Dm_Kokiri_0130", "ActorName", "Item_Stone_Forest", "Queen Gohma", "recompensa"),
    ("Dm_DeathMtTrail_0025", "ActorName", "Item_Stone_Fire", "King Dodongo", "recompensa"),
    ("Dm_ZoraFountain_0030", "ActorName", "Item_Stone_Water", "Barinade", "recompensa"),
    ("Dm_Awake_Forest_Get", "ActorName", "Item_Medal_Forest", "Phantom Ganon", "recompensa"),
    ("Dm_Awake_Fire_Get", "ActorName", "Item_Medal_Fire", "Volvagia", "recompensa"),
    ("Dm_Awake_Water_Get", "ActorName", "Item_Medal_Water", "Morpha", "recompensa"),
    ("Dm_Awake_Shadow_Get", "ActorName", "Item_Medal_Shadow", "Bongo Bongo", "recompensa"),
    ("Dm_Awake_Spirit_Get", "ActorName", "Item_Medal_Spirit", "Twinrova", "recompensa"),
    ("Dm_SageRoom_0005", "ActorName", "Item_Medal_Light", "ToT Reward from Rauru", "recompensa"),
]
# Con recompensas barajadas, el juego puede seguir abriendo la Puerta del Tiempo o el puente por los JEFES vencidos (pasos
# de historia de esas escenas) y no por el objeto: la lógica pide las dos cosas (logic.GATE).
RECOMPENSA_JEFE = {"Kokiri Emerald": "Defeat Queen Gohma", "Goron Ruby": "Defeat King Dodongo", "Zora Sapphire": "Defeat Barinade",
                   "Forest Medallion": "Defeat Phantom Ganon", "Fire Medallion": "Defeat Volvagia", "Water Medallion": "Defeat Morpha",
                   "Shadow Medallion": "Defeat Bongo Bongo", "Spirit Medallion": "Defeat Twinrova"}

# Regalos añadidos el 2026-11-10 (tandas 1-3, petición de la usuaria «no está todo randomizado»). Lista APARTE y al FINAL
# de los ids (export_web) para no mover los códigos ya generados. Mismo mecanismo que NPC: se cambia el parámetro del flujo.
# Comprobado en el romfs original (investigacion: evfl_parametros_objetos.json + análisis de puertas 2026-11-10): todos dan el
# objeto con Dm_SY_GetInEvent / NpcCommon_HandOver / TakenReward (como los de NPC); las únicas condiciones delante son sus
# propias marcas de «ya lo diste». SIN PROBAR EN JUEGO.
NPC_EXTRA = [
    # tanda 1
    ("SageOfFire", "ActorName", "Obj_Armor_Goron", "GC Rolling Goron as Adult", "regalo"),         # Event18 GetInEvent_NotTurn
    ("SageOfWater", "ActorName", "Obj_Armor_Zora", "ZD King Zora Thawed", "regalo"),               # Event242 GetInEvent_NotTurn_PosCamera
    ("MiniGame_Diving", "ActorName", "Item_Scale_Silver", "ZD Diving Minigame", "regalo"),         # Event21 GetInEvent_NotTurn_NotNpc
    ("Npc_Goron_006_Child", "ReveiveItem", "Item_BombBag_Medium", "GC Rolling Goron as Child", "regalo"),   # + Large (VALORES_EXTRA)
    # tanda 2
    ("MiniGame_HitTarget", "ReveiveItem", "Item_BulletBag_Medium", "Market Shooting Gallery Reward", "regalo"),
    ("MiniGame_HitTarget", "ReveiveItem", "Item_Quiver_Medium", "Kak Shooting Gallery Reward", "regalo"),
    ("Minigame_HorsebackArchery", "ActorName", "Obj_Heart_Piece", "GF HBA 1000 Points", "regalo"),
    ("Minigame_HorsebackArchery", "ActorName", "Item_Quiver_Large", "GF HBA 1500 Points", "regalo"),
    ("MiniGame_BombchuBowling", "ReveiveItem", "Item_BombBag_Large", "Market Bombchu Bowling First Prize", "regalo"),
    ("GatheringTokenGold", "TakenRewardActor", "Item_Wallet_Medium", "Kak 10 Gold Skulltula Reward", "regalo"),
    ("GatheringTokenGold", "TakenRewardActor", "Item_Wallet_Large", "Kak 30 Gold Skulltula Reward", "regalo"),
    ("Npc_SkullKid_Child", "ActorName", "Obj_Heart_Piece", "LW Skull Kid", "regalo"),              # toca la canción de Saria
    ("Npc_SkullKid_Child_02", "ActorName", "Obj_Heart_Piece", "LW Ocarina Memory Game", "regalo"), # «sesión» (⚠️ suposición: el de los tocones)
    ("LostWood_ScrubForestStageElder_SkullMaskFirst", "ActorName", "Item_StickBag_Medium", "Deku Theater Skull Mask", "regalo"),
    ("LostWood_ScrubForestStageElder_TrueMaskFirst", "ActorName", "Item_NutBag_Medium", "Deku Theater Mask of Truth", "regalo"),
    ("Npc_Hylia_001_Adult", "ActorName", "Obj_Heart_Piece", "Kak Man on Roof", "regalo"),         # «Has conseguido subir...»
    # tanda 3: solo la recompensa final de Biggoron (la cadena de intercambio sigue la de siempre)
    ("Npc_Goron_Biggoron_Adult", "ActorName", "Item_Sword_Biggoron", "DMT Biggoron", "regalo"),   # GetInEventItemSwordBiggoron ⚠️
    # tanda 4 (2026-11-10, como OoTR/SoH/3DR). Clave "Clave#n,m": solo esas apariciones (por orden en el fichero ORIGINAL)
    # del parámetro con ese valor, porque el mismo valor da premios distintos en el mismo flujo.
    ("MiniGame_FrogTenors", "ActorName#2", "Obj_Heart_Piece", "ZR Frogs Ocarina Game", "regalo"),   # Event384 GetInEvent (canciones)
    ("MiniGame_FrogTenors", "ActorName#0,1", "Obj_Heart_Piece", "ZR Frogs in the Rain", "regalo"),  # minijuego de los bichos (InsectRepellent, 1.ª vez y reintento) ⚠️
    ("Npc_Hylia_Dampe_001", "ActorName#1", "Obj_Heart_Piece", "Graveyard Dampe Gravedigging Tour", "regalo"),  # Event628 GetInEvent_..._Dampe (la pieza del hoyo se borra)
    ("Npc_Goron_Medigoron_Adult", "ActorName", "Shop_Sword_Giant", "GC Medigoron", "regalo"),   # SimpleShop: vende Shop_RB_<objeto> (VENDE)
    ("Npc_Hylia_049_Adult", "ReveiveItem", "Item_PocketEgg", "Kak Anju as Adult", "regalo"),   # inicio de la cadena: el huevo va al reparto
    # tanda 5 (2026-11-10, como OoTR «HF Ocarina of Time Item»): la escena del foso da la ocarina con el mismo mecanismo que
    # Saria (Event70 AddOrRemovePouchContent Actor + Event229 DisplayGetByActorName ActorName + Event280 TargetID; patch2
    # cambia las tres). La Canción del Tiempo (Event4) sigue siendo su propia ubicación. SIN PROBAR EN JUEGO.
    ("Dm_MelodyGet_Time", "ActorName", "Item_Ocarina_Time", "HF Ocarina of Time Item", "regalo"),
    # tanda 6 (2026-11-11, usuaria: «barajar el huevo sí»; como OoTR «HC Malon Egg»). Malon niña, Goto_HyruleCastle Event35
    # (Dm_SY_GetInEvent ActorName). «#0»: SOLO esa aparición; la eclosión (EggHatch Event55 AddOrRemovePouchContent Actor=Item_WeirdEgg)
    # no se toca. La eclosión va con el reto Goto_HyruleCastle en Step03, que pone la propia charla de Malon (Event46) sea cual
    # sea el regalo: con el huevo de otro sitio, eclosiona tras hablar con Malon. SIN PROBAR EN JUEGO.
    ("Goto_HyruleCastle", "ActorName#0", "Item_WeirdEgg", "HC Malon Egg", "regalo"),
]
N_EXTRA_ANTES_OCARINA = 22   # export_web: los objetos de las 22 primeras van ordenados; los de después, al final y en orden
# Ubicaciones cuyo objeto original no es el valor del parámetro (Medigoron vende el artículo Shop_Sword_Giant = la Navaja)
VANILLA_REAL = {"Npc_Goron_Medigoron_Adult:ActorName:Shop_Sword_Giant": "Item_Sword_Giant"}
# Ubicaciones que VENDEN (precio en rupias): solo objetos vendibles como artículo fabricado (remake_tienda.vendible) o su original
VENDE = {"Npc_Goron_Medigoron_Adult:ActorName:Shop_Sword_Giant": 200}
# El mismo regalo con otro valor según lo que ya tengas (bolsa mediana/grande): se cambian los dos por el objeto nuevo
# 2026-11-12: regalos añadidos DESPUÉS de core.COLOCADOS (export_web los pone al final; no mueven los códigos anteriores)
NPC_EXTRA2 = [
    # Diana del Deku del Bosque Perdido (Dm_LostWood_0040): Event30 bolsa grande / Event17 enorme (si ya tienes la grande).
    # Solo la rama de la enorme marca LostWood_HitTargetOfDekuScrub_FirstClear -> con el premio barajado patch2 fija Event83 -> Event17
    # (flujos.DIANA_UNA_VEZ) para que no se repita. SIN PROBAR EN JUEGO.
    ("Dm_LostWood_0040", "ActorName", "Item_BulletBag_Medium", "LW Target in Woods", "regalo"),
]
VALORES_EXTRA = {("Dm_LostWood_0040", "Item_BulletBag_Medium"): ["Item_BulletBag_Large"],
                 ("Npc_Goron_006_Child", "Item_BombBag_Medium"): ["Item_BombBag_Large"],
                 ("MiniGame_HitTarget", "Item_BulletBag_Medium"): ["Item_BulletBag_Large"],
                 ("MiniGame_HitTarget", "Item_Quiver_Medium"): ["Item_Quiver_Large"],
                 ("Minigame_HorsebackArchery", "Item_Quiver_Large"): ["Item_Quiver_Medium"],
                 ("MiniGame_BombchuBowling", "Item_BombBag_Large"): ["Item_BombBag_Medium"],
                 ("LostWood_ScrubForestStageElder_SkullMaskFirst", "Item_StickBag_Medium"): ["Item_StickBag_Large"],
                 ("LostWood_ScrubForestStageElder_TrueMaskFirst", "Item_NutBag_Medium"): ["Item_NutBag_Large"]}
# Objetos que solo se dan como regalo (no sabemos si salen bien de un cofre/vasija/tienda): túnicas (actor Obj_Armor_*) y la
# espada de Biggoron (su entrega tiene animación propia).
SOLO_REGALO = {"Obj_Armor_Goron", "Obj_Armor_Zora",   # (Item_Sword_Biggoron QUITADA 2026-11-11: probada en cofre, sale bien)
               "Item_Sword_Giant", "Item_PocketEgg",
               "Item_Ocarina_Time", "Item_WeirdEgg"}   # huevo extraño: sin modelo de cofre comprobado   # (la ocarina de cofre salió sin modelo con la de hadas, NOTAS 2026-11-07)

# objeto del remake -> objeto lógico del OoTR (para los que no están en remake.ITEMS)
NPC_ITEMS = {
    "Item_Melody_ZeldaLullaby": "Zeldas Lullaby", "Item_Melody_EponaSong": "Eponas Song", "Item_Melody_SariaSong": "Sarias Song",
    "Item_Melody_StormSong": "Song of Storms", "Item_Melody_SunSong": "Suns Song", "Item_Melody_TimeSong": "Song of Time",
    "Item_Melody_ForestMinuet": "Minuet of Forest", "Item_Melody_FireBolero": "Bolero of Fire",
    "Item_Melody_WaterSerenade": "Serenade of Water", "Item_Melody_ShadowNocturne": "Nocturne of Shadow",
    "Item_Melody_SpiritRequiem": "Requiem of Spirit", "Item_Melody_LightPrelude": "Prelude of Light",
    "Item_Ocarina_Fairy": "Ocarina", "Item_Gauntlet_Goron": "Progressive Strength Upgrade", "Item_ZeldaLetter": "Zeldas Letter",
    "Item_Token_Gerudo": "Gerudo Membership Card", "Item_Arrow_Light": "Light Arrows", "Item_Arrow_Fire": "Fire Arrows", "Item_DinFire": "Dins Fire",
    "Item_FaroreWind": "Farores Wind", "Item_NayruLove": "Nayrus Love", "Item_FairyBless_MP": "Magic Meter", "Item_Bottle_Letter": "Rutos Letter",
    "Item_FairyBless_MPDouble": "Magic Meter", "Item_FairyBless_DefenseDouble": "Double Defense",
    "Item_Scale_Gold": "Progressive Scale", "Item_Bottle": "Bottle", "Item_AgonyStone": "Stone of Agony",
    "Item_BombchuBundle_Large": "Bombchus (20)",
    "Item_Stone_Forest": "Kokiri Emerald", "Item_Stone_Fire": "Goron Ruby", "Item_Stone_Water": "Zora Sapphire",
    "Item_Medal_Forest": "Forest Medallion", "Item_Medal_Fire": "Fire Medallion", "Item_Medal_Water": "Water Medallion",
    "Item_Medal_Shadow": "Shadow Medallion", "Item_Medal_Spirit": "Spirit Medallion", "Item_Medal_Light": "Light Medallion",
    # 2026-11-10 (NPC_EXTRA)
    "Obj_Armor_Goron": "Goron Tunic", "Obj_Armor_Zora": "Zora Tunic", "Item_Scale_Silver": "Progressive Scale",
    "Item_BombBag_Medium": "Bomb Bag", "Item_BombBag_Large": "Bomb Bag", "Item_BulletBag_Medium": "Slingshot",
    "Item_Quiver_Medium": "Bow", "Item_Quiver_Large": "Bow", "Item_Wallet_Medium": "Progressive Wallet",
    "Item_Wallet_Large": "Progressive Wallet", "Item_StickBag_Medium": "Deku Stick Capacity",
    "Item_NutBag_Medium": "Deku Nut Capacity", "Item_Sword_Biggoron": "Biggoron Sword",
    "Item_Sword_Giant": "Giants Knife", "Item_PocketEgg": "Pocket Egg",   # tanda 4
    "Item_WeirdEgg": "Weird Egg",   # tanda 6
    "Item_Ocarina_Time": "Ocarina",   # tanda 5: la 2.ª ocarina del OoTR (puerta stones_oot_sot pide (Ocarina, 2))
}
# no son progresión en la lógica (o solo ayudan): se tratan como útiles, no como clave
NPC_NO_PROGRESO = {"Item_FairyBless_DefenseDouble", "Item_BombchuBundle_Large", "Item_AgonyStone", "Item_StickBag_Medium", "Item_NutBag_Medium"}

NPC_ES = {
    "Song from Impa": "Castillo de Hyrule: canción de Impa", "Song from Malon": "Rancho Lon Lon: canción de Malon",
    "Song from Saria": "Prado Sagrado: canción de Saria", "Song from Windmill": "Kakariko: canción del molino",
    "Song from Royal Familys Tomb": "Cementerio: canción de la tumba real", "Song from Ocarina of Time": "Campo de Hyrule: Ocarina del Tiempo (canción)",
    "Sheik in Forest": "Prado Sagrado: Sheik (minueto)", "Sheik in Crater": "Cráter: Sheik (bolero)",
    "Sheik in Ice Cavern": "Caverna de Hielo: Sheik (serenata)", "Sheik in Kakariko": "Kakariko: Sheik (nocturno)",
    "Sheik at Colossus": "Coloso del Desierto: Sheik (réquiem)", "Sheik at Temple": "Templo del Tiempo: Sheik (preludio)",
    "LW Gift from Saria": "Puente del Bosque Kokiri: regalo de Saria", "GC Darunias Joy": "Ciudad Goron: alegría de Darunia",
    "HC Zeldas Letter": "Castillo de Hyrule: carta de Zelda", "HC Malon Egg": "Castillo de Hyrule: huevo de Malon", "Hideout Gerudo Membership Card": "Fortaleza Gerudo: tarjeta de socio",
    "ToT Light Arrows Cutscene": "Templo del Tiempo: flechas de luz", "HC Great Fairy Reward": "Castillo de Hyrule: Gran Hada",
    "ZF Great Fairy Reward": "Fuente Zora: Gran Hada", "Colossus Great Fairy Reward": "Coloso del Desierto: Gran Hada",
    "DMT Great Fairy Reward": "Montaña de la Muerte: Gran Hada", "DMC Great Fairy Reward": "Cráter: Gran Hada",
    "OGC Great Fairy Reward": "Fuera del Castillo de Ganon: Gran Hada", "LH Adult Fishing": "Lago Hylia: pesca de adulto",
    "LH Child Fishing": "Lago Hylia: pesca de niño", "Market Bombchu Bowling Second Prize": "Mercado: bolos bombchu (2.º premio)",
    "Kak Anju as Child": "Kakariko: cucos de Anju", "Market Lost Dog": "Mercado: el perro perdido",
    "Kak 20 Gold Skulltula Reward": "Casa de las Skulltulas: 20", "Kak 40 Gold Skulltula Reward": "Casa de las Skulltulas: 40",
    "Kak 50 Gold Skulltula Reward": "Casa de las Skulltulas: 50",
    "Queen Gohma": "Bosque Kokiri: recompensa de Reina Gohma", "King Dodongo": "Montaña de la Muerte: recompensa del Rey Dodongo",
    "Barinade": "Fuente Zora: recompensa de Barinade", "Phantom Ganon": "Cámara de los Sabios: Saria (Ganon Fantasma)",
    "Volvagia": "Cámara de los Sabios: Darunia (Volvagia)", "Morpha": "Cámara de los Sabios: Ruto (Morpha)",
    "Bongo Bongo": "Cámara de los Sabios: Impa (Bongo Bongo)", "Twinrova": "Cámara de los Sabios: Nabooru (Birova)",
    "ToT Reward from Rauru": "Cámara de los Sabios: Rauru",
    "GC Rolling Goron as Adult": "Ciudad Goron: niño goron rodante (adulto)", "ZD King Zora Thawed": "Dominio Zora: Rey Zora descongelado",
    "ZD Diving Minigame": "Dominio Zora: buceo de las rupias", "GC Rolling Goron as Child": "Ciudad Goron: goron rodante (niño)",
    "Market Shooting Gallery Reward": "Mercado: galería de tiro", "Kak Shooting Gallery Reward": "Kakariko: galería de tiro",
    "GF HBA 1000 Points": "Fortaleza Gerudo: arquería a caballo (1000)", "GF HBA 1500 Points": "Fortaleza Gerudo: arquería a caballo (1500)",
    "Market Bombchu Bowling First Prize": "Mercado: bolos bombchu (1.er premio)",
    "Kak 10 Gold Skulltula Reward": "Casa de las Skulltulas: 10", "Kak 30 Gold Skulltula Reward": "Casa de las Skulltulas: 30",
    "LW Skull Kid": "Bosque Perdido: Skull Kid", "LW Ocarina Memory Game": "Bosque Perdido: juego de memoria", "LW Target in Woods": "Bosque Perdido: diana del Deku",
    "Deku Theater Skull Mask": "Bosque Perdido: teatro deku (máscara de calavera)", "Deku Theater Mask of Truth": "Bosque Perdido: teatro deku (máscara de la verdad)",
    "Kak Man on Roof": "Kakariko: hombre del tejado",
    "ZR Frogs Ocarina Game": "Río Zora: ranas (juego de canciones)", "ZR Frogs in the Rain": "Río Zora: ranas (minijuego de los bichos)",
    "Graveyard Dampe Gravedigging Tour": "Cementerio: excavación de Dampé", "GC Medigoron": "Ciudad Goron: Medigoron (venta)",
    "Kak Anju as Adult": "Kakariko: Anju (adulta)", "DMT Biggoron": "Montaña de la Muerte: Biggoron",
    "HF Ocarina of Time Item": "Campo de Hyrule: Ocarina del Tiempo (foso)",
}
NPC_ITEM_ES = {
    "Item_Melody_ZeldaLullaby": "Nana de Zelda", "Item_Melody_EponaSong": "Canción de Epona", "Item_Melody_SariaSong": "Canción de Saria",
    "Item_Melody_StormSong": "Canción de la tormenta", "Item_Melody_SunSong": "Canción del Sol", "Item_Melody_TimeSong": "Canción del Tiempo",
    "Item_Melody_ForestMinuet": "Minueto del bosque", "Item_Melody_FireBolero": "Bolero del fuego",
    "Item_Melody_WaterSerenade": "Serenata del agua", "Item_Melody_ShadowNocturne": "Nocturno de la sombra",
    "Item_Melody_SpiritRequiem": "Réquiem del espíritu", "Item_Melody_LightPrelude": "Preludio de la luz",
    "Item_Ocarina_Fairy": "Ocarina de las hadas", "Item_Gauntlet_Goron": "Brazalete Goron", "Item_ZeldaLetter": "Carta de Zelda",
    "Item_Token_Gerudo": "Tarjeta Gerudo", "Item_Arrow_Light": "Flechas de luz", "Item_Arrow_Fire": "Flechas de fuego", "Item_DinFire": "Fuego de Din",
    "Item_FaroreWind": "Viento de Farore", "Item_NayruLove": "Amor de Nayru", "Item_FairyBless_MP": "Magia", "Item_Bottle_Letter": "Carta de Ruto",
    "Item_FairyBless_MPDouble": "Magia doble", "Item_FairyBless_DefenseDouble": "Defensa doble", "Item_Scale_Gold": "Escama de oro",
    "Item_Bottle": "Botella", "Item_AgonyStone": "Piedra de la Agonía", "Item_BombchuBundle_Large": "Bombchus (20)",
    "Obj_Rupee_Green": "Rupia verde", "Obj_Rupee_Blue": "Rupia azul", "Obj_Rupee_Red": "Rupia roja",
    "Obj_Rupee_Purple": "Rupia morada", "Obj_Rupee_Gold": "Rupia dorada",
    "Item_Stone_Forest": "Esmeralda Kokiri", "Item_Stone_Fire": "Rubí Goron", "Item_Stone_Water": "Zafiro Zora",
    "Item_Medal_Forest": "Medallón del Bosque", "Item_Medal_Fire": "Medallón del Fuego", "Item_Medal_Water": "Medallón del Agua",
    "Item_Medal_Shadow": "Medallón de las Sombras", "Item_Medal_Spirit": "Medallón del Espíritu", "Item_Medal_Light": "Medallón de la Luz",
    "Obj_Armor_Goron": "Túnica Goron", "Obj_Armor_Zora": "Túnica Zora", "Item_Scale_Silver": "Escama de plata",
    "Item_BombBag_Medium": "Bolsa de bombas grande", "Item_BombBag_Large": "Bolsa de bombas enorme",
    "Item_BulletBag_Medium": "Bolsa de semillas grande", "Item_Quiver_Medium": "Carcaj grande", "Item_Quiver_Large": "Carcaj enorme",
    "Item_Wallet_Medium": "Bolsa de adulto", "Item_Wallet_Large": "Bolsa gigante", "Item_StickBag_Medium": "Más palos Deku",
    "Item_NutBag_Medium": "Más nueces Deku", "Item_Sword_Biggoron": "Espada de Biggoron",
    "Item_Ocarina_Time": "Ocarina del Tiempo",
}

def npc_id(flow, key, value):
    return f"{flow}:{key}:{value}"

def para_regalo(item):
    """Nombre de actor válido para que lo dé un personaje (los de cofre llevan prefijo TBox_)."""
    if item.startswith("TBox_Rupee_"): return "Obj_Rupee_" + item.split("_")[-1]
    if item.startswith(("TBox_", "Tbox_")): return "Obj_Rupee_Red"     # munición de cofre: no tiene versión de regalo
    if item.startswith("Obj_Rupee_") or item == "Obj_Heart_Piece" or item in SOLO_REGALO: return item
    if item.startswith(("Obj_", "Animal_")): return "Obj_Rupee_Green"   # relleno de suelo (corazón, bicho, hada…)
    return item
