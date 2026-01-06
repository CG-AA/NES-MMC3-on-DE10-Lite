# NES on DE10-Lite: Implementation Plan

**Goal:** Build a hybrid NES emulator using LiteX (host) + custom NES core (guest) on DE10-Lite FPGA.

**Philosophy:** Build minimal working systems, then iterate. Don't solve problems you don't have yet.

**Current Status:** Phase 3 Complete ✅ - BRAM-only approach for NROM games

---

## Quick Start Milestones

| Milestone | Target | Status |
|:----------|:-------|:-------|
| M1 | LiteX on real hardware | ✅ UART + SDRAM working |
| M2 | SDRAM read/write | ⚠️ **Individual OK, bulk deferred** |
| M3 | 6502 runs from BRAM | ✅ LED counter working |
| M4 | PPU outputs test pattern | ✅ VGA test pattern |
| M5 | NROM game boots | ✅ **Donkey Kong title screen!** |
| M6 | Game switching tool | ✅ **switch_game.py** |
| M7 | Keyboard controller | ⏳ **In Progress** |
| M8 | MMC3 game boots | ⏳ Phase 4 (needs SDRAM) |

---

## Latest Update (2026-01-06)

### Phase 3 Complete: BRAM-Only Approach ✅

**Decision:** Use BRAM for NROM games instead of SDRAM.

| Approach | Pros | Cons |
|----------|------|------|
| **BRAM** | 100% reliable, no bus contention, already working | 40KB limit, recompile per game |
| SDRAM | 64MB capacity, runtime loading | Bulk uploads unreliable via UART |

**FPGA Resources:**
- Available BRAM: 204 KB
- Used (SoC + NES): ~100 KB  
- Remaining: **104 KB** (NROM needs 40KB) ✅

### Tools Created

| Tool | Purpose |
|------|---------|
| `scripts/tools/extract_nes_rom.py` | Convert .nes → .hex files |
| `scripts/tools/switch_game.py` | Switch games (extract + update RTL + compile) |
| `scripts/tools/keyboard_controller.py` | Laptop keyboard → NES controller via UART |

### Usage
```bash
# List available games
python scripts/tools/switch_game.py --list

# Switch to a different game (extract only)
python scripts/tools/switch_game.py some_game.nes --extract-only

# Full switch with recompile and program
python scripts/tools/switch_game.py some_game.nes --compile --program

# Play with keyboard (requires controller CSR integration)
python scripts/tools/keyboard_controller.py --port /dev/ttyUSB0
```

### SDRAM Status (Deferred to Phase 4)
SDRAM hardware is fixed (phase 270°, safe timings). Bulk uploads fail due to UART buffer overrun.
Future options: Etherbone, custom loader, or SD card.

---

## Architecture Overview

### Current (Phase 2/3 - BRAM Only)
```
┌─────────────────────────────────────────┐
│              DE10-Lite                   │
│  ┌─────────────────────────────────────┐│
│  │         NES Core (50 MHz)           ││
│  │  ┌─────────┐    ┌─────────────────┐ ││
│  │  │ T65 CPU │◄──►│ PRG BRAM (32KB) │ ││
│  │  └────┬────┘    └─────────────────┘ ││
│  │       │                              ││
│  │  ┌────▼────┐    ┌─────────────────┐ ││
│  │  │   PPU   │◄──►│ CHR BRAM (8KB)  │ ││
│  │  │VGA-sync │    │ VRAM (2KB)      │ ││
│  │  └────┬────┘    └─────────────────┘ ││
│  │       │                              ││
│  │  ┌────▼────┐                        ││
│  │  │   VGA   │──────────► Monitor     ││
│  │  │640x480  │                        ││
│  │  └─────────┘                        ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

### Target (Phase 4 - SDRAM for large games)
```
LiteX SoC (100 MHz)          NES Core (50 MHz)
┌─────────────────┐          ┌─────────────────┐
│ VexRiscv CPU    │          │ T65 6502 CPU    │
│ UART            │◄────────►│ PPU → VGA       │
│ SDRAM           │  Bridge  │ APU stub        │
│ CSRs            │          │ Controller      │
└─────────────────┘          └─────────────────┘
```

---

## Implementation Phases

### Phase 1: LiteX on Hardware ⚠️ Partial
**Goal:** Prove DE10-Lite works with LiteX

| Task | Status |
|:-----|:-------|
| Build LiteX SoC | ✅ Compiles |
| UART console | ✅ Working |
| SDRAM init | ❌ Fails (256/256 errors) |

**Next:** Debug SDRAM PHY timing for IS42S16320D

### Phase 2: Minimal NES Core ✅ COMPLETE
**Goal:** 6502 executes code, PPU shows graphics

| Task | Status |
|:-----|:-------|
| T65 6502 integrated | ✅ Working |
| PPU tile rendering | ✅ Working |
| VGA output | ✅ 640x480 @ 60Hz |
| Donkey Kong title | ✅ **WORKING!** |

**Completed:** 2026-01-05

### Phase 3: ROM Loading ✅ COMPLETE
**Goal:** Support multiple NROM games with easy switching

| Task | Status |
|:-----|:-------|
| BRAM capacity analysis | ✅ 40KB NROM fits |
| ROM extraction tool | ✅ extract_nes_rom.py |
| Game switching script | ✅ switch_game.py |
| RTL path updates | ✅ rom_data/ prefix |

**Decision:** BRAM-only for NROM games. SDRAM deferred to Phase 4.

**Completed:** 2026-01-06

**See:** [03-memory-bridge.md](03-memory-bridge.md)

### Phase 4: MMC3 Support ⏳ NEXT
**Goal:** Run Super Mario Bros 3

| Task | Status |
|:-----|:-------|
| Fix SDRAM bulk uploads | ⏳ TODO (Etherbone?) |
| MMC3 mapper | ⏳ TODO |
| PRG bank switching | ⏳ TODO |
| CHR bank switching | ⏳ TODO |
| Scanline counter IRQ | ⏳ TODO |

**See:** [04-integration.md](04-integration.md)

---

## Project Structure

```
nes/
├── rtl/                    # Verilog/VHDL source
│   ├── nes_top_ppu.v       # Main top-level (ACTIVE)
│   ├── nes_ppu_vga_sync.v  # VGA-synchronized PPU
│   ├── nes_prg_bram.v      # 32KB PRG-ROM
│   ├── nes_chr_multiport.v # 8KB CHR-ROM (4-port)
│   ├── nes_vram_dp.v       # 2KB nametable (dual-port)
│   ├── vga_timing.v        # VGA timing generator
│   ├── nes_palette.v       # Color palette ROM
│   ├── hex_display.v       # 7-segment driver
│   ├── NES-FPGA/           # External: T65 CPU
│   └── NES_MiSTer/         # External: Reference
├── scripts/
│   ├── tools/
│   │   ├── switch_game.py      # Game switching automation
│   │   ├── extract_nes_rom.py  # ROM → .hex conversion
│   │   └── bios_manager.py     # LiteX BIOS utilities
│   ├── tests/                  # SDRAM test scripts
│   └── generators/             # Test ROM generators
├── rom_data/               # Extracted .hex ROM files
│   ├── donkey_kong_prg.hex
│   └── donkey_kong_chr.hex
├── roms/                   # Original .nes files
├── plan/                   # Documentation
│   ├── README.md           # This file
│   ├── 01-litex-setup.md   # Phase 1 details
│   ├── 02-components.md    # Phase 2 details
│   ├── 03-memory-bridge.md # Phase 3 details
│   └── 04-integration.md   # Phase 4 details
├── quartus_nes_vga/        # Quartus project files
├── build/                  # LiteX build outputs
├── litedram_modules.py     # SDRAM timing definitions
└── terasic_de10lite_custom.py  # LiteX target
```

---

## Build & Run

```bash
# Switch to a different game
python3 scripts/tools/switch_game.py game.nes --compile --program

# Or manually:
# 1. Extract ROM
python3 scripts/tools/extract_nes_rom.py roms/game.nes

# 2. Update RTL (automatic with switch_game.py)
# Edit INIT_FILE paths in rtl/nes_top_ppu.v

# 3. Compile
quartus_sh --flow compile quartus_nes_vga/nes_vga.qpf

# 4. Program FPGA
quartus_pgm -m jtag -o "p;quartus_nes_vga/nes_vga.sof"
```

---

## Resource Usage

| Resource | Used | Available | % |
|:---------|-----:|----------:|--:|
| Logic Elements | 22,808 | 49,760 | 46% |
| M9K Blocks | 51 | 182 | 28% |
| Memory Bits | 410,624 | 1,677,312 | 24% |

**Room for:** SDRAM bridge, mappers, audio

---

## Deferred Decisions

These will be solved when encountered:

- ⏳ CDC between LiteX and NES clock domains
- ⏳ CHR cache for >32KB games
- ⏳ SDRAM arbitration
- ⏳ PRG-ROM latency optimization
- ⏳ Audio output (beyond frame counter IRQ)
