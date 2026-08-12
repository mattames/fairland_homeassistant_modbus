# Fairland MWH216 — Modbus RTU register map

From the manufacturer document *Modbus Wärmepumpe MWH216 & MWH298*. This map is
for the **MWH216 / MWH298** boards only. The MWH366 / MWH367 / MWH381 family
uses a different map — see "Differences between board families" at the end.

**Link:** RS485, Modbus RTU, 9600, 1 start + 8 data + 1 stop, no parity.
Slave address fixed at 1 (no slave-number register on this board).
Minimum 60 ms between transactions.

## Temperature encodings — this board uses two

| Type | Conversion | Reverse | HA config |
|---|---|---|---|
| Type 1 | °C = (raw − 60) / 2 | raw = °C × 2 + 60 | `scale: 0.5`, `offset: -30` |
| Type 2 | °C = raw / 2 | raw = °C × 2 | `scale: 0.5`, no offset |

Type 2 applies to **only two registers**: input 6 (gas exhaust) and input 12
(cooling plate). Both run hot, 60–100 °C. Applying type 1 to them reads 30 °C
low and still looks plausible, which makes it an easy error to miss.

## Read-length constraint

The document states reads must begin at a permitted first address, with the
count fixed at 48 bits for 0x/1x and 3 registers for 3x/4x, or the slave may
return incorrect data.

| Table | Permitted first addresses |
|---|---|
| 1x (discrete inputs) | 0, 48 |
| 3x (input registers) | 0, 3, 6, 9, 12 |
| 4x (holding registers) | 0, 3, 6, 9, 12, 15, 18 |

In practice every working community Fairland config reads single registers.
Treat this as the first thing to suspect if values are stable but wrong.

## Coils (0x) — FC01 read / FC05 write

| Addr | Content | Range | Default | Notes |
|---|---|---|---|---|
| 0 | Power switch | 0–1 | 0 | 0 = off, 1 = on |
| 1 | Compulsory defrosting | 0–1 | 0 | 1 = enter defrost |
| 2 | **Restore factory values** | 0–1 | 0 | **Do not write** |
| 3–47 | Reserved | | | |

## Discrete inputs (1x) — FC02

| Addr | Content | Notes |
|---|---|---|
| 0 | ON/OFF | 0 = off, 1 = on |
| 1 | Defrosting | |
| 2–6 | DIN1 … DIN5 | 0 = disconnected, 1 = connected |
| 7–15 | OUT1 … OUT9 | 0 = closed, 1 = output |
| 16 | Malfunction / protection indicator | 0 = none, 1 = yes |
| 17 | Compressor running demand | 0 = none, 1 = yes |
| 18–47 | Reserved | |
| 48–57 | E0 … E9 | fault flags |
| 58, 59 | EA, Eb | |
| 60 | Reserved | |
| 61 | Ed | |
| 62–63 | Reserved | |
| 64–73 | P0 … P9 | |
| 74 | PA | |
| 75–79 | Reserved | |
| 80–89 | F0 … F9 | |
| 90, 91 | FA, Fb | |
| 92–95 | Reserved | |

The *Modbus document* gives no indication of what DIN1–5 and OUT1–9 are
physically wired to — but this unit's own factory wiring diagram does. See the
photographs in [`photos/`](photos/) (`wiring_diagram_bphc78s.jpg`, and the
board-silkscreen shots), which are primary evidence for this specific machine.

**OUT relays — silkscreen labels on the board**, in physical order along the
relay bank: electric heating belt of condenser · 4-way valve · fan low speed ·
fan middle speed · fan high speed · water pump · compressor. That names what
the generic `OUT1–OUT9` bits actually drive here — but the silkscreen gives
*functions*, not a proven function→bit-number map (the diagram shows relay
positions `OUT1A`…`OUT8A`, more than the seven labels). **Confirm each bit
against a live run cycle before renaming entities** — or, if you never can,
treat the function set as known and the exact numbering as unconfirmed.

**DIN inputs — named on the wiring diagram**, not generic: remote controller,
high-pressure protection switch, low-pressure protection switch, water-flow
switch, and the customer remote-control (external-release) contact on DIN2
below. The diagram's callout numbers don't cleanly resolve which physical DIN
carries which, so confirm the specific DIN before wiring a dry contact.

**DIN2 (address 3) is the external enable contact**, at least as Peraqua wire
their units. Their one-page note *External release via DIN2* (linked from the
product page in Sources) states that DIN2 is a socket on the main board,
bridged with a jumper at the factory and therefore closed on delivery. Opening
it blocks the heat pump and the controller displays `OFF`. It does not
overwrite the operating mode or any parameter — it behaves like the flow
switch, blocking regardless of current state, and when closed the pump starts
only if there is also a heating or cooling demand. The external controller must
switch it **potential-free; no voltage may be applied.** Peraqua suggest
keeping it closed for at least 60 minutes at a time to avoid short-cycling.

This is now corroborated on **this unit's own factory wiring diagram**
([`photos/wiring_diagram_bphc78s.jpg`](photos/wiring_diagram_bphc78s.jpg),
model `BPH(C)78s.P-1.Wi-Fi (AUS)`), which prints a "Customer remote control
switch connector (**Disabled upon jumper on DIN2**)" callout — so it is a
documented feature of this machine, not merely a Peraqua distributor
convention. The manufacturer *Modbus* document still names the bit only as
DIN2; the wiring diagram is the source that ties it to the external-release
contact. One caveat remains: the diagram doesn't cleanly show which physical
DIN terminal is DIN2, so confirm the jumper on your own board before relying on
it.

This matters as a control path in its own right: a potential-free dry contact
on DIN2 blocks and releases the pump **without writing any register** — no
setpoint or mode write, none of the write-side registers that can only be
validated on hardware. If Modbus write validation is not available, this is the
low-risk way to gate the pump for solar-dump control.

## Holding registers (4x) — FC03 read / FC06 write

| Addr | Content | Range | Step | Default | Notes |
|---|---|---|---|---|---|
| 0 | Function selection | 0–2 | 1 | 1 | 0 = Auto, 1 = Heating, 2 = Cooling |
| 1 | Working mode selection | 0–3 | 1 | 1 | 0 = Smart, 1 = Silence, 3 = Turbo. **2 undefined.** Source adds "(Some models without Turbo)" — 3 may be a no-op |
| 2 | Auto mode setpoint | 84–140 | 2 | 112 | Type 1 → 12–40 °C, default 26 |
| 3 | Heating mode setpoint | 96–140 | 2 | 112 | Type 1 → 18–40 °C, default 26 |
| 4 | Cooling mode setpoint | 84–120 | 2 | 112 | Type 1 → 12–30 °C, default 26 |
| 5 | Water pump working mode (P0) | 0–2 | 1 | 0 | 0 = continuous, 1 = water temp, 2 = time + water temp |
| 6 | Water pump run time (P1) | 10–120 min | 5 | 60 | |
| 7 | Compressor run time between defrost (P2) | 30–90 min | 1 | 30 | |
| 8 | Defrost entry temp (P3) | 26–60 | 2 | 46 | Type 1 → −17 to 0 °C, default −7 |
| 9 | Max defrost run time (P4) | 1–12 min | 1 | 12 | |
| 10 | Defrost exit temp (P5) | 76–120 | 2 | 86 | Type 1 → 8–30 °C, default 13 |
| 11–16 | Reserved | | | | |
| 17 | EEV superheat, heating | 40–100 | 2 | 66 | Type 1 → −10 to 20 °C, default 3 |
| 18 | EEV superheat, cooling | 40–100 | 2 | 64 | Type 1 → −10 to 20 °C, default 2 |
| 19–24 | Reserved | | | | |
| 25 | Power-off restart memory | 0–1 | 1 | 1 | 0 = stay off, 1 = restore prior state |
| 26–32 | Reserved | | | | |

Step 2 in raw units is 1.0 °C, so the board will not accept half-degree
setpoints.

## Input registers (3x) — FC04

| Addr | Content | Units / conversion |
|---|---|---|
| 0 | Compressor running speed percentage | % |
| 1 | Compressor target frequency | Hz |
| 2 | PFC voltage | V |
| 3 | Water inlet temp (AIN1) | Type 1 |
| 4 | Water outlet temp (AIN2) | Type 1 |
| 5 | Ambient temp (AIN7) | Type 1 |
| 6 | Gas exhaust temp (AIN5) | **Type 2** |
| 7 | Outer coil pipe temp, evaporator (AIN3) | Type 1 |
| 8 | Gas return temp (AIN6) | Type 1 |
| 9 | Inner coil pipe temp, titanium HX (AIN4) | Type 1 |
| 10 | Compressor frequency | Hz |
| 11 | Compressor current | 0.1 A |
| 12 | Cooling plate temp | **Type 2** |
| 13 | EEV opening | |
| 14 | DC fan motor speed | RPM |
| 15–29 | Reserved | |

**There are no mainboard-version, model-code, setpoint-limit, supply-voltage
or restart-delay registers on this board.** Those exist on other Fairland
boards, and configs shared online that read input registers 15+ are not for
MWH216.

This unit's factory wiring diagram
([`photos/wiring_diagram_bphc78s.jpg`](photos/wiring_diagram_bphc78s.jpg))
lists exactly **seven wired AIN sensors** — inlet water, outlet water,
heating-coil pipe, cooling-coil pipe, exhaust, return gas, air — matching the
AIN1–AIN7 assignments above (IR 3, 4, 7, 9, 6, 8, 5). It labels AIN3/AIN4
"heating-coil"/"cooling-coil" where this table says outer/inner; same
positions, a wording difference only. **IR 12 ("cooling plate") is not among
those seven** — it has no external AIN sensor on the diagram, consistent with
it being the internal inverter-heatsink temperature. So the diagram confirms
the wired-sensor registers but adds nothing to IR 12, whose type-2 encoding
remains single-sourced (see the README).

## Differences between board families

Worth knowing, because configs get copied between them and the failures are
silent rather than loud.

| | MWH216 / MWH298 | MWH366 / MWH367 / MWH381 |
|---|---|---|
| HR 1 semantics | Working mode: 0 Smart, 1 Silence, 3 Turbo | Fan speed: 0 Silence, 1 Smart, 2 Turbo |
| Slave address | Fixed at 1 | Settable via 4x register 200, range 1–16 |
| Water pump status bit | Not present | **DI 20** |
| Input registers 15+ | Reserved | Reserved |
| Extra holding registers | — | Fixed-speed ratio (P6), EEV manual mode and opening, intermediate frequency ratio, 2nd fan control, fan speed P19 |
| 3x/4x read length | Fixed at 3 | Max 8 |
| 3x/4x **first address** | Restricted to 0, 3, 6, 9, 12 (and 15, 18 for 4x) | **Unrestricted** — any start address |
| 1x/0x read length | Fixed at 48 | Max 48, first address 0 or 48 |

The two families invert the meaning of 0 and 1 in the mode register. A config
copied across would select Silence when asking for Smart, and vice versa —
with no error.

This is corroborated outside the two spreadsheets. Peraqua's own hardware deck
*iQnnect Hardware Wärmepumpe* (linked from the product page in Sources) ends
with a "Tips" page reading *"Version der Platine prüfen, und Modus
gegebenenfalls adaptieren"* — check the board version and adapt the mode
accordingly — and prints the two register-1 definitions side by side: MWH216 &
MWH298 as `Working Mode Selection` (0 Smart, 1 Silence, 3 Turbo) against
MWH381 & MWH366 & MWH367 as `Fan speed selection` (0 Silence, 1 Smart,
2 Turbo). The distributor warns installers about this specific register, which
is independent support for treating it as the headline difference between the
families.

The first-address row matters as much as the length row. MWH381 states only a
maximum consecutive-read count and no restriction on where a read starts, so a
polling scheme written for that family is legal there and violates the MWH216
rule. The documented symptom is silently incorrect data, not an error.

## Known ambiguities in the source document

Two things the manufacturer document does not settle. Both are recorded here
so they are not silently resolved by someone later assuming the map is
complete. **Do not remove this section without hardware evidence.**

### 1. Whether address 0 is a permitted first address

The read-length table above lists 0 as a permitted first address for 1x, 3x
and 4x. That is an **inference from the sheet's layout, not a transcription.**

In the source, "Reads allowed as first address" is a column-A marker cell. It
appears on each section's header row and then on specific data rows — 48 for
1x; 3, 6, 9, 12 for 3x; 3, 6, 9, 12, 15, 18 for 4x. Address 0 is never marked
on its own data row in any table, and there are no merged cells tying a
header-row marker to the row beneath it.

Read strictly, address 0 would not be permitted — which cannot be right, since
it would make coils 0–47, discrete inputs 0–47 and input registers 0–2
(compressor speed, target frequency, PFC voltage) unreachable. Two things
support reading 0 as permitted:

- The block arithmetic only closes if it is. 3x from 0/3/6/9/12 at 3 registers
  each covers exactly 0–14, the full populated range. 0x from 0 at 48 bits
  covers exactly 0–47. 1x from 0 and 48 covers exactly 0–95.
- The sibling MWH381 document states the equivalent rule in prose: "the first
  address of the read must be 0 or 48".

Treated as settled enough to act on, but it is an inference. The 0x table is
included on the same basis — the source carries the marker column there but
marks no data row at all, so 0x → 0 only.

### 2. Holding register 25 is unreachable under the document's own read rule

Permitted 4x first addresses stop at 18, and the count is fixed at 3. The
reachable blocks are therefore [0–2], [3–5], [6–8], [9–11], [12–14], [15–17],
[18–20] — ending at register 20.

**HR 25 (power-off restart memory) falls outside every permitted block.** No
marker at 21 or 24 would let a compliant read reach it. The document defines a
register its own read rule cannot address.

This only bites if the read-length constraint turns out to be enforced on real
firmware. If it is, HR 25 cannot be read compliantly at all, and the block-read
fallback described in the HA package will not cover it.

## Sources

- Fairland *Modbus Wärmepumpe MWH216 & MWH298* (manufacturer document)
- Fairland *Modbus Wärmepumpe MWH381 & MWH366 & MWH367* (manufacturer document)
- Peraqua product page for the iQ Inver Silence Vertical 13.2 kW (art. 7301269),
  which is where both of the above originate and which carries seven documents
  in total, including the DIN2 note and the hardware deck cited above:
  <https://shop.peraqua.com/en/p/smart-full-inverter-heat-pump-iq-inver-silence-vertical-13-2-kw-230-v-1p-r32-vertical-discharge-titanium-heat-exchanger-modbus-capable-app-control-suitable-for-salt-electrolysis-ultra-quiet-7301269.html>
- <https://github.com/spdr870/fairland_iphcr45_modbus>
- <https://github.com/rstcologne/ESP-Home-Fairland-Heatpump>
- <https://community.home-assistant.io/t/fairland-heat-pump-to-ha/304871>
- <https://community.home-assistant.io/t/fairland-pool-warmepumpe-heatpump-ixcr66-modbus-register/711658>
