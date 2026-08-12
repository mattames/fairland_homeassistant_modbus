# AES / Fairland Pool Heat Pump over Modbus — MWH216 / MWH298

A transcribed Modbus register map for the Fairland **MWH216 / MWH298** pool
heat pump control board, a Home Assistant package built from it, and a
read-only scan script for bringing a unit up safely.

The register map is transcribed from the manufacturer's own protocol document
for this board, and that document is included in the repo. Everything derived
from it has been audited line by line against the source — see
[`AUDIT.md`](AUDIT.md).

> **Nothing here has been confirmed against real hardware yet.** Every value is
> transcription from paper. It is careful transcription, and it has been
> audited, but no register in this repo has yet been read from a live board.
> See [Confidence](#confidence--what-is-actually-verified) before you trust it.

---

## Which board is this for?

**MWH216 and MWH298 only.**

Fairland make several control boards with overlapping but *incompatible*
Modbus maps, and they are rebadged under many brand names, so the sticker on
your unit will probably not tell you the board. Open the control panel and read
the board itself, or check the protocol document your supplier gave you — the
first page names the boards it covers.

### This map does not apply to MWH366 / MWH367 / MWH381

Those are a sibling family with a different map. The differences are the kind
that fail *silently* — no error, no exception, just wrong behaviour:

| | MWH216 / MWH298 | MWH366 / MWH367 / MWH381 |
|---|---|---|
| Holding register 1 | **Working mode**: 0 = Smart, 1 = Silence, 3 = Turbo | **Fan speed**: 0 = Silence, 1 = Smart, 2 = Turbo |
| Slave address | Fixed at 1, no register | Settable via 4x register 200 (range 1–16) |
| Water pump status bit | Not present | Discrete input 20 |
| Holding registers 11, 19–24 | Reserved | Fixed-speed ratio (P6), EEV manual mode/opening, intermediate frequency, 2nd fan, fan speed P19 |
| 3x/4x read length | Fixed at 3 registers | Max 8 |
| 3x/4x first address | Restricted to 0, 3, 6, 9, 12 (+15, 18 for 4x) | Unrestricted |

**Register 1 is the one to notice.** The two families invert the meaning of 0
and 1. A config copied from a MWH381 unit onto a MWH216 selects Silence when it
means Smart, and Smart when it means Silence — and the write succeeds, the
register reads back the value you wrote, and nothing anywhere reports a
problem. That single register is the reason this repo is scoped to one board
family and repeatedly refuses to borrow values from the other.

This is not just a reading of the two spreadsheets. Peraqua's own hardware deck
closes with a "Tips" page telling installers to *check the board version and
adapt the mode accordingly*, printing the two register-1 definitions side by
side. The distributor warns about this specific register, which is independent
support for treating it as the difference that matters.

The same trap catches **input registers 15 and up**. They are Reserved on
MWH216. Several configs circulating on the Home Assistant forums read input
registers 17 and 18 as minimum/maximum setpoint — those are for a different
board. If a config you found online reads input registers above 14, it is not
for this one.

The full comparison, with cell-level citations to both manufacturer documents,
is in [`mwh216_register_map.md`](mwh216_register_map.md#differences-between-board-families)
and [`AUDIT.md`](AUDIT.md) task 3.

---

## The hardware this was built for

- **Heat pump** — AES-badged, rebadged Fairland. ~35 kW thermal, ~5.5 kW
  maximum electrical. The badge is irrelevant; the board is what matters.
- **Control board** — Fairland MWH216.
- **Gateway** — Protoss PW11 (Hi-Flying RS485-to-WiFi serial server) wired to
  the board's RS485 header, running in **Modbus TCP ⇄ RTU conversion mode**.
  That mode makes the gateway parse each request, add the RTU CRC, and
  serialise requests from multiple clients onto the one RS485 bus — which is
  what lets Home Assistant poll while you run the scan script. The HA hub is
  therefore `type: tcp`, not `rtuovertcp`.
- **Serial parameters** — 9600 baud, 1 start + 8 data + 1 stop, no parity.
  Minimum 60 ms between transactions.
- **Slave address** — fixed at 1. MWH216 has no slave-number register, so
  there is nothing to configure and nothing to get wrong.

Any RS485 transport works — a USB adapter, an ESP-based bridge, a different
WiFi gateway. Only the hub block at the top of the HA package assumes a PW11.

---

## What is in the repo

### Derived files — written here, from the source documents

| File | What it is |
|---|---|
| [`mwh216_register_map.md`](mwh216_register_map.md) | The register map: coils, discrete inputs, holding registers, input registers, both temperature encodings, the read-length rule, the board-family comparison, and a "Known ambiguities" section recording what the manufacturer document does not settle. |
| [`fairland_mwh216_modbus.yaml`](fairland_mwh216_modbus.yaml) | Home Assistant package — 86 Modbus entities, 5 template sensors, 5 write scripts. Validated against the HA Modbus schema at 2026.8.1. |
| [`scan_heatpump.py`](scan_heatpump.py) | Read-only register dump over Modbus TCP. Issues only FC02/FC03/FC04; there is no code path in it that writes. |
| [`AUDIT.md`](AUDIT.md) | Line-by-line audit of the two derived files against the manufacturer spreadsheets, with cell references. The audit trail for every claim above. |
| [`CLAUDE.md`](CLAUDE.md) | Working notes — hardware detail, the facts that must not be re-derived, and the open hardware questions. |

### Source documents — the authority

These are the manufacturer's own protocol documents, included so you can check
any register yourself rather than taking this repo's word for it.

They come from [Peraqua's product page for the iQ Inver Silence Vertical
13.2 kW](https://shop.peraqua.com/en/p/smart-full-inverter-heat-pump-iq-inver-silence-vertical-13-2-kw-230-v-1p-r32-vertical-discharge-titanium-heat-exchanger-modbus-capable-app-control-suitable-for-salt-electrolysis-ultra-quiet-7301269.html)
(art. 7301269), which publishes seven documents for the unit. The copies here
were verified **byte-identical to the upstream originals** by SHA-256 on
2026-08-12. If you have a Fairland-based unit from any brand, that page is
worth checking — it is the most complete public source found so far.

| File | Status |
|---|---|
| `protocol_MWH216_MWH298.xlsx` | **The document for this board.** The one to check when a register is in doubt. |
| `protocol_MWH216_overview.png` | Scanned overview page of the same sheet. Used to resolve the "reads allowed as first address" marker column. |
| `protocol_MWH381_MWH366_MWH367.xlsx` | Sibling family. Kept **only** to show where the families diverge. Do not read a register out of this file and apply it to a MWH216. |
| `protocol_temperature_types.xlsx` | Temperature conversion appendix. **Belongs to the MWH366/367/381 family, not to this board** — see [`AUDIT.md` §4.1](AUDIT.md) for the proof. Where it overlaps with the MWH216 document it agrees, so nothing derived from it is wrong, but it is not a second source for this board. Upstream it is simply `Modbus_Wärmepumpe.xlsx`, listed with no family in the name between the two family-specific files, which is likely how it came to be taken for a MWH216 document. |

### Third-party reference

| File | Status |
|---|---|
| `reference_ha_config_example.yml` | A community config from the [HA forums](https://community.home-assistant.io/t/fairland-heat-pump-to-ha/304871). Useful for **Home Assistant schema shape only, not as a register source** — it reads input registers 17 and 18 as min/max setpoint, which are Reserved on MWH216. It is an example of the "different board" configs described above. |

### Hardware photos — this unit

[`photos/`](photos/) holds photographs of the owner's actual control
compartment and Protoss PW11 install, with a captioned index in
[`photos/README.md`](photos/README.md). Because they show this board's
silkscreen and the factory wiring-diagram plate, they are **primary evidence
for this specific unit** — they confirm the board is MWH216-V3 in a 3-phase
400 V `BPH(C)78s` machine, and they carry the OUT-relay labels, DIN-input
names, and AIN sensor order for *this* hardware. See that index for which
findings are settled and which still need a bench reading before the register
map is edited.

---

## Using the Home Assistant package

1. Copy `fairland_mwh216_modbus.yaml` to `<config>/packages/`.
2. In `configuration.yaml`:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

3. Edit the `host:` and `port:` at the top of the package (marked
   `# <-- CHANGE ME`). Port 502 is standard for Modbus TCP, but a PW11 often
   keeps its socket port — verify on the gateway's own configuration page.
   A commented `rtuovertcp` block is included for transparent-TCP gateways.
4. **Developer Tools → YAML → Check configuration**, then restart.

Disable the gateway's heartbeat and registration packets, and leave its own
Modbus Master polling off.

### What you get

Entities are prefixed `pool_hp_`, on a hub named `fairland_hp`:

- **`climate.pool_heat_pump`** — current temperature from water inlet, target
  on the heating setpoint, power on coil 0, working mode on the fan-mode slot.
- **Sensors** — all 15 input registers (inlet, outlet, ambient, gas exhaust,
  coil temps, compressor speed/frequency/current, EEV opening, fan RPM) and 14
  holding registers, plus derived Delta T, thermal output, and text renderings
  of the mode registers.
- **Binary sensors** — the 18 status bits and all 36 documented fault flags
  (E, P and F codes), plus an "Active Faults" text sensor that joins whichever
  are on.
- **Scripts** — `pool_hp_set_function`, `pool_hp_set_working_mode`,
  `pool_hp_set_auto_setpoint`, `pool_hp_set_cooling_setpoint`,
  `pool_hp_set_water_pump_mode`.

### Two things in the package that look wrong and are not

**The climate entity is heating-only, deliberately.** The three setpoint
registers have three different documented ranges — auto 12–40 °C, heating
18–40 °C, cooling 12–30 °C — but a HA climate entity has a single
`min_temp`/`max_temp` pair for all modes. An entity that switches target
register by mode therefore cannot have correct bounds in every mode. An earlier
version did exactly that and produced a path where commanding 35 °C in cooling
mode wrote a raw value past the register's documented cap, to a live
compressor. It is now pinned to heating, where the bounds are exactly right,
and the auto and cooling setpoints live in scripts carrying their own correct
bounds. Do not re-add mode switching to `target_temp_register`.

**Coil 2 has no entity.** It is "Restore factory values". Its absence is
deliberate — do not add it.

---

## Running the scan script

`scan_heatpump.py` dumps every documented register once and prints it beside
its documented meaning. Use it to confirm the gateway works and the register
map matches your board **before** pointing Home Assistant at it.

It is strictly read-only: only FC02, FC03 and FC04, and no code path that
writes a coil or a register.

```sh
python3 -m venv venv
./venv/bin/pip install pymodbus

./venv/bin/python scan_heatpump.py <gateway-ip> [port]
```

Port defaults to 502. Options: `--slave` (default 1, fixed on this board),
`--timeout` (default 3 s), `--delay` (default 0.06 s, the documented minimum
between transactions).

```sh
./venv/bin/python scan_heatpump.py 192.168.0.50
./venv/bin/python scan_heatpump.py 192.168.0.50 8899 --timeout 5
```

Verified against pymodbus 3.14. The slave-id keyword was renamed over releases
(`unit` → `slave` → `device_id`), so the script detects which one the installed
version takes rather than pinning a version.

It reads input registers 0–14 (plus 15–20 as a board check), holding registers
0–10, 17, 18, 25, and discrete inputs 0–17 and 48–95.

### Reading the output

- **Start with the `PRIORITY CHECK` block.** It settles the one value in this
  repo that most needs settling — see [Confidence](#confidence--what-is-actually-verified).
- **Temperatures print both conversions.** This board uses two encodings and
  the wrong one reads 30 °C out while still looking entirely plausible. Every
  temperature line shows raw, type 1 and type 2, with `<= type 1` / `<= type 2`
  marking the one the manufacturer document specifies for that register.
- **Input registers 15–20 are a board check, not data.** They are documented
  Reserved on MWH216, so `modbus exception 2 (illegal data address)` is the
  expected, confirming answer and is not counted as a failure. **A plausible
  value there means this is probably not a MWH216** — and the rest of this map
  should be treated as suspect.
- **Individual read failures do not stop the scan.** Transport errors are
  distinguished from proper Modbus exception responses, and everything that
  failed is listed again in the summary.

If it connects but values are stable and wrong, suspect the read-length rule:
the document says reads must begin at a permitted first address with the count
fixed at 48 bits (0x/1x) or 3 registers (3x/4x), "otherwise the slave may
return incorrect data". This script reads single registers, as the HA package
and every working community config do.

---

## Confidence — what is actually verified

Be clear about what has and has not been established.

**Verified:** that the derived files faithfully reproduce the manufacturer
document. [`AUDIT.md`](AUDIT.md) records a cell-by-cell check of every coil,
all 54 named discrete inputs, all 14 holding registers and all 15 input
registers against `protocol_MWH216_MWH298.xlsx`, plus the HA package's
addresses, `input_type` values and temperature encodings. It found 5 definite
errors, 4 places where the source itself is ambiguous, and 9 cosmetic issues.
All five definite errors are fixed; the ambiguities are documented rather than
resolved, because resolving them needs hardware.

**Not verified:** any of it, against a real board. **No register in this repo
has been read from live hardware.** The map may be a perfect transcription of a
document that is wrong, or right about a board revision that is not yours.

### Input register 12 rests on a single cell

The highest-priority uncertainty. IR 12 (cooling plate temperature) is
documented as **temperature type 2** — °C = raw / 2, rather than the type 1
°C = (raw − 60) / 2 used by almost everything else on this board.

That claim comes from **one cell in one document**: the Remark column of the
cooling-plate row in `protocol_MWH216_MWH298.xlsx`. Nothing corroborates it.
`protocol_temperature_types.xlsx` belongs to the sibling family and does not
list the register at all, and the MWH366/367/381 document leaves its own IR 12
unannotated. There is no second document to fall back on. (IR 6, gas exhaust,
is by contrast marked type 2 in both documents — that one is corroborated.)

This has been tested rather than assumed. All seven documents Peraqua publish
for the unit were checked on 2026-08-12: the other four carry no register
annotations, and `Modbus_Wärmepumpe.xlsx` does not contain the string "Cooling
plate temp" at all. Nothing upstream corroborates it, so the answer has to come
from hardware.

If the cell is wrong, IR 12 reads 30 °C low and still looks plausible. The scan
script prints a dedicated check comparing both readings against ambient: the
cooling plate is the inverter heatsink, so it sits at or above ambient when
idle and well above it under load, and is never meaningfully below ambient. One
idle sample often cannot decide it — re-run with the compressor loaded. If type
1 turns out to be correct, three files need changing: the register map, the HA
package, and the scan script.

### Other things awaiting hardware

- The PW11's actual port in Modbus TCP mode (502 vs its socket port).
- Whether the heating setpoint sensor matches the unit's own display —
  **confirm this before writing anything**.
- Whether gas exhaust really reads 60–100 °C when running.
- Which OUT bits are compressor, fan, 4-way valve and circulation pump. The
  document does not say; the bits are generic. Named versions found in other
  Fairland configs come from sibling boards and do not apply.
- Whether DIN2 (discrete input 3) is jumpered as an external enable contact on
  your unit. Peraqua document it that way — factory-bridged, and opening it
  blocks the pump without overwriting any parameter — but that is a distributor
  wiring convention, not something the Modbus document states. See the
  [register map](mwh216_register_map.md#discrete-inputs-1x--fc02); it is also a
  control path that needs no register write.
- Whether the read-length constraint is actually enforced. If it is, holding
  register 25 sits outside every permitted block and cannot be read compliantly
  at all — the document defines a register its own read rule cannot address.
  See "Known ambiguities" in the register map.
- Whether Turbo does anything. The source qualifies it with "(Some models
  without Turbo)".

### Safety

**Reads are safe. Writes are not.** This is a mains-powered machine with a
compressor. Only write registers the manufacturer document names, never write
to discover what a register does, and never write coil 2.

---

## Corrections welcome

If you have a MWH216 or MWH298 and any value here is wrong, please open an
issue — a corrected register with what you actually observed is worth more than
everything in this repo, all of which is still paper. Readings from a running
unit are especially useful for input register 12, the OUT bit assignments, and
whether the read-length rule is enforced on your firmware.

Sibling-board owners (MWH366 / MWH367 / MWH381, or anything else Fairland)
are welcome too. The board-family comparison table exists to stop configs being
copied across families, and it is only as good as the boards people have
checked it against. If your board disagrees with the table, that is worth
knowing.

Corrections to the derived files should cite the manufacturer document or a
hardware observation — [`AUDIT.md`](AUDIT.md) shows the citation style. Where
the source itself is ambiguous, the register map's "Known ambiguities" section
records that rather than papering over it; please add to it rather than
silently resolving one.

---

## Sources

- Fairland *Modbus Wärmepumpe MWH216 & MWH298* — manufacturer protocol
  document, included here as `protocol_MWH216_MWH298.xlsx`.
- Fairland *Modbus Wärmepumpe MWH381 & MWH366 & MWH367* — sibling family,
  included as `protocol_MWH381_MWH366_MWH367.xlsx`.
- <https://github.com/spdr870/fairland_iphcr45_modbus>
- <https://github.com/rstcologne/ESP-Home-Fairland-Heatpump>
- <https://community.home-assistant.io/t/fairland-heat-pump-to-ha/304871>
- <https://community.home-assistant.io/t/fairland-pool-warmepumpe-heatpump-ixcr66-modbus-register/711658>

The manufacturer protocol documents are included because a register map is not
much use without the thing it was transcribed from, and because they are
otherwise hard to find. They are Fairland's, not mine. If Fairland would rather
they were not here, open an issue and they will come out.
