# Pool heat pump — Modbus integration into Home Assistant

## Hardware

- **Heat pump:** AES-badged unit, rebadged Fairland. ~35 kW thermal, ~5.5 kW
  max electrical.
- **Control board:** Fairland **MWH216**. Confirmed by the owner, and the
  manufacturer protocol document is for "MWH216 & MWH298".
- **Gateway:** Protoss PW11 (Hi-Flying RS485-to-WiFi serial server) wired to
  the board's RS485 header. Decision made to run it in **Modbus TCP ⇄ RTU
  conversion mode**, so the HA hub is `type: tcp`, not `rtuovertcp`.
- **Serial params:** 9600, 1 start + 8 data + 1 stop, no parity. Slave address
  fixed at 1 — MWH216 has no slave-number register.

## Files in this repo

Written here:

- `fairland_mwh216_modbus.yaml` — the HA package. Goes in
  `<config>/packages/`. Validated against the HA Modbus schema at 2026.8.1.
- `mwh216_register_map.md` — register map transcribed from the manufacturer
  document, plus the differences between board families.

Source documents — these are the authority, the two files above are derived
from them:

- `protocol_MWH216_MWH298.xlsx` — the manufacturer protocol document for
  **this** board. The one to check when a register is in doubt.
- `protocol_temperature_types.xlsx` — protocol document carrying the type 1 /
  type 2 conversion tables and the per-register "Register Content" notes that
  say which type each temperature uses.
- `protocol_MWH381_MWH366_MWH367.xlsx` — sibling board family. Kept only to
  show where the families diverge. Do not read a register out of this file and
  apply it to MWH216.
- `protocol_MWH216_overview.png` — scanned overview page for the MWH216.

Third-party reference:

- `reference_ha_config_example.yml` — a community config from the HA forums
  (`community.home-assistant.io/t/fairland-heat-pump-to-ha/304871`). Useful for
  HA schema shape only, **not** as a register source: it reads input registers
  17 and 18 as min/max setpoint, which are Reserved on MWH216. It is one of the
  "different board" configs warned about below.

## Critical facts — do not re-derive these

**Two temperature encodings on this board.**

| Type | Conversion | HA |
|---|---|---|
| Type 1 | °C = (raw − 60) / 2 | `scale: 0.5`, `offset: -30` |
| Type 2 | °C = raw / 2 | `scale: 0.5`, **no offset** |

Type 2 applies to exactly two registers: input 6 (gas exhaust) and input 12
(cooling plate). Everything else temperature-related is type 1. Mixing them up
reads 30 °C out and still looks plausible.

**Input registers 15–29 are Reserved on MWH216.** There are no version,
model-code, setpoint-limit, supply-voltage or restart-delay registers. Configs
found online that read input registers 15+ are for a different board.

**Discrete inputs 2–17 are generic** on this board: DIN1–5 (2–6), OUT1–9
(7–15), malfunction indicator (16), compressor demand (17). The document does
not say what they're wired to. Named versions found in other Fairland configs
are from sibling boards and do not apply.

**Coil 2 is "Restore factory values". Never write it.**

**Holding register 1** on MWH216: 0 = Smart, 1 = Silence, 3 = Turbo. Value 2 is
undefined. The MWH366/367/381 boards invert this (0 = Silence, 1 = Smart), so
configs must not be copied between families.

**Setpoint step** is 2 raw units = 1.0 °C. The board will not accept
half-degree setpoints.

**Read-length constraint.** The document says reads must start at a permitted
first address with count fixed at 48 bits (0x/1x) or 3 registers (3x/4x), or
the slave "may return incorrect data". Permitted first addresses: 1x → 0, 48;
3x → 0, 3, 6, 9, 12; 4x → 0, 3, 6, 9, 12, 15, 18. The current config uses
single-register reads, as all working community configs do. If values are
stable but wrong, this is the first thing to suspect.

## Open questions — resolve these on real hardware

1. Confirm the PW11's port in Modbus TCP mode (502 vs its socket port).
2. Confirm `sensor.pool_hp_heating_setpoint` matches the unit's own display
   before writing anything.
3. Confirm gas exhaust temp reads 60–100 °C when running, not ~30 °C below.
4. Identify which OUT bits correspond to compressor, fan, 4-way valve, and
   circulation pump by observing a run cycle, then rename those entities.
5. Test whether the read-length constraint is actually enforced.

## Working rules

- **Reads are safe. Writes are not.** This is a mains-powered machine with a
  compressor. Only write to registers the manufacturer document names, and
  never write to discover what a register does.
- Verify against `mwh216_register_map.md` rather than memory or general
  Fairland knowledge — the board families differ in ways that fail silently.
- HA's Modbus integration has **no read action** and no `number` or `select`
  platform. Reading is done by declaring entities; only
  `modbus.write_register` and `modbus.write_coil` exist as actions.
- `entity_category` is not valid on Modbus entities. The platform schemas are
  strict and reject unknown keys.

## Intended use

Primary: dump curtailed solar export into the pool during negative-price
events (household is on Amber wholesale pricing with solar and a battery).
Secondary: modulate via working mode to track available surplus rather than
running flat out. Measure COP once from inlet/outlet/ambient plus a CT clamp
to settle whether cheap overnight power beats warm-afternoon efficiency.

There is no power register on this board — compressor current (0.1 A) and PFC
voltage won't give real consumption. Use a CT clamp on the heater circuit.
