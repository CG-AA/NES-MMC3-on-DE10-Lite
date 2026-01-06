# Project Changelog

Historical record of major milestones and changes.

---

## January 7, 2026 - Phase 3 Complete! 🎉

**Status:** FULLY PLAYABLE NES emulator on DE10-Lite

### Major Achievements
- ✅ All 64 sprites rendering with correct priority
- ✅ UART keyboard controller working reliably
- ✅ Background tiles + sprites + input = complete game!
- ✅ Donkey Kong, Balloon Fight fully playable

### Technical Fixes

**DMA Timing Bug (Jan 6-7)**
- Problem: Sprites didn't render, OAM had zeros
- Root cause: Registered outputs set in WRITE state, sampled same cycle
- Fix: Pre-set signals in READ_WAIT state
- Result: All sprites now render correctly

**UART Receiver Reliability (Jan 7)**
- Problem: Only 0x80 and 0xFF received correctly
- Root cause: Baud rate drift with 1x sampling
- Fix: 16x oversampling with majority-vote filtering
- Result: All button values received reliably

**64-Sprite Rendering (Jan 7)**
- Challenge: Scale from 1 to 64 sprites
- Solution: Priority encoder with lookahead
- Result: All sprites render with correct priority

### Documentation Refactored
- Created phase3/ directory with summary, build guide, hardware specs
- Created phase4/ directory for future planning
- Archived old phase documents
- Streamlined main README as index

---

## January 6, 2026 - Phase 3.5: Core Refinement

### Sprite System
- Expanded from 8 to 64 sprites
- Added priority encoder
- Implemented sprite priority (behind/in front of BG)
- Fixed horizontal positioning with lookahead

### Memory Optimization
- CHR: 4 → 6 ports (added sprite pattern reads)
- VRAM: 2 → 3 ports (added attribute table)
- Multiport architecture prevents bus conflicts

### Debug Infrastructure
- Visual debug bars showing OAM values
- VBlank snapshot for stable display
- DMA capture for data verification

---

## January 6, 2026 - Phase 3: BRAM-Only Decision

### Strategic Decision
**Use BRAM for NROM games instead of SDRAM**

Reasoning:
- SDRAM bulk uploads unreliable via UART
- BRAM has plenty of capacity for NROM (40KB fits easily)
- Defer SDRAM to Phase 4 with MMC3 mapper

### Tools Created
- `extract_nes_rom.py` - Convert .nes → .hex
- `switch_game.py` - Automated game switching
- `keyboard_controller.py` - UART keyboard input

### Architecture
- 32KB PRG-ROM BRAM (compile-time)
- 8KB CHR-ROM BRAM (compile-time)
- Game switching via recompilation (~7 min)

---

## January 5, 2026 - Phase 2 Complete: Donkey Kong Boots! 🎮

### PPU + VGA Working
- VGA timing: 640x480@60Hz, 25MHz pixel clock
- 2x NES scaling (256x240 → 512x480 centered)
- Background tile rendering verified
- Palette ROM working (64 colors)

### First Game Running
- **Donkey Kong title screen displayed!**
- Nametable rendering correct
- Pattern table (CHR) working
- Color palette accurate

### PPU Features
- Nametable addressing
- Attribute table (2x2 tile coloring)
- Pattern table CHR reads
- VGA-synchronized rendering
- 2-bit-per-pixel → 6-bit color conversion

---

## January 4, 2026 - Phase 2: T65 CPU Verified

### CPU Debug Success
- Root cause found: JMP address off by 1
- Test ROM regenerated with correct address
- Binary counter on LEDs working
- All 6502 instructions verified

### Hardware Confirmed
- T65 VHDL core working
- 32KB PRG BRAM with $readmemh
- 2KB internal RAM
- Address decoding correct
- Memory timing verified

### Test Results
| Test | Result |
|------|--------|
| Reset sequence | ✅ FFFC→FFFD→8000 |
| Delay loop BNE | ✅ Branching correctly |
| LED counter | ✅ Binary counting |

---

## January 2, 2026 - Phase 1: LiteX on Hardware

### Initial Setup
- LiteX SoC on DE10-Lite
- UART working (115200 baud)
- BIOS prompt responding
- Individual SDRAM reads/writes OK

### Deferred
- SDRAM bulk uploads (UART buffer overrun)
- LiteX integration with NES core

### Decision
Focus on standalone NES core first, defer LiteX+SDRAM to Phase 4.

---

## Development Methodology

### Iterative Approach
1. Build minimal working system
2. Verify in isolation
3. Integrate and debug
4. Expand functionality

### Debug Techniques
- Visual debug bars (horizontal bars = data values)
- Isolation testing (ghost sprites, solid colors)
- Snapshot at VBlank (stable values)
- Capture source vs destination data

### Tools Philosophy
- Python scripts for automation
- Compile-time ROM loading (simple, reliable)
- UART for input (no custom hardware needed)

---

## Resource Growth

| Phase | LE | M9K | % LE | % M9K |
|-------|----:|----:|-----:|------:|
| Phase 2 (CPU+PPU basic) | ~15K | ~40 | 30% | 22% |
| Phase 3.0 (BG tiles) | ~20K | ~50 | 40% | 27% |
| Phase 3.5 (64 sprites) | ~23K | ~55 | 46% | 30% |
| Phase 4 (est. MMC3) | ~35K | ~70 | 70% | 38% |

Plenty of headroom remaining!

---

## Next Steps (Phase 4)

See `phase4/PHASE4_PLAN.md` for:
1. SDRAM bulk upload via Etherbone
2. Wishbone bridge NES ↔ SDRAM
3. MMC3 mapper (bank switching + IRQ)
4. Large games (SMB3, Mega Man 3)

---

*This changelog tracks major milestones. For detailed technical notes, see LESSONS_LEARNED.md*
