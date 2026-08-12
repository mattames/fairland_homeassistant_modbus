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

The I/O bits are generic on this board — the document gives no indication of
what DIN1–5 and OUT1–9 are physically wired to. Identify them by watching the
states through a run cycle.

## Holding registers (4x) — FC03 read / FC06 write

| Addr | Content | Range | Step | Default | Notes |
|---|---|---|---|---|---|
| 0 | Function selection | 0–2 | 1 | 1 | 0 = Auto, 1 = Heating, 2 = Cooling |
| 1 | Working mode selection | 0–3 | 1 | 1 | 0 = Smart, 1 = Silence, 3 = Turbo. **2 undefined** |
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

## Differences between board families

Worth knowing, because configs get copied between them and the failures are
silent rather than loud.

| | MWH216 / MWH298 | MWH366 / MWH367 / MWH381 |
|---|---|---|
| HR 1 semantics | Working mode: 0 Smart, 1 Silence, 3 Turbo | Fan speed: 0 Silence, 1 Smart, 2 Turbo |
| Slave address | Fixed at 1 | Settable via 4x register 200, range 1–16 |
| Water pump status bit | Not present | DI 31 |
| Input registers 15+ | Reserved | Reserved |
| Extra holding registers | — | Fixed-speed ratio (P6), EEV manual mode and opening, intermediate frequency ratio, 2nd fan control, fan speed P19 |
| 3x/4x read length | Fixed at 3 | Max 8 |
| 1x/0x read length | Fixed at 48 | Max 48, first address 0 or 48 |

The two families invert the meaning of 0 and 1 in the mode register. A config
copied across would select Silence when asking for Smart, and vice versa —
with no error.

## Sources

- Fairland *Modbus Wärmepumpe MWH216 & MWH298* (manufacturer document)
- Fairland *Modbus Wärmepumpe MWH381 & MWH366 & MWH367* (manufacturer document)
- <https://github.com/spdr870/fairland_iphcr45_modbus>
- <https://github.com/rstcologne/ESP-Home-Fairland-Heatpump>
- <https://community.home-assistant.io/t/fairland-heat-pump-to-ha/304871>
- <https://community.home-assistant.io/t/fairland-pool-warmepumpe-heatpump-ixcr66-modbus-register/711658>
