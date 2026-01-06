# Phase 1: LiteX on Hardware

**Goal:** Get LiteX running on real DE10-Lite, not just simulation.

**Status:** ✅ PARTIAL SUCCESS (2026-01-02)
- UART working
- BIOS responding
- SDRAM not working (deferred)

## Success Criteria

- [x] `litex_term` shows BIOS prompt
- [x] Can type commands in UART console
- [ ] `mem_test` passes (SDRAM works) — **DEFERRED**

## Hardware Setup

**UART Connection (CP2102 USB-Serial):**
- CP2102 RX → DE10-Lite GPIO[0] (pin V10 on JP1)
- CP2102 TX → DE10-Lite GPIO[1] (pin W10 on JP1)
- GND → GND

**Programming:**
- USB-Blaster connected via onboard USB

## Steps

### 1. Build for Hardware

```bash
cd /home/cg/risc-v_on_de10-lite/nes
python3 -m litex_boards.targets.terasic_de10lite \
    --build \
    --cpu-type=vexriscv \
    --uart-baudrate=115200
```

Note: `--with-uart` is not needed (UART enabled by default).

### 2. Load to FPGA

```bash
python3 -m litex_boards.targets.terasic_de10lite --load
```

Output:
```
Info (209007): Configuration succeeded -- 1 device(s) configured
```

### 3. Connect UART

```bash
litex_term /dev/ttyUSB0 --speed 115200
```

Or test with Python:
```python
import serial
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2)
ser.write(b'\r\n')
print(ser.read(1024))  # Should show "litex>"
```

**Result:** ✅ BIOS prompt responds:
```
litex> help
LiteX BIOS, available commands:
leds, flush_l2_cache, flush_cpu_dcache, crc, ident, help
serialboot, reboot, boot
mem_cmp, mem_speed, mem_test, mem_copy, mem_write, mem_read, mem_list
sdram_mr_write, sdram_test, sdram_init
```

### 4. Test SDRAM

```
litex> sdram_test
```

**Result:** ❌ FAILED — bus errors 256/256, data errors 524288/524288

This is a known timing issue with the GENSDRPHY on MAX10. Deferred to later.

## Known Issues

### SDRAM Not Working
- All bus operations fail (256/256 bus errors)
- **Attempts to fix (Failed):**
    - Phase shifts: 0°, 90°, 180°, 270°
    - Clock frequency: 50MHz, 40MHz, 25MHz
    - Timings: Relaxed tRP, tRCD, tWR to 40ns (vs 20ns default)
- Root cause: Likely a deep PHY initialization or pin drive strength issue specific to this board revision.
- **Workaround for Phase 2:** Use BRAM only. NROM games (Super Mario Bros, Donkey Kong) fit within the FPGA's internal memory (M9K blocks).

## What Works

| Component | Status |
|:----------|:-------|
| VexRiscv CPU | ✅ Running |
| UART | ✅ 115200 baud via GPIO[0]/GPIO[1] |
| BIOS | ✅ Interactive prompt |
| LEDs | ✅ Accessible via `leds` command |
| SDRAM | ❌ Bus errors (deferred) |

## Next Phase

Proceed to **Phase 2** using BRAM only:
- Get T65 6502 core
- Get PPU core
- Wire to BRAM (no SDRAM bridge needed for NROM games)

---

## Reference (Archived Details)

The detailed SDRAM memory map, CSR definitions, and boot sequence specs
are preserved below for when they're needed.

<details>
<summary>Click to expand archived specifications</summary>
