# Phase 1: LiteX on Hardware

**Goal:** Get LiteX running on real DE10-Lite, not just simulation.

## Success Criteria

- [ ] `litex_term` shows BIOS prompt
- [ ] Can type commands in UART console
- [ ] `mem_test` passes (SDRAM works)

## Steps

### 1. Build for Hardware

```bash
cd /home/cg/risc-v_on_de10-lite/nes
python3 -m litex_boards.targets.terasic_de10lite \
    --build \
    --cpu-type=vexriscv \
    --with-uart \
    --uart-baudrate=115200
```

### 2. Load to FPGA

```bash
# Using Quartus Programmer or:
python3 -m litex_boards.targets.terasic_de10lite --load
```

### 3. Connect UART

```bash
litex_term /dev/ttyUSB0 --speed 115200
```

You should see:
```
LiteX BIOS
(c) Copyright 2012-2024 Enjoy-Digital

BIOS> 
```

### 4. Test SDRAM

```
BIOS> mem_test 0x40000000 0x100000
```

## Troubleshooting

**No UART output:**
- Check USB cable
- Check `/dev/ttyUSB*` permissions
- Try different baud rate

**SDRAM test fails:**
- Check SDRAM module parameter matches DE10-Lite (IS42S16320)
- Try `--sdram-rate=1:1` if timing fails

## What NOT To Do Yet

- Don't add custom CSRs
- Don't write firmware
- Don't implement ROM loader
- Don't connect NES core

## Next Phase

Once BIOS works → Phase 2: Get 6502 + PPU running from BRAM

---

## Reference (Archived Details)

The detailed SDRAM memory map, CSR definitions, and boot sequence specs
are preserved below for when they're needed.

<details>
<summary>Click to expand archived specifications</summary>
