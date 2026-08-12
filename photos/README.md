# Hardware photos — this unit

Photographs of the owner's actual heat pump control compartment and the
Protoss PW11 gateway install, taken 2026-08-12. These are **primary evidence
for this specific unit** and, where they show silkscreen or a factory plate,
they outrank the generic Peraqua family documents for questions about *this*
board.

Unit identity confirmed by these photos: control board **MWH216-V3
(2020.02.20, V8)**; unit model **BPH(C)78s.P-1.Wi-Fi (AUS)**, wiring-diagram
doc `013090860002`, box barcode `BPH78CS` / `210206`. Supply is **3-phase
400 V / 50 Hz** (L1/L2/L3/N), so the earlier "~5.5 kW electrical" figure is a
three-phase machine — consistent with the 3-pole Goodspec HLC-3XU04CG
contactor visible in the overview shots.

| File | What it shows |
|---|---|
| `control_box_overview.jpg` | Whole opened control compartment. 3-pole contactor (Goodspec HLC-3XU04CG, L1/L2/L3→T1/T2/T3), three run capacitors, PFC electrolytic bank + IPM/driver daughterboard (top right), main MWH216 board (right), finned braking resistor (bottom left). |
| `power_board_overview.jpg` | Closer view of the power section: PFC caps (`MWH11WB-CAP-V3.6C`, `B78CS` driver), run caps, main **MWH216-V3** board with the OUT-relay silkscreen strip, `SMY-2016-112` inductor, empty DIN rail. |
| `mwh216_board_closeup.jpg` | Top-down close-up of the MWH216-V3 board. Reads the board revision, `MDRV`, the OUT-relay label strip, MCU, and the unit barcode strip ending `BPH78CS`. |
| `board_terminals_rs485_din.jpg` | Bottom-edge terminal strip: `AIN1`, `CN12`, the RS485 header **`C60` = `B A G +12V`**, `CN26`, `DIN1`–`DIN5`, `WCTIL`, `CN2`, and the red 4-way DIP switch `SW1` (`ON / 1 2 3 4`). This is the connector the gateway taps. |
| `pw11_closeup.jpg` | Protoss-PW11 (RS485↔WiFi). Top screw terminals **7 / 6 / 5** (RS485 side), SMA antenna, status LEDs — **Active + Link green, Net off, Power red** at the time of the photo. |
| `pw11_context.jpg` | The PW11 on its DIN rail in context: `SMY-2016-112` inductor below it, low-voltage power wiring, RS485 run across to board header `C60`, OUT-relay labels on the board at right. |
| `pw11_power_splice.jpg` | Hand holding two **field-made soldered splices** (a brown pair and a blue pair, tinned and twisted) over the DC-bus cap bank — the installer's low-voltage tap feeding the gateway. Not a factory joint; noted so a future reader doesn't mistake it for OEM wiring. |
| `wiring_diagram_bphc78s.jpg` | The factory wiring-diagram plate, `BPH(C)78s.P-1.Wi-Fi (AUS)` / `013090860002`. See findings below. |

## What the photos settle (vs. the open questions)

These are observations to fold into [`../mwh216_register_map.md`](../mwh216_register_map.md)
after the bit-level numbering is confirmed — see the caveats.

- **OUT relays are silkscreen-labelled on this board.** The strip over the
  relay bank reads, in board order:
  `Electric heating belt of condenser · 4-way Valve · Low speed · Middle speed ·
  High speed · Water Pump · Compressor`.
  That names what the generic `OUT1–OUT9` discrete bits actually drive on
  *this* unit — the identities Open Question 5 asked for. **Caveat:** the
  silkscreen gives *functions*, not a proven function→OUT-number map; the
  wiring diagram shows relays `OUT1A`…`OUT8A`, more positions than labels.
  Confirm each bit against a live run cycle before renaming entities.
- **The DIN inputs are *not* generic on this unit.** The wiring-diagram
  callouts name them: **Remote Controller**, **High-pressure protection
  switch**, **Low-pressure protection switch**, **Water-flow switch**, and a
  **"Customer remote control switch connector (Disabled upon jumper on
  DIN2)"**. So the DIN2 external-release path is printed on the factory diagram
  for this exact unit — stronger than the distributor-note status it has in
  CLAUDE.md. **Caveat:** exact callout→DIN-number assignment isn't cleanly
  legible; confirm which physical DIN is which before wiring a dry contact.
- **Analog sensor order (AIN1→AIN7), from the diagram, top to bottom:**
  inlet water · outlet water · heating-coil pipe · **cooling-coil pipe** ·
  exhaust · return gas · air. Note the diagram calls IR 12 the "cooling coil
  pipe temp sensor" (not "cooling plate"). This is *identity* corroboration
  only — it does **not** resolve the type-1-vs-type-2 scaling question
  (Open Question 1), which still needs the hardware reading.
- **RS485/gateway header:** the PW11 lands on board header `C60`
  (`B A G +12V`) — the diagram's "Wi-Fi terminal". Terminal 7/6/5 on the PW11
  to `B/A/G` on the board.
- **`SW1` DIP switch exists** (4-way, red). Its function is not in the Modbus
  document; do not assume it sets slave address (the map notes MWH216 has no
  slave-number register). Left as an open item.
