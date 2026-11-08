# Feature checklist (acceptance, not a build list)

Because we compile NetHack's own source, features come with the code. This
list is what we *verify* works on the C64 (Phase 4) — by scripted AUTOTEST
runs where practical, by hand otherwise. Mark each `[x]` with how it was
checked (test name, or "manual, date").

## Engine
- [ ] Dungeon generation: rooms + corridors, mazes, caverns (Mines)
- [ ] Level memory: remembered glyphs, returning to visited levels
- [ ] Vision / field of view (lit rooms, dark corridors, blindness, telepathy)
- [ ] Movement incl. diagonals, running (`G`/shift), travel (`_`)
- [ ] Monster AI: hostile, peaceful, fleeing, item use (`muse.c`)
- [ ] Combat: melee, ranged, spells, passive responses
- [ ] Inventory: stacking, letters, containers (bag of holding), encumbrance
- [ ] Hunger, nutrition, corpses and intrinsics
- [ ] Status effects and timeouts
- [ ] RNG seeded and unbiased; bones-compatible behaviour within this port

## Items (each class: use, identify, BUC)
- [ ] Weapons & armour (wield, wear, enchantment, erosion)
- [ ] Potions (quaff, dip, throw)
- [ ] Scrolls (read; identify, enchant, teleport, genocide, ...)
- [ ] Wands (zap, engrave-ID, break)
- [ ] Rings & amulets
- [ ] Tools (apply: keys, lamps, horns, unicorn horn, ...)
- [ ] Spellbooks and casting
- [ ] Artifacts (gifts, wishes, invoking, quest artifacts)
- [ ] Discoveries list (`\`), naming/calling (`#name`, `C`)

## Places
- [ ] Gnomish Mines + Minetown (temple, shops)
- [ ] Sokoban (all 4 levels; boulder rules)
- [ ] Oracle (consultations need `oracles` text)
- [ ] Big room, rogue level tribute
- [ ] Quest (13 roles' home/locate/goal levels + `quest.dat` text)
- [ ] Fort Ludios (via magic portal)
- [ ] Medusa, Castle (drawbridge, wand of wishing)
- [ ] Gehennom mazes, Juiblex, Orcus, Asmodeus, Baalzebub, Wizard's Tower, Vlad's Tower
- [ ] Vibrating square, invocation, Sanctum
- [ ] Elemental planes and Astral (ascension)

## Special rooms and systems
- [ ] Shops and shopkeepers (pricing, credit, theft, Kops)
- [ ] Temples and priests (donations, protection)
- [ ] Altars (BUC by drop, sacrifice, conversion)
- [ ] Prayer (timeout, luck, troubles)
- [ ] Thrones, fountains, sinks, graves, trees
- [ ] Pets (taming, following across levels, eating)
- [ ] Polymorph (self and monsters), lycanthropy
- [ ] Engraving (Elbereth), graffiti, headstones
- [ ] Traps (all types incl. level teleporters, trapdoors, magic portals)

## UI (the c64 window port)
- [ ] 80x21 map + 2 status lines + message line
- [ ] `--More--` handling and message history (`^P`)
- [ ] Menus: single/multi select, paging, item counts
- [ ] Inventory display (`i`, `I`), `#` extended commands with completion
- [ ] `y/n/q` prompts, getlin text entry, direction prompts
- [ ] Help (`?`), encyclopedia lookup (`/`, `;`)
- [ ] Options (`O`) — reduced set, persisted
- [ ] Character info (`^X`), attributes, enlightenment
- [ ] Key layout usable on a C64 keyboard (vi-keys; `number_pad` off)

## Persistence
- [ ] Save and restore (`S`), across power cycles
- [ ] Bones files
- [ ] High-score list (`topten`) and DYWYPI end-of-game dump
- [ ] Panic save
