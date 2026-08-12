#!/usr/bin/env python3
"""Read-only Modbus TCP dump of a Fairland MWH216 pool heat pump control board.

This script NEVER writes. It issues only FC02 (read discrete inputs), FC03
(read holding registers) and FC04 (read input registers). There is no code
path here that can write a coil or a register — see the working rules in
CLAUDE.md: reads are safe, writes are not, and coil 2 is "restore factory
values".

Register semantics come from mwh216_register_map.md, which is transcribed from
the manufacturer document for the MWH216 / MWH298 boards. Do not apply this
map to the MWH366 / MWH367 / MWH381 family — they differ in ways that fail
silently.

Usage:
    python3 scan_heatpump.py <host> [port]
"""

from __future__ import annotations

import argparse
import inspect
import sys
import time

try:
    from pymodbus.client import ModbusTcpClient
except ImportError:
    sys.exit(
        "pymodbus is not installed.\n"
        "    python3 -m venv venv && ./venv/bin/pip install pymodbus"
    )

# --------------------------------------------------------------------------
# Register map — from mwh216_register_map.md
# --------------------------------------------------------------------------

# Temperature encodings. Type 2 applies to exactly two registers on this board:
# input register 6 (gas exhaust) and input register 12 (cooling plate).
TYPE_1 = 1  # degC = (raw - 60) / 2
TYPE_2 = 2  # degC = raw / 2


def type_1(raw: int) -> float:
    return (raw - 60) / 2


def type_2(raw: int) -> float:
    return raw / 2


# addr: (name, unit, temp_type, scale, enum)
#   temp_type  None unless the register is a temperature
#   scale      display multiplier for non-temperature registers
#   enum       {raw: meaning} for discrete-valued registers
INPUT_REGISTERS = {
    0: ("Compressor running speed percentage", "%", None, 1, None),
    1: ("Compressor target frequency", "Hz", None, 1, None),
    2: ("PFC voltage", "V", None, 1, None),
    3: ("Water inlet temp (AIN1)", None, TYPE_1, 1, None),
    4: ("Water outlet temp (AIN2)", None, TYPE_1, 1, None),
    5: ("Ambient temp (AIN7)", None, TYPE_1, 1, None),
    6: ("Gas exhaust temp (AIN5)", None, TYPE_2, 1, None),
    7: ("Outer coil pipe temp, evaporator (AIN3)", None, TYPE_1, 1, None),
    8: ("Gas return temp (AIN6)", None, TYPE_1, 1, None),
    9: ("Inner coil pipe temp, titanium HX (AIN4)", None, TYPE_1, 1, None),
    10: ("Compressor frequency", "Hz", None, 1, None),
    11: ("Compressor current", "A", None, 0.1, None),
    12: ("Cooling plate temp", None, TYPE_2, 1, None),
    13: ("EEV opening", "", None, 1, None),
    14: ("DC fan motor speed", "RPM", None, 1, None),
}

# Documented as Reserved on MWH216. Probed to confirm the board really is a
# MWH216 and not a sibling that exposes version / setpoint-limit registers here.
RESERVED_INPUT_PROBE = range(15, 21)

HOLDING_REGISTERS = {
    0: ("Function selection", None, None, 1,
        {0: "Auto", 1: "Heating", 2: "Cooling"}),
    1: ("Working mode selection", None, None, 1,
        {0: "Smart", 1: "Silence", 2: "UNDEFINED on MWH216", 3: "Turbo"}),
    2: ("Auto mode setpoint", None, TYPE_1, 1, None),
    3: ("Heating mode setpoint", None, TYPE_1, 1, None),
    4: ("Cooling mode setpoint", None, TYPE_1, 1, None),
    5: ("Water pump working mode (P0)", None, None, 1,
        {0: "continuous", 1: "water temp", 2: "time + water temp"}),
    6: ("Water pump run time (P1)", "min", None, 1, None),
    7: ("Compressor run time between defrost (P2)", "min", None, 1, None),
    8: ("Defrost entry temp (P3)", None, TYPE_1, 1, None),
    9: ("Max defrost run time (P4)", "min", None, 1, None),
    10: ("Defrost exit temp (P5)", None, TYPE_1, 1, None),
    17: ("EEV superheat, heating", None, TYPE_1, 1, None),
    18: ("EEV superheat, cooling", None, TYPE_1, 1, None),
    25: ("Power-off restart memory", None, None, 1,
         {0: "stay off", 1: "restore prior state"}),
}


def discrete_input_name(addr: int) -> str:
    """Documented name for a discrete input, per the register map.

    Addresses 2-17 are generic on this board: the document does not say what
    DIN1-5 and OUT1-9 are physically wired to. Named versions found in other
    Fairland configs are from sibling boards and do not apply here.
    """
    if addr == 0:
        return "ON/OFF (0 = off, 1 = on)"
    if addr == 1:
        return "Defrosting"
    if 2 <= addr <= 6:
        return f"DIN{addr - 1} (0 = disconnected, 1 = connected)"
    if 7 <= addr <= 15:
        return f"OUT{addr - 6} (0 = closed, 1 = output)"
    if addr == 16:
        return "Malfunction / protection indicator"
    if addr == 17:
        return "Compressor running demand"
    if 18 <= addr <= 47:
        return "Reserved"
    if 48 <= addr <= 57:
        return f"E{addr - 48} (fault flag)"
    if addr == 58:
        return "EA (fault flag)"
    if addr == 59:
        return "Eb (fault flag)"
    if addr == 61:
        return "Ed (fault flag)"
    if 64 <= addr <= 73:
        return f"P{addr - 64} (protection flag)"
    if addr == 74:
        return "PA (protection flag)"
    if 80 <= addr <= 89:
        return f"F{addr - 80} (flag)"
    if addr == 90:
        return "FA (flag)"
    if addr == 91:
        return "Fb (flag)"
    return "Reserved"


DISCRETE_INPUT_RANGES = (range(0, 18), range(48, 96))

# --------------------------------------------------------------------------
# Modbus plumbing
# --------------------------------------------------------------------------


class ReadFailed(Exception):
    """A single register read failed. Reported, then the scan continues.

    `code` is the Modbus exception code when the slave answered with a proper
    exception response, and None when the read failed at the transport layer
    (timeout, reset, decode error). The distinction matters for the Reserved
    probe: an exception response is the expected, board-confirming answer,
    whereas a dropped connection says nothing about the register.
    """

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


def slave_kwarg(client) -> str:
    """Name of the slave-id keyword for the installed pymodbus.

    pymodbus renamed this over time: `unit` -> `slave` -> `device_id`
    (3.9 deprecated `slave`, 4.0 removed it). Detect rather than pin.
    """
    params = inspect.signature(client.read_input_registers).parameters
    for name in ("device_id", "slave", "unit"):
        if name in params:
            return name
    raise RuntimeError(
        "Cannot determine the slave-id keyword for this pymodbus version"
    )


def read_one(client, fn_name: str, addr: int, kwarg: str, slave: int, delay: float):
    """Read a single register or bit. Raises ReadFailed on any error.

    Reads are issued one at a time. The manufacturer document specifies a fixed
    read length (48 bits for 1x, 3 registers for 3x/4x) starting at a permitted
    address, but every working community config reads singles, as does the HA
    package in this repo. If values come back stable but wrong, that constraint
    is the first thing to suspect.
    """
    fn = getattr(client, fn_name)
    try:
        rr = fn(addr, count=1, **{kwarg: slave})
    except Exception as exc:  # transport dropped, timeout, decode error
        raise ReadFailed(f"{type(exc).__name__}: {exc}") from exc
    finally:
        # The document asks for a minimum 60 ms between transactions.
        time.sleep(delay)

    if rr is None:
        raise ReadFailed("no response")
    if getattr(rr, "isError", lambda: False)():
        code = getattr(rr, "exception_code", None)
        if code is not None:
            raise ReadFailed(
                f"modbus exception {code} ({exception_name(code)})", code=code
            )
        raise ReadFailed(str(rr))

    values = getattr(rr, "registers", None)
    if values is None:
        values = getattr(rr, "bits", None)
    if not values:
        raise ReadFailed("empty response")
    return values[0]


def exception_name(code: int) -> str:
    return {
        1: "illegal function",
        2: "illegal data address",
        3: "illegal data value",
        4: "slave device failure",
        6: "slave device busy",
        11: "gateway target device failed to respond",
    }.get(code, "unknown")


def as_signed(raw: int) -> int:
    return raw - 0x10000 if raw > 0x7FFF else raw


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def heading(text: str) -> None:
    print()
    print(text)
    print("-" * len(text))


def format_register(addr: int, raw: int, spec) -> str:
    """One output line for a register.

    Temperatures print raw plus BOTH conversions, with the documented one
    marked, because applying type 1 to a type 2 register reads 30 degC low and
    still looks plausible.
    """
    name, unit, temp_type, scale, enum = spec
    prefix = f"  {addr:>3}  raw={raw:>6}"

    if temp_type is not None:
        t1 = f"t1={type_1(raw):>7.1f} C"
        t2 = f"t2={type_2(raw):>7.1f} C"
        if temp_type == TYPE_1:
            body = f"{t1} <= type 1   {t2}"
        else:
            body = f"{t1}   {t2} <= type 2"
        line = f"{prefix}  {body}  {name}"
    elif enum is not None:
        meaning = enum.get(raw, "NOT IN DOCUMENTED RANGE")
        line = f"{prefix}  {meaning:<34}  {name}"
    else:
        value = raw * scale
        shown = f"{value:g} {unit}".strip() if unit is not None else f"{value:g}"
        line = f"{prefix}  {shown:<34}  {name}"

    if raw > 0x7FFF:
        line += f"  [signed int16: {as_signed(raw)}]"
    return line


def scan_registers(client, fn_name, table, kwarg, slave, delay, failures):
    for addr in sorted(table):
        try:
            raw = read_one(client, fn_name, addr, kwarg, slave, delay)
        except ReadFailed as exc:
            print(f"  {addr:>3}  FAILED: {exc}")
            failures.append((fn_name, addr, str(exc)))
            continue
        print(format_register(addr, raw, table[addr]))


def scan_reserved(client, kwarg, slave, delay, failures):
    """Probe registers documented as Reserved and report what comes back.

    An 'illegal data address' exception is the expected, board-confirming
    result. A plausible-looking value here means this is not an MWH216 and the
    rest of this map should be treated as suspect.
    """
    surprises = []
    for addr in RESERVED_INPUT_PROBE:
        try:
            raw = read_one(client, "read_input_registers", addr, kwarg, slave, delay)
        except ReadFailed as exc:
            if exc.code is not None:
                # The slave answered with an exception response. That is the
                # expected result here, not a failure worth reporting.
                print(f"  {addr:>3}  {exc}   (expected — documented Reserved)")
            else:
                # Transport-level failure. Says nothing about the register.
                print(f"  {addr:>3}  READ FAILED: {exc}   (not a Reserved result)")
                failures.append(("read_input_registers[reserved]", addr, str(exc)))
            continue
        note = "returned 0 — consistent with unused" if raw == 0 else "NON-ZERO"
        print(f"  {addr:>3}  raw={raw:>6}  {note}")
        if raw != 0:
            surprises.append(addr)
    return surprises


def scan_discrete(client, kwarg, slave, delay, failures):
    for rng in DISCRETE_INPUT_RANGES:
        for addr in rng:
            try:
                raw = read_one(client, "read_discrete_inputs", addr, kwarg, slave, delay)
            except ReadFailed as exc:
                print(f"  {addr:>3}  FAILED: {exc}")
                failures.append(("read_discrete_inputs", addr, str(exc)))
                continue
            bit = 1 if raw else 0
            print(f"  {addr:>3}  {bit}  {discrete_input_name(addr)}")


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Modbus TCP dump of a Fairland MWH216 board. "
                    "This script never writes.",
    )
    parser.add_argument("host", help="Protoss PW11 gateway IP address")
    parser.add_argument("port", nargs="?", type=int, default=502,
                        help="Modbus TCP port (default: 502)")
    parser.add_argument("--slave", type=int, default=1,
                        help="Slave address (default: 1, fixed on MWH216)")
    parser.add_argument("--timeout", type=float, default=3.0,
                        help="Per-transaction timeout in seconds (default: 3)")
    parser.add_argument("--delay", type=float, default=0.06,
                        help="Delay between transactions in seconds "
                             "(default: 0.06, the documented minimum)")
    args = parser.parse_args()

    print(f"Fairland MWH216 read-only scan — {args.host}:{args.port} slave {args.slave}")
    print("No register is written by this script.")

    client = ModbusTcpClient(args.host, port=args.port, timeout=args.timeout)
    try:
        connected = client.connect()
    except Exception as exc:
        print(f"\nConnection failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if not connected:
        print(
            f"\nCould not connect to {args.host}:{args.port}.\n"
            "Check the gateway is reachable, and that it is in Modbus TCP <-> RTU\n"
            "conversion mode on this port (the PW11's socket port is often not 502).",
            file=sys.stderr,
        )
        return 1

    failures: list[tuple[str, int, str]] = []
    surprises: list[int] = []
    try:
        kwarg = slave_kwarg(client)

        heading("Input registers 0-14 (3x, FC04)")
        scan_registers(client, "read_input_registers", INPUT_REGISTERS,
                       kwarg, args.slave, args.delay, failures)

        heading("Input registers 15-20 — documented Reserved on MWH216")
        surprises = scan_reserved(client, kwarg, args.slave, args.delay, failures)

        heading("Holding registers (4x, FC03) — read only, not written")
        scan_registers(client, "read_holding_registers", HOLDING_REGISTERS,
                       kwarg, args.slave, args.delay, failures)

        heading("Discrete inputs 0-17 and 48-95 (1x, FC02)")
        scan_discrete(client, kwarg, args.slave, args.delay, failures)
    finally:
        client.close()

    heading("Summary")
    if surprises:
        print(f"  Input registers {surprises} returned non-zero, but are documented")
        print("  Reserved on MWH216. Either this is a different board, or the")
        print("  gateway is echoing stale data. Re-check before trusting this map.")
    else:
        print("  Reserved input registers behaved as documented.")

    if failures:
        print(f"  {len(failures)} read(s) failed:")
        for fn_name, addr, reason in failures:
            print(f"    {fn_name} {addr}: {reason}")
    else:
        print("  All reads succeeded.")

    print()
    print("  Sanity checks before trusting these values:")
    print("   - gas exhaust (IR 6) should read 60-100 C when running, not ~30 C low")
    print("   - heating setpoint (HR 3) should match the unit's own display")
    print("   - if values are stable but wrong, suspect the fixed read-length rule")
    return 0


if __name__ == "__main__":
    sys.exit(main())
