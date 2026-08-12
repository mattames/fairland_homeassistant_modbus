# Pool heat pump — Modbus

Modbus integration for an AES-badged (rebadged Fairland) pool heat pump with a
**MWH216** control board, reached over a Protoss PW11 RS485-to-WiFi gateway in
Modbus TCP ⇄ RTU conversion mode.

- `fairland_mwh216_modbus.yaml` — Home Assistant package, goes in `<config>/packages/`
- `mwh216_register_map.md` — register map transcribed from the manufacturer document
- `scan_heatpump.py` — read-only register dump, for bringing the unit up
- `CLAUDE.md` — hardware notes, board-family gotchas, and working rules

## Scanning the heat pump

`scan_heatpump.py` dumps every documented register once and prints it with its
documented meaning. Use it to confirm the gateway works and the register map
matches the board **before** pointing Home Assistant at it.

It is strictly read-only: it issues only FC02, FC03 and FC04, and there is no
code path in it that writes a coil or a register.

### Install

```sh
python3 -m venv venv
./venv/bin/pip install pymodbus
```

Verified against pymodbus 3.14. The slave-id keyword was renamed over time
(`unit` → `slave` → `device_id`), so the script detects which one the installed
version takes rather than pinning a release.

### Run

```sh
./venv/bin/python scan_heatpump.py <gateway-ip> [port]
```

Port defaults to 502. For example:

```sh
./venv/bin/python scan_heatpump.py 192.168.0.50
./venv/bin/python scan_heatpump.py 192.168.0.50 8899 --timeout 5
```

Options: `--slave` (default 1, fixed on this board), `--timeout` (default 3 s),
`--delay` (default 0.06 s, the documented minimum between transactions).

### What it reads

| Table | Addresses |
|---|---|
| Input registers (3x) | 0–14, plus 15–20 probed as a board check |
| Holding registers (4x) | 0–10, 17, 18, 25 |
| Discrete inputs (1x) | 0–17, 48–95 |

### Reading the output

**Start with the PRIORITY CHECK block.** Input register 12 (cooling plate) is
documented as type 2 by a single cell in a single document — the sibling-family
appendix doesn't list the register, and that family's own document leaves its
IR 12 unannotated. The scan prints a dedicated check comparing both readings
against ambient and says whether type 2 holds up. Settle this before trusting
anything else, because a wrong encoding here reads 30 °C low and still looks
plausible. One idle sample often can't decide it; re-run under load.

**Temperatures print both conversions.** This board uses two encodings, and
applying the wrong one reads 30 °C out while still looking plausible. Each
temperature line shows the raw value, type 1 `(raw−60)/2`, and type 2 `raw/2`,
with `<= type 1` / `<= type 2` marking the one the manufacturer document
specifies for that register. Only input 6 (gas exhaust) and input 12 (cooling
plate) are type 2.

**Input registers 15–20 are a board check.** They are documented Reserved on
MWH216, so `modbus exception 2 (illegal data address)` is the expected,
confirming answer and is not counted as a failure. A plausible value here means
this is probably not an MWH216 — several configs circulating online read input
registers 15+ as version and setpoint-limit registers, and those are for a
different board. The summary calls out any non-zero result.

**Individual read failures don't stop the scan.** Each failed register prints
its address and reason, and all of them are listed again in the summary.
Transport errors (timeouts, resets) are distinguished from proper Modbus
exception responses.

If the scan connects but values look stable and wrong, suspect the fixed
read-length rule: the document says reads must start at a permitted address
with a fixed count (48 bits for 1x, 3 registers for 3x/4x). This script reads
single registers, as the HA package and every working community config do.

### If it can't connect

The PW11's port in Modbus TCP mode is often not 502 — check the gateway's own
configuration page and pass the right port as the second argument.
