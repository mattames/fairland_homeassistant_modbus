# Audit — derived files vs. manufacturer spreadsheets

Audit date: 2026-08-12. Nothing was edited; this is findings only.

**Sources of truth used**

- `protocol_MWH216_MWH298.xlsx` — 127 rows × 8 cols, single sheet. Cell refs
  below are `[col][row]` as the sheet numbers them (header row 4 = `r4`).
- `protocol_MWH216_overview.png` — rendered image of the same sheet, used to
  resolve the column-A "Reads allowed as first address" markers.
- `protocol_MWH381_MWH366_MWH367.xlsx` — 131 rows × 7 cols. Note the column
  offset: this file has no column-A marker column, so its `Register Addr.` is
  column A where the MWH216 file uses column B.
- `protocol_temperature_types.xlsx` — 26 rows × 3 cols.

**Headline:** the register map is accurate on every register. All 3 coils, all
54 named discrete inputs, all 14 holding registers and all 15 input registers
match the source on address, range, step, default and enum, and both
temperature formulas and both type-2 assignments are correct. The YAML is likewise correct
on every address, `input_type` and temperature encoding.

The real problems are in two places: the **board-family comparison table**
(one flat-wrong address, one material omission), the **climate entity's
temperature limits** (an out-of-range write path in cooling mode), and the
**provenance of `protocol_temperature_types.xlsx`**, which is not a MWH216
document at all.

| Rating | Count |
|---|---|
| Definite error | 5 |
| Ambiguous in the source | 4 |
| Cosmetic | 9 |

---

## Task 1 — `mwh216_register_map.md` vs. `protocol_MWH216_MWH298.xlsx`

### Verified correct — no discrepancy

Stated explicitly, since these were checked rather than skipped:

- **Coils (0x)**, `r5`–`r8`: addresses 0, 1, 2 and the 3~47 reserved block.
  Ranges, steps, defaults and enums all match.
- **Discrete inputs (1x)**, `r12`–`r70`: every one of addresses 0–17, the
  18~47 reserved block, E0–E9 (48–57), EA/Eb (58, 59), reserved 60, Ed (61),
  reserved 62–63, P0–P9 (64–73), PA (74), reserved 75–79, F0–F9 (80–89),
  FA/Fb (90, 91), reserved 92–95. The map reproduces this exactly, including
  the non-obvious gap at 60 between Eb and Ed.
- **Holding registers (4x)**, `r74`–`r100`: addresses 0–10, 17, 18, 25 and all
  three reserved blocks (11–16, 19–24, 26–32). Every range, step and default
  matches, and every derived °C figure in the map recomputes correctly under
  type 1 — spot-checking the awkward ones: HR 8 raw 26~60 → −17…0 °C default
  −7 ✓; HR 10 raw 76~120 → 8…30 °C default 13 ✓; HR 17 raw 40~100 → −10…20 °C
  default 3 ✓.
- **Input registers (3x)**, `r104`–`r119`: addresses 0–14 and the 15~29
  reserved block, including units (`%`, `Hz`, `V`, `0.1 A`, `RPM`).
- **Temperature formulas**, `[B122]`–`[B127]`: type 1 `(raw−60)/2`, type 2
  `raw/2`. Both transcribed correctly.
- **Type-2 assignment**: `[H110]` (IR 6, gas exhaust) and `[H116]` (IR 12,
  cooling plate) are the only two cells in the entire sheet reading
  "Temperature type 2". The map's claim that type 2 applies to exactly these
  two registers is confirmed.
- **Link settings**, `[A1]`: RS485, MODBUS-RTU, 1ST+8DATA+1SP, 9600, ≥60 ms
  between transactions, slave number 1. All correct.

### 1.1 — Holding register 1: "(Some models without Turbo)" dropped — **definite error (omission)**

`[H75]` reads in full:

> `0: Smart 1: Silence 3: Turbo (Some models without Turbo)`

The map (`mwh216_register_map.md` HR table) and `CLAUDE.md` both render this as
a flat `3 = Turbo`. The parenthetical is a hardware caveat: Turbo may not exist
on this unit. It matters because the YAML exposes Turbo as a selectable fan
mode and a script option, so writing 3 may be a no-op on some boards. Worth
carrying into both files.

### 1.2 — Whether address 0 is a permitted first address is inferred, not marked — **ambiguous in the source**

The map's read-length table asserts `1x → 0, 48`, `3x → 0, 3, 6, 9, 12`,
`4x → 0, 3, 6, 9, 12, 15, 18`.

In the sheet, the "Reads allowed as first address" marker is a column-A cell.
It appears on the **section header rows** (`[A4]`, `[A11]`, `[A73]`, `[A103]`)
and then on specific **data rows**: `[A31]` = addr 48; `[A77]`/`[A80]`/`[A83]`/
`[A86]`/`[A89]`/`[A92]` = 4x addrs 3, 6, 9, 12, 15, 18; `[A107]`/`[A110]`/
`[A113]`/`[A116]` = 3x addrs 3, 6, 9, 12. There are **no merged cells** in
column A anywhere in the register sections (checked via openpyxl), so nothing
structurally ties a header-row marker to the address-0 row below it. Address 0
is never marked on its own data row in any of the four tables.

Read strictly, address 0 is not a permitted first address — which is absurd,
since it would make coils 0–47, IR 0–2 (compressor speed, target frequency,
PFC voltage) and DI 0–47 unreachable. Two things resolve it in the map's
favour:

- The block arithmetic only closes if 0 is permitted: 3x blocks from
  0/3/6/9/12 at 3 registers each cover exactly 0–14, the full populated range.
  0x from 0 at 48 bits covers exactly 0–47, the full table. 1x from 0 and 48
  covers exactly 0–95.
- The sibling document states the equivalent rule in plain prose —
  `protocol_MWH381_MWH366_MWH367.xlsx` `[A1]` item 5: *"the first address of
  the read must be 0 or 48"*.

**The map's table is almost certainly right.** Flagging it because the claim is
an inference from layout, not a transcription, and the map presents it as if
directly stated.

### 1.3 — The 0x table is missing from the read-length table — **ambiguous in the source**

The map's "Permitted first addresses" table lists 1x, 3x and 4x but has no row
for 0x (coils), and `CLAUDE.md` and the YAML header comment both omit it too.
The sheet does carry the marker column on the 0x table (`[A4]`), but marks no
data row. Under the same reasoning as 1.2, 0x → 0 only, with a 48-bit count
covering the whole 0–47 table. Worth adding as a row for completeness.

### 1.4 — Holding register 25 is unreachable under the document's own read rule — **ambiguous in the source**

Permitted 4x first addresses stop at 18 (`[A92]`), and the count is fixed at 3
(`[A1]` item 5). The reachable blocks are therefore [0–2], [3–5], [6–8],
[9–11], [12–14], [15–17], [18–20] — ending at register 20.

**HR 25 (power-off restart memory, `r99`) falls outside every permitted
block.** There is no marker at 21 or 24 that would let a compliant read reach
it. The source contradicts itself here: it defines a register that its own read
rule cannot address.

Neither the map nor the YAML notes this. It has practical bite: the YAML reads
HR 25 as a sensor, and the block-read fallback advice in the YAML header
(`fairland_mwh216_modbus.yaml:27-37`) would not cover that register if the
constraint turns out to be enforced. Same applies to the scan script.

### 1.5 — Coil 2 is labelled "(Reserved)" in the source — **cosmetic**

`[C7]` reads `Restore factory values (Reserved)`; the map renders it
`**Restore factory values**`. The qualifier may mean the function is unimplemented
on shipping firmware. Doesn't change the correct handling — never write it —
but the source hedges and the map doesn't.

### 1.6 — "Value 2 is undefined" on HR 1 is an inference — **ambiguous in the source**

`[D75]` gives the range as `0~3` while `[H75]` enumerates only 0, 1 and 3. The
map and `CLAUDE.md` both state that 2 is undefined. That's a reasonable reading
of the gap, but the sheet nowhere says it. The alternative reading — that the
range is authoritative and 2 is an undocumented fourth mode — is not excluded
by anything in the document.

### 1.7 — Register names paraphrased — **cosmetic**

The map shortens several source names. None change meaning:

| Source | Map |
|---|---|
| `[C76]` Auto mode temperature range | Auto mode setpoint |
| `[C82]` Defrosting entry temperature (P3) | Defrost entry temp (P3) |
| `[C91]` Electronic expansion valve overheat level (Heating) | EEV superheat, heating |
| `[C81]` Compressor continuously running time between defrosting mode (P2) | Compressor run time between defrost (P2) |

Note the source's own typos are preserved in the sheet but silently fixed in
the map: `[C110]` "Gas exhuast temp", `[C117]` "EEV openning". Fixing them is
right; worth knowing if you ever grep the source.

### 1.8 — Coil table omits the Step column — **cosmetic**

The map's coil table has no Step column; `[F5]`, `[F6]`, `[F7]` are all 1. No
information lost in practice.

---

## Task 2 — `fairland_mwh216_modbus.yaml` vs. the spreadsheet

### Verified correct — no discrepancy

- **Every address exists and none is reserved.** 18 discrete inputs (0–17),
  36 fault bits (48–59, 61, 64–74, 80–91), 2 coils (0, 1), 15 input registers
  (0–14), 14 holding registers (0–10, 17, 18, 25). Cross-checked against the
  reserved blocks at `r30`, `r43`, `r45`, `r57`, `r70`, `r85`–`r90`, `r93`–`r98`,
  `r100`, `r119` — no entity lands in one.
- **`input_type` is correct on all 86 Modbus entities** (54 discrete inputs,
  15 input registers, 14 holding registers, 2 coils, 1 climate):
  `discrete_input` for 1x, `holding` for 4x, `input` for 3x,
  `write_type: coil` for 0x.
- **Temperature encodings are correct throughout.** Type 1 with
  `scale: 0.5, offset: -30` on IR 3, 4, 5, 7, 8, 9 and HR 2, 3, 4, 8, 10, 17,
  18. Type 2 with `scale: 0.5` and no offset on IR 6 and IR 12 only — matching
  `[H110]` and `[H116]` exactly. This is the error the whole map warns about
  and the YAML gets it right.
- **No stray scale or offset on non-temperature registers.** IR 0, 1, 2, 10,
  13, 14 and HR 0, 1, 5, 6, 7, 9, 25 are all bare. The one scaled
  non-temperature register, IR 11 `scale: 0.1`, is correct — `[E115]` gives the
  unit as `0.1 A`.
- **`temp_step: 1` is correct**: `[F77]` step 2 raw × 0.5 °C = 1.0 °C.
- **`hvac_mode_register` matches `[H74]`** exactly: auto 0, heat 1, cool 2.
- **`fan_mode_register` matches `[H75]`** exactly: 0, 1, 3, correctly skipping 2.
- **Coverage is complete.** Every non-reserved register in the document has an
  entity, with exactly one deliberate exception: **coil 2**, which is correctly
  absent. Do not add it.
- **The block-read fallback comment is arithmetically right.** `virtual_count: 47`
  from address 48 yields 48 bits (48–95); the comment's claims that `_3` is E3,
  `_16` is P0 and `_32` is F0 all check out.
- **Write scripts match the documented ranges.** Auto setpoint 12–40 °C ↔
  `[D76]` 84~140 ✓; cooling setpoint 12–30 °C ↔ `[D78]` 84~120 ✓; working mode
  0/1/3 ↔ `[H75]` ✓; pump mode 0–2 ↔ `[D79]` ✓. The raw conversion
  `temp × 2 + 60` matches `[B123]` ✓.

### 2.1 — Climate `min_temp`/`max_temp` are wrong for two of the three modes — **definite error**

`fairland_mwh216_modbus.yaml:930-932` sets `min_temp: 18`, `max_temp: 40`, with
the comment "Heating range from the doc: raw 96-140 = 18-40 °C". Against
`[D77]` that is correct **for heating**, and it's what the task asked me to
check — so on its own terms it passes.

The problem is that these keys are entity-global while the climate entity
writes to a *different register per mode* via
`target_temp_register: [2, 4, 4, 4, 3, 3, 3]`. The three registers have three
different documented ranges:

| Mode | Register | Source | Raw range | °C range | YAML allows |
|---|---|---|---|---|---|
| Heating | HR 3 | `[D77]` 96~140 | 96–140 | 18–40 | 18–40 ✓ |
| Auto | HR 2 | `[D76]` 84~140 | 84–140 | 12–40 | 18–40 ✗ |
| Cooling | HR 4 | `[D78]` 84~120 | 84–120 | 12–30 | 18–40 ✗ |

So in **cooling** mode the UI will happily command 40 °C, sending raw 140 to a
register the document caps at 120 — an out-of-range write to a mains-powered
compressor. And in auto and cooling, 12–17 °C is blocked despite being legal.

This is a write path, which is the category the project's own working rules
treat as unsafe, so I'd rate it the most important finding in the YAML. Note
the standalone scripts get this right (`:1073` uses 12–40 for auto, `:1094`
uses 12–30 for cooling) — it's only the climate entity that flattens them.

I have not changed it, per your instruction. Worth deciding whether to
constrain the climate entity to the intersection (18–30), drop cooling from
`target_temp_register`, or accept the gap and rely on the scripts.

### 2.2 — Fan-mode labels don't map intuitively — **cosmetic**

`:956-961` maps Smart → `state_fan_high`, Silence → `state_fan_low`, Turbo →
`state_fan_focus`. The register values are right, which is what matters, but
"Turbo" surfacing as *focus* while "Smart" surfaces as *high* will read oddly
in the UI. HA's fan-mode slots are a fixed vocabulary so some mismatch is
unavoidable; `focus` for Smart and `high` for Turbo would be the less
surprising assignment.

### 2.3 — No write script for the heating setpoint — **cosmetic**

There are scripts for the auto setpoint (HR 2), cooling setpoint (HR 4), working
mode (HR 1) and pump mode (HR 5), but none for HR 3 — the heating setpoint, and
the one that actually matters for the stated solar-dump use case. It is reachable
through the climate entity, so nothing is unreachable; the asymmetry is just
surprising given the others exist.

### 2.4 — Registers in the spreadsheet with no entity

Only **coil 2** (`[C7]`, restore factory values). **Not worth adding** — it is
the one register the project rules single out as never-write, and exposing it
in HA creates an accidental-click path to a factory reset. Its absence is
correct and deliberate.

Every other documented register is already represented.

---

## Task 3 — Board-family comparison

Verified `mwh216_register_map.md` "Differences between board families" against
both spreadsheets.

### Confirmed correct

| Claim | Verdict | Evidence |
|---|---|---|
| HR 1: MWH216 working mode 0 Smart / 1 Silence / 3 Turbo; MWH381 fan speed 0 Silence / 1 Smart / 2 Turbo | **Confirmed** | MWH216 `[H75]` vs MWH381 `[G78]`. The inversion is real, and Turbo differs too (3 vs 2). |
| Slave address: MWH216 fixed at 1; MWH381 settable via 4x 200, range 1–16 | **Confirmed** | MWH216 `[A1]` item 4 vs MWH381 `[A104]`, range `[C104]` 1~16 |
| Input registers 15+ Reserved on both | **Confirmed** | MWH216 `r119`, MWH381 `r123` |
| Extra holding registers on MWH381: fixed-speed ratio (P6), EEV manual mode and opening, intermediate frequency ratio, 2nd fan control, fan speed P19 | **Confirmed, all five** | `r88` (11, P6), `r96` (19, EEV mode), `r97`/`r98` (20/21, EEV opening), `r99` (22, intermediate freq), `r100` (23, 2nd fan), `r101` (24, P19) |
| 3x/4x read length: MWH216 fixed at 3; MWH381 max 8 | **Confirmed** | MWH216 `[A1]` item 5 vs MWH381 `[A1]` item 6 |
| 1x/0x read length: MWH216 fixed 48; MWH381 max 48, first address 0 or 48 | **Confirmed** | MWH216 `[A1]` item 5 vs MWH381 `[A1]` item 5 |

### 3.1 — Water pump status bit is at DI 20, not DI 31 — **definite error**

The map states:

> `| Water pump status bit | Not present | DI 31 |`

The source says address **20**:

```
MWH381 r30:  18       Reserved
MWH381 r31:  19       Reserved
MWH381 r32:  20       Water Pump Status    0~1    0: OFF 1: ON (Read only)
MWH381 r33:  21~47    Reserved
```

There is no register at DI 31 in either document — it sits inside MWH381's
`21~47` reserved block. Straight transcription error. Low blast radius (this
board doesn't have the bit at all, so nothing in the YAML depends on it), but
it is flatly wrong and would mislead anyone using this map against a MWH381.

### 3.2 — The 3x/4x *first-address* restriction is a family difference the table misses — **definite error (omission)**

The comparison table has a row for read *length* but not for read *first
address*, and the difference there is sharper than the length difference:

- **MWH216** restricts 3x/4x reads to first addresses 0, 3, 6, 9, 12 (+15, 18
  for 4x) — the marker cells at `[A77]`–`[A92]` and `[A107]`–`[A116]`.
- **MWH381** imposes **no first-address restriction at all** on 3x/4x. Its
  `[A1]` item 6 says only *"3x, 4x, maximum number of consecutive reads is 8"*,
  and the file has no marker column anywhere.

This is exactly the copy-between-families failure mode the section exists to
document: a polling scheme written for MWH381 (arbitrary start, up to 8
registers) is legal there and violates the MWH216 rule, with the documented
symptom being silently incorrect data rather than an error. Worth adding as a
row.

### 3.3 — Same-address, different-meaning registers

The user's specific concern. Full list, from a direct diff of the two 4x/1x
tables:

| Addr | MWH216 | MWH381 | Risk |
|---|---|---|---|
| 4x 1 | Working Mode (0 Smart, 1 Silence, 3 Turbo) `[H75]` | Fan speed (0 Silence, 1 Smart, 2 Turbo) `[G78]` | **Silent inversion** — already documented |
| 4x 0 | Function Selection, range `0~2` `[D74]` | Mode selection, range `0~3` `[C77]` | Same enum (0 Auto, 1 Heating, 2 Cooling); only the declared range differs |
| 4x 11 | Reserved `[C85]` | Fixed speed frequency ratio (P6) `[B88]` | Write lands on a reserved register |
| 4x 19–24 | Reserved `[C93]`–`[C98]` | EEV mode / EEV opening ×2 / intermediate freq / 2nd fan / P19 | Write lands on reserved registers |
| 1x 20 | Reserved (inside `18~47`) `[C30]` | Water Pump Status `[B32]` | Read returns nothing meaningful |

The map's table names the extra MWH381 registers but **gives no addresses**.
Adding the address column above would make the collision risk concrete rather
than something the reader has to reconstruct. Rated cosmetic since the
information is technically present.

### 3.4 — Smaller differences the table misses — **cosmetic**

- **OUT1–9 remark wording**: MWH216 `[H19]` "0: Closed 1: Output"; MWH381
  `[G19]` "0: Disconnected 1: Connected". Same semantics, different phrasing —
  but it means the MWH216 sheet uses one phrasing for DIN and another for OUT,
  while MWH381 uses one for both.
- **Input-register reserved block**: MWH216 `15~29` (`r119`), MWH381 `15~28`
  (`r123`). The map's table renders both as just "Reserved".
- **MWH381 slave-number firmware caveat**: `[G104]` ends with *"No slave number
  modification function for programs prior to 12 August 2022"*. Omitted from
  the map. Only affects the sibling family.
- **MWH381 IR 12 has no temperature type**: `r120` gives "Cooling plate temp"
  with an empty Remark, where MWH216 `[H116]` explicitly marks it type 2. So
  MWH216 is the *better* documented of the two here — worth knowing, since it
  means a MWH381-derived config has no guidance for that register.

---

## Cross-check — `protocol_temperature_types.xlsx`

### 4.1 — This is not a MWH216 document — **definite error** (in `CLAUDE.md`'s description of it)

`CLAUDE.md:29-31` describes this file as *"protocol document carrying the type
1 / type 2 conversion tables and the per-register 'Register Content' notes that
say which type each temperature uses"*, listed under "Source documents — these
are the authority". That framing is wrong: **it is the appendix to the
MWH381/366/367 document, not to MWH216.**

The proof is exact. Its 17 rows correspond one-to-one, in document order, to
the registers MWH381 annotates with a conversion formula:

| Sheet row | Content | MWH381 register |
|---|---|---|
| `r2`–`r4` | Auto / Heating / Cooling temp setting | 4x 2, 3, 4 |
| `r5`–`r6` | Defrost start (P3), quit (P5) | 4x 8, 10 |
| `r7`–`r8` | EEV overheat Heating / Cooling | 4x 17, 18 |
| `r9`–`r10` | **EEV opening setting Heating / Cooling** | **4x 20, 21** |
| `r11` | **Fan motor speed (P19)** | **4x 24** |
| `r12`–`r18` | Inlet, outlet, ambient, gas exhaust, outer coil, gas return, inner coil | 3x 3–9 |

Rows `r9`–`r11` are decisive: EEV opening setting (`Real openning = Setting
value * 2`) and fan motor speed P19 (`Real speed = Setting value * 9`) **do not
exist on MWH216** — those addresses are Reserved (`[C94]`, `[C98]`).
Conversely the sheet **omits cooling plate temp**, which MWH216 documents as
type 2 at `[H116]` and MWH381 leaves unannotated at `r120`. The sheet tracks
MWH381's annotation set precisely, including its gap.

Practical consequence: **`[H116]` in the MWH216 document is the sole source for
IR 12 being type 2.** That claim is currently treated as a "critical fact" in
`CLAUDE.md`, and it is correctly sourced — but not corroborated by this second
file, contrary to what the file description implies. If IR 12 reads ~30 °C low
on real hardware, there is no second document to fall back on.

(The description in `CLAUDE.md` is mine, from the earlier commit `08de62c` —
I inferred it from the sheet's content without checking it against the sibling
document. It needs correcting.)

### 4.2 — Where it overlaps, it agrees — no discrepancy

For every register present in both this sheet and the MWH216 document, the
temperature type matches: all type 1, except gas exhaust (AIN5) at `r15`, which
is type 2 — agreeing with MWH216 `[H110]`. Both formula blocks (`r21`–`r26`)
are character-identical to MWH216 `[B122]`–`[B127]`.

So nothing derived from it is wrong. The issue is provenance, not content.

---

## Addendum — upstream provenance check, 2026-08-12

Added after the audit above. The source spreadsheets were traced to their
origin: the Peraqua product page for the iQ Inver Silence Vertical 13.2 kW
(art. 7301269), which publishes **seven** documents for the unit. All seven
were pulled and examined.

### A.1 — The repo's three spreadsheets are byte-identical to upstream

SHA-256, repo copy against freshly downloaded original:

| Repo file | Upstream filename | SHA-256 | Match |
|---|---|---|---|
| `protocol_MWH216_MWH298.xlsx` | `Modbus_Wärmepumpe_MWH216 & MWH298.xlsx` | `8ea82a86…9a7a32` | ✓ |
| `protocol_MWH381_MWH366_MWH367.xlsx` | `Modbus_Wärmepumpe_MWH381 & MWH366 & MWH367.xlsx` | `7746de64…0186b868` | ✓ |
| `protocol_temperature_types.xlsx` | `Modbus_Wärmepumpe.xlsx` | `98171b64…b0e1339b` | ✓ |

So every finding above rests on unmodified source files. Nothing was corrupted
or edited in transit, and the cell references in this audit can be checked
against upstream directly.

### A.2 — Finding 4.1 explained, and reinforced

`protocol_temperature_types.xlsx` is upstream simply `Modbus_Wärmepumpe.xlsx`,
listed on the product page as just **"Modbus"** — no family in the name — and
positioned between the two family-specific files. That is very likely how it
came to be described as a MWH216 document in the first place. The content-based
proof in 4.1 that it belongs to the MWH366/367/381 family stands unchanged; the
naming now explains the error rather than excusing it.

### A.3 — IR 12 remains single-sourced, now tested rather than assumed

The remaining four documents (product manual, `iQnnect_Hardware_Wärmepumpe.pdf`,
and the DIN2 note in German and English) carry no register annotations. A string
search across all three spreadsheets confirms `Modbus_Wärmepumpe.xlsx` does not
contain "Cooling plate temp" at all, while both family documents do.

**Nothing in the complete upstream document set corroborates IR 12 being
temperature type 2.** The claim still rests solely on `[H116]`. This closes the
question of whether a second source exists: it does not.

### A.4 — The HR 1 inversion is corroborated outside the spreadsheets

`iQnnect_Hardware_Wärmepumpe.pdf` closes with a "Tips" page reading *"Version
der Platine prüfen, und Modus gegebenenfalls adaptieren"*, printing MWH216 &
MWH298 `Working Mode Selection` (0 Smart, 1 Silence, 3 Turbo) against MWH381 &
MWH366 & MWH367 `Fan speed selection` (0 Silence, 1 Smart, 2 Turbo). Independent
distributor-level support for the family difference in task 3. It also
reproduces the "(Some models without Turbo)" caveat from finding 1.1.

### A.5 — DIN2 is documented as the external enable contact

*External release via DIN2* (one page, DE and EN) states that DIN2 — discrete
input address 3 — is a main-board socket, factory-bridged with a jumper and so
closed on delivery; opening it blocks the pump and displays `OFF`, without
overwriting mode or parameters, behaving like the flow switch. It must be
switched potential-free. This is the only one of the eighteen generic I/O bits
with a documented function, but the source is a distributor wiring note rather
than the manufacturer Modbus document, so it is recorded in the register map as
a convention to confirm rather than a board fact.

### A.6 — Not recorded: OUT relay labels from a board photograph

`iQnnect_Hardware_Wärmepumpe.pdf` includes a photograph of a physical
MWH298-V2 board whose output relays carry stuck-on labels (water pump, 4-way
valve, condenser heating belt, and high/middle/low fan speeds). This was
deliberately **not** carried into the register map. Two reasons: several of the
relevant terminals are obscured in the photograph, so part of any mapping would
be inferred rather than read; and the unit photographed uses a three-speed AC
fan, whereas MWH216 is a DC inverter reporting fan RPM at IR 14 — a board wired
for fan-speed relays is not wired like this one. Open question 5 stays open, to
be settled by watching a run cycle.

---

## Suggested priority

1. **2.1** — climate `min_temp`/`max_temp` vs cooling range. Only finding with
   an unsafe write path.
2. **3.1** — DI 31 → DI 20. Flatly wrong.
3. **4.1** — correct the `CLAUDE.md` description of
   `protocol_temperature_types.xlsx`, and note that IR 12 type 2 is
   single-sourced.
4. **1.1** — carry "(Some models without Turbo)" into the map and YAML.
5. **3.2** — add the 3x/4x first-address row to the family table.
6. **1.4 / 1.3 / 1.2** — read-rule gaps: HR 25 unreachable, 0x row missing,
   address-0 inference.
7. Everything rated cosmetic.
