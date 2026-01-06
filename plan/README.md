# NES on DE10-Lite: Implementation Plan

**Goal:** Build a hybrid NES emulator using LiteX (host) + custom NES core (guest) on DE10-Lite FPGA.

**Philosophy:** Build minimal working systems, then iterate. Don't solve problems you don't have yet.

**Current Status:** Phase 3.5 - Core Refinement ⏳ - Fixing rendering pipeline and adding sprites

---

# 📚 Reference Documentation

> Stable, organized information about the project architecture and usage.

---

## Quick Start Milestones

| Milestone | Target | Status |
|:----------|:-------|:-------|
| M1 | LiteX on real hardware | ✅ UART + SDRAM working |
| M2 | SDRAM read/write | ⚠️ Individual OK, bulk deferred |
| M3 | 6502 runs from BRAM | ✅ LED counter working |
| M4 | PPU outputs test pattern | ✅ VGA test pattern |
| M5 | NROM game boots | ✅ Donkey Kong title screen |
| M6 | Game switching tool | ✅ switch_game.py |
| M7 | Keyboard controller | ✅ UART controller working |
| M7.5 | Core refinement | ⏳ In Progress |
| M8 | MMC3 game boots | ⏳ Phase 4 |

---

## Architecture Overview

### Current (Phase 3 - BRAM Only)
\`\`\`
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
│  │  │+Sprites │    │ OAM (256B)      │ ││
│  │  └────┬────┘    └─────────────────┘ ││
│  │       │                              ││
│  │  ┌────▼────┐    ┌─────────────────┐ ││
│  │  │   VGA   │    │ UART Controller │ ││
│  │  │640x480  │    │ (keyboard in)   │ ││
│  │  └────┬────┘    └─────────────────┘ ││
│  │       ▼                              ││
│  │    Monitor                           ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
\`\`\`

### Target (Phase 4 - SDRAM for large games)
\`\`\`
LiteX SoC (100 MHz)          NES Core (50 MHz)
┌─────────────────┐          ┌─────────────────┐
│ VexRiscv CPU    │          │ T65 6502 CPU    │
│ UART            │◄────────►│ PPU → VGA       │
│ SDRAM           │  Bridge  │ APU stub        │
│ CSRs            │          │ Controller      │
└─────────────────┘          └─────────────────┘
\`\`\`

---

## Project Structure

\`\`\`
nes/
├── rtl/                        # Verilog/VHDL source
│   ├── nes_top_ppu.v           # Main top-level
│   ├── nes_ppu_vga_sync.v      # VGA-synchronized PPU with sprites
│   ├── nes_prg_bram.v          # 32KB PRG-ROM
│   ├── nes_chr_multiport.v     # 8KB CHR-ROM (6-port)
│   ├── nes_vram_dp.v           # 2KB nametable (3-port)
│   ├── nes_dma_controller.v    # OAM DMA controller
│   ├── nes_apu_stub.v          # APU frame counter stub
│   ├── nes_uart_controller.v   # UART keyboard input
│   ├── vga_timing.v            # VGA timing generator
│   ├── nes_palette.v           # Color palette ROM
│   ├── hex_display.v           # 7-segment driver
│   ├── NES-FPGA/               # External: T65 CPU
│   └── NES_MiSTer/             # External: Reference
├── scripts/tools/
│   ├── switch_game.py          # Game switching automation
│   ├── extract_nes_rom.py      # ROM → .hex conversion
│   ├── keyboard_controller.py  # Keyboard → NES controller
│   └── bios_manager.py         # LiteX BIOS utilities
├── rom_data/                   # Extracted .hex ROM files
├── roms/                       # Original .nes files
├── plan/                       # Documentation (this folder)
├── quartus_nes_vga/            # Quartus project files
└── build/                      # LiteX build outputs
\`\`\`

---

## Build & Run

\`\`\`bash
# Switch to a different game (full pipeline)
python3 scripts/tools/switch_game.py game.nes --compile --program

# Or manually:
python3 scripts/tools/extract_nes_rom.py roms/game.nes
quartus_sh --flow compile quartus_nes_vga/nes_vga.qpf
quartus_pgm -m jtag -o "p;quartus_nes_vga/nes_vga.sof"

# Play with keyboard
python scripts/tools/keyboard_controller.py --port /dev/ttyUSB0
\`\`\`

---

## Resource Usage

| Resource | Used | Available | % |
|:---------|-----:|----------:|--:|
| Logic Elements | ~23,000 | 49,760 | 46% |
| M9K Blocks | ~55 | 182 | 30% |
| Memory Bits | ~450,000 | 1,677,312 | 27% |

**Timing:** Worst-case setup slack 0.316ns @ 50MHz ✅

**Room for:** SDRAM bridge, mappers, audio

---

## Known Limitations

| Limitation | Impact | Future Fix |
|------------|--------|------------|
| 8x8 sprites only | No 8x16 sprite mode | Add ppuctrl[5] support |
| 64 sprites scanned per pixel | High logic usage | Per-scanline evaluation |
| No sprite 0 hit detection | Some games may break | Add collision check |
| Simplified scrolling | Single-screen OK | Full split-screen |
| APU stub only | No audio | Implement full APU |

---

## Deferred Decisions

- ⏳ CDC between LiteX and NES clock domains
- ⏳ CHR cache for >32KB games  
- ⏳ SDRAM arbitration
- ⏳ PRG-ROM latency optimization
- ⏳ Audio output (beyond frame counter IRQ)

---
---

# 📝 Development Log

> Chronological updates, debugging notes, and work-in-progress details.
> This section contains messy notes and detailed technical debugging information.

---

## 2026-01-06: Phase 3.5 - Core Component Refinement

### Code Review Findings

After comprehensive code review, 11 issues were identified and fixed:

| Issue | Component | Status |
|-------|-----------|--------|
| CPU data bus mux returned \`cpu_dout\` during writes | \`nes_top_ppu.v\` | ✅ Fixed |
| UART bit sampling at boundaries (low noise immunity) | \`nes_uart_controller.v\` | ✅ Fixed |
| Controller priority check \`!= 0\` causing input mixing | \`nes_top_ppu.v\` | ✅ Fixed |
| Attribute table hardcoded palette 0 | \`nes_ppu_vga_sync.v\` | ✅ Fixed |
| Scrolling not implemented | \`nes_ppu_vga_sync.v\` | ✅ Fixed |
| OAM DMA controller not wired | \`nes_top_ppu.v\` | ✅ Fixed |
| OAM memory not in PPU | \`nes_ppu_vga_sync.v\` | ✅ Fixed |
| APU stub not wired | \`nes_top_ppu.v\` | ✅ Fixed |
| Palette mirroring (\$3F10→\$3F00) missing | \`nes_ppu_vga_sync.v\` | ✅ Fixed |
| Pixel strip misalignment (pipeline timing) | \`nes_ppu_vga_sync.v\` | ✅ Fixed |
| Missing sprites (no sprite rendering) | \`nes_ppu_vga_sync.v\` | ✅ Implemented |

### Hardware Test Results

After fixes, Donkey Kong shows:
- ✅ Title screen renders correctly
- ✅ Text/logos display properly  
- ✅ Colors correct (palette mirroring fixed)
- ✅ Scrolling works
- ⏳ Sprites implemented (needs hardware test)

### Technical Details

**Pipeline Registers Added:**

BRAM reads have 1-cycle latency. Added pipeline registers to compensate:
- \`fine_x_p1\`, \`fine_x_p2\` - Fine X scroll delay
- \`fine_y_p1\` - Fine Y scroll delay
- \`tile_x_p1\`, \`tile_y_p1\` - Quadrant calculation delay
- \`vga_y_p1\`, \`vga_y_p2\` - Visibility check delay
- \`quadrant_p2\` - Attribute quadrant delay
- \`palette_hi_p1\` - Palette high bits delay

**Sprite Rendering System:**
- Scans all 64 OAM sprites per pixel (simplified, not cycle-accurate)
- Finds first sprite covering current pixel position
- Handles horizontal/vertical flip
- Implements sprite priority (behind/in front of BG)
- Uses dedicated CHR ports (5/6) for sprite pattern reads
- Pipeline registers match CHR read latency

**Memory Port Extensions:**
- CHR: 4 → 6 ports (added sprite lo/hi bitplanes)
- VRAM: 2 → 3 ports (added attribute table read)

---

## 2026-01-06: Phase 3 Complete - BRAM-Only Approach

### Decision Made

Use BRAM for NROM games instead of SDRAM.

| Approach | Pros | Cons |
|----------|------|------|
| **BRAM** | 100% reliable, no bus contention | 40KB limit, recompile per game |
| SDRAM | 64MB capacity, runtime loading | Bulk uploads unreliable via UART |

### Tools Created

| Tool | Purpose |
|------|---------|
| \`extract_nes_rom.py\` | Convert .nes → .hex files |
| \`switch_game.py\` | Switch games (extract + update RTL + compile) |
| \`keyboard_controller.py\` | Laptop keyboard → NES controller via UART |

### SDRAM Status

SDRAM hardware is fixed (phase 270°, safe timings). Bulk uploads fail due to UART buffer overrun.
Future options: Etherbone, custom loader, or SD card. Deferred to Phase 4.

---

## 2026-01-05: Phase 2 Complete - Donkey Kong Boots!

### Achievement Unlocked ��

Donkey Kong title screen displaying on VGA!

### What Works
- T65 6502 CPU executing PRG-ROM
- PPU tile rendering from CHR-ROM
- VGA output at 640x480 @ 60Hz
- Nametable rendering

---

## Implementation Phases Summary

| Phase | Goal | Status |
|-------|------|--------|
| 1 | LiteX on Hardware | ⚠️ Partial (SDRAM issues) |
| 2 | Minimal NES Core | ✅ Complete |
| 3 | ROM Loading (BRAM) | ✅ Complete |
| 3.5 | Core Refinement | ⏳ In Progress |
| 4 | MMC3 Support | ⏳ Next |

### Phase 4 Tasks (MMC3)

| Task | Status |
|:-----|:-------|
| Fix SDRAM bulk uploads | ⏳ TODO (Etherbone?) |
| MMC3 mapper | ⏳ TODO |
| PRG bank switching | ⏳ TODO |
| CHR bank switching | ⏳ TODO |
| Scanline counter IRQ | ⏳ TODO |

---

## Related Documents

- [01-litex-setup.md](01-litex-setup.md) - LiteX SoC setup details
- [02-components.md](02-components.md) - NES component details
- [03-memory-bridge.md](03-memory-bridge.md) - Memory architecture
- [04-integration.md](04-integration.md) - Integration plans
