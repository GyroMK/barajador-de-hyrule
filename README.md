# Barajador de Hyrule

*Versión en español más abajo.*

A randomizer for the Nintendo Switch 2 *Ocarina of Time*: it takes the game's items (chests, gifts, songs, shops…) and moves them around. Every playthrough is different.

**Built for the remake, not copied from the N64 one.** On Switch 2 you can't save and warp back to a dungeon entrance, so a randomizer using N64 logic can lock you in. This one won't:

- **You never get stuck.** All 447 rooms of the 12 dungeons and the overworld were checked: where a room locks and needs an item to leave, the way back stays open or the logic never sends you there without it.
- **Room-by-room logic (experimental):** the tracker shows what you can get inside each dungeon with what you carry and how many keys you hold.
- **Remake fixes:** the shared trade-item slot (the Pocket Egg no longer hides the Cucco), the Mask Shop even if Kakariko's gate opens from the mountain, Darunia's gift that never expires, "if you already have the shield" chests that give their item.
- **4 difficulty levels** (Easy, Normal, Hard, Very hard), a web tracker with logic, 9 languages.

Version 0.5.0-beta. It's a beta: you can play it start to finish, but some things haven't been tested by playing yet. The table below shows what has and hasn't.

The web page can be switched to English (it comes in ten languages). Hints and the spoiler log come in Spanish and English.

## What you need

- Your copy of the game as a .nup, with the 1.1.1 update (update v131072, ID 0400486024DEC000).
- An emulator that loads mods on top of .nup games, such as Lichii (change #203 or newer).
- Python 3.14, free at python.org. On Windows, tick "Add python.exe to PATH" when installing. Python 3.10 or newer also works if you run `python -m pip install zstandard`.

No programming needed.

## How to use it

1. Open `Barajador de Hyrule.html` in your browser, choose what to shuffle and press **Generate**.
2. Press **Semilla .json** to save the seed, or **Copiar código** to copy it as text.
3. Close the emulator.
   - Windows: drag the .json onto `seed.bat`, or open it and paste the code.
   - Linux or Mac: run `seed.sh` and drag the .json into the terminal, or paste the code.

   It doesn't matter which folder the program is in. The first time, it asks where your .nup and your emulator's mod folder are. You can drag them into the window instead of typing the path.
4. Start a new game. The game has a single save (one manual save plus rotating autosaves), so a new game overwrites yours: back up the emulator's save folder first if you want to keep it. If you get stuck, `spoiler.txt` says where everything went.

To go back to the normal game, delete the "Barajador de Hyrule" folder from the mod folder.

## Quick answers

**Can every seed be finished?** Yes. Before applying a seed, the program checks that the end can be reached with what was placed. If not, it won't apply it.

**Can I skip cutscenes?** Yes. The web page lets you choose which cutscenes and texts to remove. Bosses keep their entrance and name card.

**What if my save breaks?** Save manually before anything risky: if it goes wrong, load that save (or an earlier autosave). If something goes wrong, open an issue with the seed code, where you were and a screenshot.

## What's been tested

Each option is split into small pieces. A piece tested by playing counts fully; one that works like something already tested counts half; a new untested one counts zero. The percentage comes from that. The web page shows the same number next to each option; click it for the details.

| Option | Tested | Still to test |
|---|---|---|
| Overworld and dungeon chests | 100 % | — |
| Character gifts | 70 % | Windmill with Song of Storms obtained earlier; Lake fire arrows (shoot the sun) shuffled; Jabu-Jabu compass shuffled (Ruto's room chest); Dodongo's Cavern Lizalfos always present (entering from the other door no longer locks you in); Logic never sends you to dead ends: boss rooms need what beats the boss, Shadow boat, Well basement (bombs), Requiem and Bolero only with another warp song, royal tomb and Dampé's race; Chests with an «if you already have X» substitute give the shuffled item; Darunia's gift also after Dodongo's Cavern; Biggoron (own animation); Two gifts with the same item in one flow |
| Skulltula House rewards | 100 % | — |
| Songs | 75 % | — |
| Songs mixed with everything | 75 % | — |
| Maps and compasses | 90 % | — |
| Boss heart containers | 100 % | — |
| Loose heart pieces | 50 % | — |
| Dungeon rewards (stones and medallions) | 95 % | — |
| Pots, rocks, grass and crates | 75 % | — |
| Shops | 100 % | — |
| Shop prices | 75 % | Random prices |
| Keys outside their dungeon | 100 % | — |
| Room-by-room logic (experimental) | 50 % | Adult temples (Forest, Fire, Water, Shadow, Spirit, Ice); Gerudo Training Ground and Ganon's Castle |
| Kokiri Forest | 75 % | — |
| Kakariko gate | 100 % | — |
| Zora's Fountain | 100 % | — |
| Door of Time | 100 % | — |
| Rainbow bridge | 100 % | — |
| Cutscenes: intro | 100 % | — |
| Cutscenes: arrivals | 65 % | — |
| Cutscenes: Navi | 85 % | — |
| Cutscenes: owl | 100 % | — |
| Cutscenes: bosses | 100 % | — |
| Cutscenes: tutorials | 100 % | — |
| Cutscenes: story | 80 % | Volcano healing after the Fire Temple |
| Cutscenes: area titles | 100 % | — |
| Cutscenes: stops | 100 % | — |
| Cutscenes: gifts | 100 % | — |
| Cutscenes: names | 100 % | — |
| Starting items | 95 % | — |

The logic (what you need to reach each place) comes from the N64 OoT Randomizer, adapted to this remake. Rooms that changed on Switch 2, jumping and sprinting haven't been fully reviewed yet, so the logic may sometimes be stricter than it needs to be.

## Not shuffled (yet)

Gold Skulltula tokens; most pots and crates; Deku Scrub salesmen; individual frog song prizes; cows (they all share one event); trade sequences, except the Pocket Egg and the Weird Egg (they hatch even if someone else gives them to you); entrances. The remake's new chests only hold filler for now.

## Known issues

- Boss entrances, with their name card, stay on purpose. So do a few cutscenes that move you somewhere else (Epona jumping the fence, the Gerudo cell, the Water Temple entrance, the Colossus and the graveyard) and the ending: removing them as they are would leave you in the wrong place.
- A bag or upgrade bought in a shop (or from Medigoron) may not work until you reload your save.
- In Dampé's dig, the heart coming out of the hole is just the animation. You get the shuffled item.
- Some characters still mention their original item when they talk.
- On Switch 2 the Great Fairies of the castle and of Death Mountain's summit are swapped compared to N64. The Barajador names them by their real place and lets you visit them in any order.

## Legal

- No game files are included. The program reads what it needs from your copy and builds a small mod for the emulator.
- It does not bypass DRM, encryption or any other protection. You need a legal dump of your game.
- Fan project, not affiliated with Nintendo. *The Legend of Zelda* and *Ocarina of Time* are trademarks of Nintendo.
- The logic is based on the [OoT Randomizer](https://github.com/OoTRandomizer/OoT-Randomizer) (MIT license). Includes evfl by leoetlino (GPLv2+).

---

# Barajador de Hyrule (español)

Un randomizer para el *Ocarina of Time* de Nintendo Switch 2: coge los objetos del juego (cofres, regalos, canciones, tiendas…) y los cambia de sitio. Cada partida es distinta y nunca sabes qué hay en el siguiente cofre.

**Hecho para el remake, no copiado del de N64.** En Switch 2 no puedes guardar y volver a la entrada de una mazmorra, así que un randomizer que use la lógica de N64 te puede dejar encerrada. Este no:

- **Nunca te quedas encerrada.** Revisadas las 447 salas de las 12 mazmorras y del mundo: donde una sala se cierra y pide un objeto para salir, la puerta de vuelta queda libre o la lógica no te manda sin él.
- **Lógica por salas (experimental):** el tracker te marca lo que puedes coger dentro de cada mazmorra con lo que llevas y con cuántas llaves.
- **Arreglos del propio remake:** el hueco de objetos de intercambio (el huevo de bolsillo ya no tapa al cuco), la tienda de máscaras aunque la puerta de Kakariko se abra por la montaña, el regalo de Darunia que no caduca, cofres de «si ya tienes el escudo…» que dan su objeto.
- **4 niveles de dificultad** (Fácil, Normal, Difícil, Muy difícil), tracker en la web con lógica y 9 idiomas.

Versión 0.5.0-beta. Es una beta: se puede jugar de principio a fin, pero todavía hay cosas que nadie ha probado jugando. Más abajo hay una tabla con lo que está probado y lo que no.


## Qué necesitas

- Tu copia del juego en .nup, con la actualización 1.1.1 (update v131072, ID 0400486024DEC000).
- Un emulador que cargue mods sobre .nup. Yo uso Lichii (cambio #203 o posterior).
- Python 3.14, gratis en python.org. En Windows, al instalarlo marca «Add python.exe to PATH». Si ya tienes Python 3.10 o más nuevo, vale con ejecutar `python -m pip install zstandard`.

No hace falta saber programar.

## Cómo se usa

1. Abre `Barajador de Hyrule.html` en el navegador, elige qué quieres barajar y pulsa **Generar**.
2. Pulsa **Semilla .json** para guardarte la semilla, o **Copiar código** si prefieres pegarla.
3. Cierra el emulador.
   - Windows: arrastra el .json encima de `seed.bat`, o ábrelo y pega el código.
   - Linux o Mac: abre `seed.sh` y arrastra el .json a la terminal, o pega el código.

   Da igual en qué carpeta tengas el programa. La primera vez te pregunta dónde está tu .nup y la carpeta de mods del emulador. Puedes arrastrarlos a la ventana en vez de escribir la ruta.
4. Abre el juego y empieza una partida nueva. El juego tiene una sola partida (un guardado manual y varios autoguardados), así que empezar otra pisa la tuya: si quieres conservarla, copia antes la carpeta de guardado del emulador. Si te atascas, en `spoiler.txt` está dónde ha ido a parar cada cosa.

Para volver al juego normal, borra la carpeta «Barajador de Hyrule» de la carpeta de mods.

## Preguntas rápidas

**¿Siempre se puede terminar?** Sí. Antes de aplicar una semilla, el programa comprueba que se puede llegar al final con lo que hay repartido. Si no, no la aplica.

**¿Me puede tocar algo imposible, como un objeto detrás de una pared que necesita ese mismo objeto?** No, eso es justo lo que comprueba.

**¿Me salto las escenas?** Puedes. En la web eliges qué escenas y textos quitar. Las de los jefes se quedan con su entrada y su nombre.

**¿Y si se me rompe la partida?** Guarda a mano antes de algo arriesgado: si sale mal, cargas ese guardado (o un autoguardado anterior). Si algo falla, abre un *issue* con el código de la semilla, dónde estabas y una captura. Cada fallo que llega se arregla y se apunta.

## Qué está probado

Cada opción se ha partido en piezas pequeñas. Una pieza probada jugando cuenta entera; una que funciona igual que otra ya probada cuenta media; una nueva sin probar no cuenta. El porcentaje sale de ahí. En la web está el mismo número al lado de cada opción, y si lo pulsas ves el detalle.

| Opción | Probado | Falta probar |
|---|---|---|
| Cofres del mundo y de las mazmorras | 100 % | — |
| Regalos de personajes | 70 % | Molino con la Canción de la Tormenta conseguida antes; Flechas de fuego del lago (disparar al sol) barajadas; Brújula de Jabu-Jabu barajada (cofre de la sala de Ruto); Lizalfos de la Cueva de los Dodongos siempre presentes (entrando por la otra puerta ya no te quedas encerrada); La lógica no te manda a sitios sin salida: salas de jefe piden lo de vencerlo, barca de las Sombras, sótano del Pozo (bombas), Réquiem y Bolero solo con otra canción de viaje, tumba real y carrera de Dampé; Cofres con «si ya tienes X, da otra cosa» dan el objeto barajado; Regalo de Darunia también después de la Cueva de los Dodongos; Biggoron (animación propia); Dos regalos con el mismo objeto en un flujo |
| Recompensas de la casa de las Skulltulas | 100 % | — |
| Canciones | 75 % | — |
| Canciones mezcladas con todo | 75 % | — |
| Mapas y brújulas | 90 % | — |
| Corazones de los jefes | 100 % | — |
| Piezas de corazón sueltas | 50 % | — |
| Recompensas de mazmorra (piedras y medallones) | 95 % | — |
| Vasijas, rocas, hierba y cajas | 75 % | — |
| Tiendas | 100 % | — |
| Precios de tienda | 75 % | Precios aleatorios |
| Llaves fuera de su mazmorra | 100 % | — |
| Lógica por salas (experimental) | 50 % | Templos de adulta (Bosque, Fuego, Agua, Sombras, Espíritu, Hielo); Centro de Instrucción Gerudo y Castillo de Ganon |
| Bosque Kokiri | 75 % | — |
| Puerta de Kakariko | 100 % | — |
| Fuente Zora | 100 % | — |
| Puerta del Tiempo | 100 % | — |
| Puente del arcoíris | 100 % | — |
| Escenas: intro | 100 % | — |
| Escenas: llegadas | 65 % | — |
| Escenas: Navi | 85 % | — |
| Escenas: búho | 100 % | — |
| Escenas: jefes | 100 % | — |
| Escenas: tutoriales | 100 % | — |
| Escenas: historia | 80 % | Volcán curándose tras el Templo del Fuego |
| Escenas: carteles | 100 % | — |
| Escenas: paradas | 100 % | — |
| Escenas: regalos | 100 % | — |
| Escenas: nombres | 100 % | — |
| Objetos al empezar | 95 % | — |

La lógica (qué hace falta para llegar a cada sitio) viene del OoT Randomizer de N64, adaptada a este remake. Las salas que cambian en Switch 2, el salto y el esprint todavía no están revisados del todo, así que puede que alguna vez la lógica sea más estricta de lo necesario.

## Qué se baraja

- Cofres del mundo y de las mazmorras.
- Regalos de personajes y minijuegos: Grandes Hadas, sayos, escama de oro, galerías de tiro, la diana del Deku del Bosque Perdido, arquería a caballo, bolos, Skull Kid, teatro deku, el del tejado, Biggoron, la excavación y la carrera de Dampé, Medigoron, Anju, el perro perdido, el Huevo extraño de Malon, las flechas de fuego del lago y la Ocarina del Tiempo del foso.
- Canciones, tiendas y precios.
- Piedras espirituales, medallones y corazones de los jefes.
- Las 13 piezas de corazón que se ven sueltas por el mundo (opción aparte).
- Mapas, brújulas y llaves, también fuera de su mazmorra.
- Parte de las vasijas, rocas, hierba y cajas.

## Qué no se baraja (todavía)

- Las fichas de Skulltula dorada.
- La mayoría de vasijas y cajas.
- Los dekus que venden cosas.
- Los premios de cada canción de las ranas (sí el juego de canciones y el de los bichos).
- Las vacas: todas usan el mismo evento y no se pueden distinguir.
- Las cadenas de intercambio, salvo el Huevo de bolsillo y el Huevo extraño, que eclosionan aunque te los dé otro personaje.
- Las entradas.
- Los cofres nuevos del remake: solo llevan relleno, porque aún no se sabe qué hace falta para abrir cada uno.

## Fallos conocidos

- Las entradas de los jefes, con su nombre, se quedan a propósito. También unas pocas escenas que te llevan a otro sitio (Epona saltando la valla, la celda gerudo, la entrada del Templo del Agua, el Coloso y el cementerio) y el final del juego: quitarlas sin más te dejaría en un sitio equivocado.
- Una bolsa o mejora comprada en una tienda (o a Medigoron) puede no funcionar hasta que cargues la partida otra vez.
- En la excavación de Dampé, el corazón que sale del hoyo es solo la animación. Lo que recibes es lo barajado.
- Algunos personajes siguen nombrando su objeto original al hablar (por ejemplo, Anju habla de la botella).
- En Switch 2 las Grandes Hadas del castillo y de la cima de la Montaña de la Muerte están cambiadas respecto a N64. El Barajador las nombra por su sitio real y deja visitarlas en cualquier orden.

## Legal

- Aquí no hay ningún fichero del juego. El programa lee lo que necesita de tu copia y monta un mod pequeño para el emulador.
- No se salta DRM, cifrado ni protecciones de ningún tipo. Necesitas un volcado legal de tu juego.
- Es un proyecto de fans sin relación con Nintendo. *The Legend of Zelda* y *Ocarina of Time* son marcas de Nintendo.
- La lógica parte del [OoT Randomizer](https://github.com/OoTRandomizer/OoT-Randomizer) (licencia MIT). Incluye evfl, de leoetlino (GPLv2+).
