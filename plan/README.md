# NES on DE10-Lite: Implementation Plan

**Goal:** Build a hybrid NES emulator using LiteX (host) + custom NES core (guest) on DE10-Lite FPGA.

**Philosophy:** Build minimal working systems, then iterate. Don't solve problems you don't have yet.

## Quick Start Milestones

| Milestone | Target | Validation |
|:----------|:-------|:-----------|
| M1 | LiteX on real hardware | LED blinks, UART responds |
| M2 | SDRAM read/write | Upload 32KB, read back, verify |
| M3 | 6502 runs from BRAM | Infinite loop toggles LED |
| M4 | PPU outputs test pattern | VGA shows colored bars |
| M5 | NROM game boots | Donkey Kong title screen |
| M6 | MMC3 game boots | Super Mario Bros 3 title |

## Architecture Overview

```
LiteX SoC (100 MHz)          NES Core (21.48 MHz)
┌─────────────────┐          ┌─────────────────┐
│ VexRiscv CPU    │          │ 6502 CPU        │
│ UART            │◄────────►│ PPU → VGA       │
│ SDRAM           │  Bridge  │ APU stub        │
│ CSRs            │          │ Controller      │
└─────────────────┘          └─────────────────┘
```

## Implementation Phases

### Phase 1: LiteX on Hardware
**Goal:** Prove DE10-Lite works with LiteX

**Do:**
- Build and load default LiteX SoC
- Verify UART console works
- Verify SDRAM initializes

**Don't:**
- Add NES-specific CSRs yet
- Write ROM loader yet
- Worry about clock domains yet

**Done when:** `litex_term /dev/ttyUSB0` shows BIOS prompt

### Phase 2: Minimal NES Core
**Goal:** 6502 executes code, PPU shows something

**Do:**
- Get T65 6502 core (external)
- Get PPU core from iandailis/NES-FPGA
- Wire to BRAM only (no SDRAM bridge)
- Use NROM (mapper 0) - no bank switching

**Don't:**
- Implement MMC3 yet
- Build SDRAM bridge yet
- Optimize anything

**Done when:** Donkey Kong or similar NROM game shows title screen

### Phase 3: SDRAM Integration
**Goal:** Load ROMs larger than BRAM

**Do:**
- Build simple Wishbone bridge
- Load PRG-ROM to SDRAM
- Keep CHR-ROM in BRAM (≤8KB for NROM)

**Don't:**
- Implement CHR cache bank-swapping
- Optimize latency

**Done when:** Can load and run any NROM game via UART

### Phase 4: MMC3 Support
**Goal:** Run Super Mario Bros 3

**Do:**
- Port MMC3 mapper
- Add PRG bank switching
- Add CHR bank switching (still BRAM cache)
- Add scanline counter IRQ

**Done when:** SMB3 boots and is playable

## RTL Modules (Existing)

In [`rtl/`](../rtl/):
- `nes_clk_gen.v` - Clock enables (3:1 PPU/CPU)
- `nes_addr_decode.v` - Address decoder
- `nes_internal_ram.v` - 2KB RAM
- `nes_dma_controller.v` - OAM DMA
- `nes_apu_stub.v` - Frame counter IRQ
- `nes_controller.v` - Shift register
- `nametable_mirror.v` - H/V mirroring
- `cdc_multibit.v` - CDC utilities

## External Components Needed

| Component | Source | Priority |
|:----------|:-------|:---------|
| T65 6502 | github.com/fpganes/T65 | Phase 2 |
| PPU | github.com/iandailis/NES-FPGA | Phase 2 |
| MMC3 | github.com/MiSTer-devel/NES_MiSTer | Phase 4 |

## Current Status

### Working
- [x] LiteX SoC simulation
- [x] Basic RTL modules written

### Next Action
```bash
# Build LiteX for real DE10-Lite hardware
python3 -m litex_boards.targets.terasic_de10lite --build --load
```

## Deferred Decisions

These will be solved when encountered, not planned in advance:

- CDC details between clock domains
- CHR cache for >32KB games
- SDRAM arbitration edge cases
- PRG-ROM latency optimization
- Audio output (APU beyond frame counter)
