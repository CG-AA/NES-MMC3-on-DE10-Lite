# Phase 3 Summary: Standalone NES Core

**Duration:** January 4-7, 2026  
**Status:** ✅ COMPLETE - FULLY PLAYABLE

---

## What Was Built

A complete, standalone NES emulator running on DE10-Lite FPGA:

### Hardware
- **FPGA:** Intel MAX 10 (10M50DAF484C7G)
- **Clock:** 50MHz system, 25MHz VGA pixel clock
- **Display:** VGA 640x480@60Hz (2x NES scaling)
- **Input:** UART keyboard controller (CP2102 USB adapter)
- **Memory:** BRAM only (no SDRAM needed for NROM games)

### Features
- ✅ T65 6502 CPU @ ~1.78MHz
- ✅ PPU with VGA-synchronized rendering
- ✅ Background tile layer (32x30 nametable)
- ✅ Sprite rendering (all 64 sprites, priority correct)
- ✅ OAM DMA controller
- ✅ UART keyboard input (16x oversampling)
- ✅ Game switching tool (compile-time ROM change)
- ✅ APU frame counter stub (for timing)

### What Works
- Full background rendering with scrolling
- All sprites render with correct priority
- Keyboard controls responsive
- Games play smoothly at 60 FPS
- Donkey Kong, Balloon Fight, etc. fully playable

---

## Architecture

### Block Diagram
```
┌─────────────────────────────────────────────────────────┐
│                    DE10-Lite FPGA                        │
│  ┌─────────────────────────────────────────────────────┐│
│  │           NES Core (Standalone)                     ││
│  │                                                      ││
│  │  ┌──────────┐         ┌─────────────────────────┐  ││
│  │  │ T65 CPU  │◄───────►│ PRG-ROM (32KB BRAM)     │  ││
│  │  │ ~1.78MHz │         │ Internal RAM (2KB BRAM) │  ││
│  │  └─────┬────┘         └─────────────────────────┘  ││
│  │        │                                            ││
│  │        │ Memory Bus (50MHz)                         ││
│  │        │                                            ││
│  │  ┌─────▼──────┐       ┌─────────────────────────┐  ││
│  │  │    PPU     │◄─────►│ CHR-ROM (8KB, 6-port)   │  ││
│  │  │ VGA-sync   │       │ VRAM (2KB, 3-port)      │  ││
│  │  │ Sprite64   │       │ OAM (256B, DMA)         │  ││
│  │  └─────┬──────┘       │ Palette (32B ROM)       │  ││
│  │        │              └─────────────────────────┘  ││
│  │        │ RGB + Sync                                 ││
│  │  ┌─────▼──────┐       ┌─────────────────────────┐  ││
│  │  │ VGA Output │       │ UART Keyboard (GPIO[0]) │  ││
│  │  │ 640x480    │       │ 115200 baud, 16x sample │  ││
│  │  │ 25MHz px   │       │ Auto-fallback switches  │  ││
│  │  └────────────┘       └─────────────────────────┘  ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### Resource Usage
| Resource | Used | Available | % |
|----------|------|-----------|---|
| Logic Elements | 23,000 | 49,760 | 46% |
| M9K Blocks | 55 | 182 | 30% |
| Memory Bits | 450,000 | 1,677,312 | 27% |

**Headroom available:** 54% logic, 70% memory, 73% RAM for Phase 4 expansion.

---

## Major Debug Sessions

### 1. DMA Timing Bug (Jan 6-7)
**Symptom:** Sprites didn't render, OAM contained zeros.  
**Root Cause:** Registered outputs set in WRITE state, sampled same cycle.  
**Fix:** Pre-set signals in READ_WAIT state for stable sampling.  
**Result:** All sprites now render correctly.

### 2. UART Receiver Reliability (Jan 7)
**Symptom:** Only 0x80 and 0xFF received, other values failed.  
**Root Cause:** Baud rate drift with 1x sampling (0.03 cycles/bit error).  
**Fix:** 16x oversampling with majority-vote noise filtering.  
**Result:** All button values received reliably.

### 3. Multi-Sprite Rendering (Jan 7)
**Challenge:** Scale from 1 sprite to 64 without explosion.  
**Solution:** Priority encoder with lookahead compensation.  
**Result:** All 64 sprites render with correct priority.

---

## Key Files

### RTL (Verilog/VHDL)
- `rtl/nes_top_ppu.v` - Top-level integration
- `rtl/nes_ppu_vga_sync.v` - PPU with VGA sync + 64 sprites
- `rtl/nes_dma_controller.v` - OAM DMA (fixed timing)
- `rtl/nes_uart_controller.v` - 16x oversampling UART RX
- `rtl/nes_chr_multiport.v` - 6-port CHR-ROM for parallel access
- `rtl/nes_vram_dp.v` - 3-port VRAM (PPU + CPU)
- `rtl/NES-FPGA/src/t65/` - T65 6502 core (VHDL)

### Tools (Python)
- `scripts/tools/switch_game.py` - Full game switching pipeline
- `scripts/tools/extract_nes_rom.py` - .nes → .hex converter
- `scripts/tools/keyboard_controller.py` - Laptop keyboard → NES

### Quartus Project
- `quartus_nes_vga/nes_vga.qsf` - Pin assignments, settings
- `quartus_nes_vga/nes_vga.sdc` - Timing constraints

### ROM Data
- `rom_data/donkey_kong_prg.hex` - 32KB PRG-ROM (example)
- `rom_data/donkey_kong_chr.hex` - 8KB CHR-ROM (example)
- `roms/*.nes` - Original ROM files

---

## Tested Games (NROM Only)

| Game | Status | Notes |
|------|--------|-------|
| Donkey Kong | ✅ Perfect | Title, gameplay, all sprites working |
| Balloon Fight | ✅ Perfect | Full gameplay tested |
| Ice Climber | ✅ Expected | NROM compatible |
| Excitebike | ✅ Expected | NROM compatible |

---

## Lessons Learned

See `LESSONS_LEARNED.md` for full details:

1. **Registered Output Timing** - Set signals one cycle early for cross-module boundaries
2. **UART Oversampling** - 16x sampling essential for reliable baud rate tolerance
3. **Visual Debug Bars** - Horizontal bars show data values better than hex displays
4. **Pipeline Latency** - Always account for BRAM 1-cycle read delay
5. **Isolation Testing** - Ghost sprites, solid colors verify subsystems independently

---

## Deferred to Phase 4

- **SDRAM integration** - Bulk ROM uploads via Etherbone/Ethernet
- **MMC3 mapper** - Bank switching, scanline IRQ
- **8x16 sprites** - Tall sprite mode
- **Sprite 0 hit** - Collision detection for split-screen
- **APU audio** - Sound synthesis
- **Advanced scrolling** - Split-screen, status bars

---

## Ready for Phase 4

With Phase 3 complete, we have:
- Solid foundation (PPU + CPU verified)
- Clean architecture (easy to add mappers)
- Debug experience (know how to isolate issues)
- Working tools (game switching, ROM extraction)

Next step: SDRAM + MMC3 for large games!
