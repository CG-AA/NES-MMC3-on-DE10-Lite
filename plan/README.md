# NES on DE10-Lite: Implementation Plan

**Goal:** Build a hybrid NES emulator using LiteX (host) + custom NES core (guest) on DE10-Lite FPGA.

**Philosophy:** Build minimal working systems, then iterate. Don't solve problems you don't have yet.

**Current Status:** Phase 3.5 - Core Refinement ✅ - Background ✅ working, Sprites ✅ WORKING!

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
| M7.5 | Core refinement | ✅ BG + Sprites fully working! |
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
| 1-pixel horizontal sprite gap | Minor visual artifact | Fine_x boundary fix |
| 8x8 sprites only | No 8x16 sprite mode | Add ppuctrl[5] support |
| 64 sprites scanned per pixel | High logic usage | Per-scanline evaluation |
| No sprite 0 hit detection | Some games may break | Add collision check |
| Simplified scrolling | Single-screen OK | Full split-screen |
| APU stub only | No audio | Implement full APU |

---

## 🎉 Sprite Rendering Fix (January 7, 2026)

### Problem Discovered
Sprites were not rendering - OAM contained all zeros or small values despite DMA completing.

### Debug Process
1. **Ghost Sprite Test**: Hardcoded OAM values rendered correctly → CHR path works
2. **Solid Color Test**: 8x8 square at (50,50) worked → Coordinate system OK
3. **Visual Debug Bars**: Displayed OAM[0-3] as horizontal bar lengths
4. **VBlank Snapshot**: Eliminated flickering by capturing values at vblank
5. **DMA Capture**: Added second row of bars showing what DMA read from RAM
6. **Key Finding**: DMA bars were long (correct data), OAM bars were short (wrong data)

### Root Cause: DMA Timing Bug
```verilog
// BROKEN: Write signals set in WRITE state, sampled same cycle
WRITE: begin
    dma_data <= read_latch;   // Updates at END of cycle
    dma_write <= 1'b1;         // Updates at END of cycle
    // PPU samples cpu_wr at same clock edge - sees OLD values!
end
```

### Fix: Pre-set Write Signals
```verilog
READ_WAIT: begin
    if (mem_ack) begin
        // Set write signals HERE so they're valid NEXT cycle
        dma_addr <= 16'h2004;
        dma_data <= bus_data_in;
        dma_write <= 1'b1;
        state <= WRITE;
    end
end

WRITE: begin
    dma_write <= 1'b0;  // Clear after PPU has sampled it
    // Continue to next byte...
end
```

### Multi-Sprite Rendering
After DMA fix, expanded from 1 sprite to 8 to 64:
- Combinational hit detection for all 64 sprites
- Priority encoder selects lowest-indexed hit
- Pipeline lookahead (`vga_x + 1`) compensates for CHR read latency
- All sprites now render correctly with animations and priorities

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
| CPU data bus mux returned `cpu_dout` during writes | `nes_top_ppu.v` | ✅ Fixed |
| UART bit sampling at boundaries (low noise immunity) | `nes_uart_controller.v` | ✅ Fixed |
| Controller priority check `!= 0` causing input mixing | `nes_top_ppu.v` | ✅ Fixed |
| Attribute table hardcoded palette 0 | `nes_ppu_vga_sync.v` | ✅ Fixed |
| Scrolling not implemented | `nes_ppu_vga_sync.v` | ✅ Fixed |
| OAM DMA controller not wired | `nes_top_ppu.v` | ✅ Fixed |
| OAM memory not in PPU | `nes_ppu_vga_sync.v` | ✅ Fixed |
| APU stub not wired | `nes_top_ppu.v` | ✅ Fixed |
| Palette mirroring ($3F10→$3F00) missing | `nes_ppu_vga_sync.v` | ✅ Fixed |
| Pixel strip misalignment (pipeline timing) | `nes_ppu_vga_sync.v` | ✅ Fixed |
| **Sprite rendering** | `nes_ppu_vga_sync.v` | ❌ **BROKEN** |

### Hardware Test Results (Latest)

**Background rendering: ✅ WORKING**
- Title screen, text, logos render correctly
- Donkey Kong character (background tiles) displays properly
- Colors correct
- Scrolling works

**Sprite rendering: ❌ BROKEN**
- Mario, Princess, barrels appear fragmented/chunked
- Sprites appear at wrong screen positions
- Some sprites missing entirely

---

## 2026-01-06/07: Sprite Debugging Session (Extended)

### Current Symptoms
1. Sprites appear as fragmented chunks in diagonal pattern
2. Sprite positions are wrong (scattered from top-left to bottom-right)
3. Some sprites don't appear at all
4. Background tiles (Donkey Kong, text) work correctly
5. A "fast moving thing" runs diagonally across screen

### Debug Approach: Ghost Sprite Isolation Test

Instead of debugging the full OAM system, we isolated components:

#### Test 1: Hardcoded Ghost Sprite
- Placed hardcoded sprite at position (50, 50) using tile $01
- **Result**: "Chunk of Mario's leg" appeared, but position wrong and arc-shaped
- **Conclusion**: CHR data path works, coordinate/pipeline issue exists

#### Test 2: Solid Color Square (No CHR)
- Removed CHR lookup entirely, just draw solid 8x8 colored square at (50, 50)
- **Result**: Perfect 8x8 orange-yellow square at correct position! ✅
- **Conclusion**: Hit detection and coordinate system work perfectly

#### Test 3: Ghost Sprite with Correct Pipeline  
- Added CHR tile reading with 1-cycle pipeline delay
- **Result**: Mario's bottom half visible, partially transparent where expected ✅
- **Conclusion**: Sprite rendering pipeline timing is correct

### Root Cause Identified: OAM Data Problem

After proving the renderer works, we switched to reading from actual OAM:

#### Visual Debug Bars Added
Display OAM sprite 0 values as horizontal bars at top of screen:
- **Orange bar (row 1)**: OAM[3] = X position (length in pixels)
- **Green bar (row 2)**: OAM[0] = Y position (length in pixels)  
- **Blue bar (row 3)**: OAM[1] = Tile number (length in pixels)
- **White box**: Crosshair at sprite 0's actual position

#### Findings from Visual Debug

| Observation | Interpretation |
|-------------|----------------|
| Bars flash/flicker rapidly when reading OAM continuously | OAM being written mid-frame, or read/write conflict |
| Bars stable when using VBlank snapshot | Confirms we need frame-sync for OAM reads |
| Bars only appear when game demo starts | OAM is empty/uninitialized until game writes it |
| All bars are ~1px when game running | OAM[0..3] contain values 0 or 1 |
| White box at top-left corner (0,0) | Sprite 0 positioned at X=0, Y=0 |
| oamaddr bar (cyan) doesn't appear | oamaddr = 0 at vblank (DMA completed correctly) |

### Current Hypothesis

**The game IS writing to OAM via DMA, but the data ends up wrong.**

Possibilities:
1. ❌ DMA not running → Disproven (oamaddr wraps to 0, meaning 256 bytes written)
2. ❌ OAM not being read correctly → Disproven (VBlank snapshot is stable)
3. ⚠️ **DMA reads wrong source data** → RAM address mux issue?
4. ⚠️ **CPU writes wrong data to RAM before DMA** → CPU/RAM interface issue?
5. ⚠️ **oamaddr not set to 0 before DMA starts** → Game relies on $2003 write

### Verified Working Components
- ✅ Ghost sprite at hardcoded position renders correctly
- ✅ Sprite CHR tile lookup works (Mario's leg visible)
- ✅ Sprite transparency works
- ✅ Sprite pipeline timing correct (1-cycle delay)
- ✅ Hit detection and coordinate comparison work
- ✅ VBlank snapshot prevents read/write conflicts
- ✅ DMA completes (oamaddr = 0 after DMA)
- ✅ OAM reads are stable when snapshotted

### Still Broken
- ❌ Actual sprite data in OAM is wrong (all zeros or very small values)
- ❌ Real sprites don't appear at correct positions

### Next Investigation Steps

1. **Check DMA source address**
   - Is `dma_addr` pointing to correct RAM locations?
   - Is RAM returning correct data to DMA?

2. **Check what game writes to RAM**
   - Add debug to show RAM[$0200..$02FF] (typical OAM buffer)
   - Compare with expected sprite data

3. **Verify $2003 (OAMADDR) timing**
   - Game should write $00 to $2003 before DMA
   - If oamaddr starts non-zero, data goes to wrong slots

### Architecture Diagram (OAM DMA Path)

```
Game Code:
  LDA #$02        ; Source page = $0200
  STA $4014       ; Trigger DMA
        │
        ▼
┌───────────────────────────────┐
│ DMA Controller                │
│  dma_addr = $0200 + count     │◄──── Is this correct?
│  dma_read = 1                 │
└───────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│ RAM (2KB)                     │
│  ram_addr_mux = dma_addr      │◄──── Is RAM returning correct data?
│  bus_data_in = ram_rdata      │
└───────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│ DMA Controller                │
│  read_latch = bus_data_in     │
│  dma_addr = $2004             │
│  dma_write = 1                │
│  dma_data = read_latch        │
└───────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│ PPU                           │
│  if (dma_ppu_wr)              │
│    oam[oamaddr] = dma_data    │◄──── Is oamaddr = 0 at start?
│    oamaddr++                  │
└───────────────────────────────┘
```

### Debug Output Currently Active

The PPU currently has visual debug bars enabled:
- 4 horizontal bars at top of screen showing OAM sprite 0 data
- White crosshair box at sprite 0's screen position
- Values snapshotted at VBlank for stability

To disable debug and restore normal rendering, remove the debug code section in `nes_ppu_vga_sync.v`.
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
