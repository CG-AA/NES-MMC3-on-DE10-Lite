# NES on DE10-Lite - Project Documentation

**Goal:** Build a complete NES emulator on DE10-Lite FPGA, starting standalone (Phase 3) then adding LiteX+SDRAM for larger games (Phase 4).

**Philosophy:** Build minimal working systems, then iterate. Don't solve problems you don't have yet.

**Current Status:** Phase 3 ✅ COMPLETE - Standalone NES core FULLY PLAYABLE!

---

## 📖 Documentation Index

### Phase 3 (Current - COMPLETE)
- **[Phase 3 Summary](phase3/PHASE3_SUMMARY.md)** - What was built, architecture, achievements
- **[Build Guide](phase3/BUILD_GUIDE.md)** - How to compile, program, debug
- **[Hardware Specs](phase3/HARDWARE.md)** - Pin assignments, resource usage, timing
- **[Lessons Learned](LESSONS_LEARNED.md)** - Debug wisdom, common pitfalls

### Phase 4 (Next - Planning)
- **[Phase 4 Plan](phase4/PHASE4_PLAN.md)** - MMC3 mapper, SDRAM integration

### Other
- **[INDEX.md](INDEX.md)** - Full navigation guide (start here if lost!)
- **[CHANGELOG.md](CHANGELOG.md)** - Project history and milestones
- **[archive/](archive/)** - Old phase documents (LiteX setup, early experiments)

---

## 🎮 Quick Start

```bash
# Switch to a game and play
cd /home/cg/risc-v_on_de10-lite/nes
python3 scripts/tools/switch_game.py roms/donkey_kong.nes --compile --program
python3 scripts/tools/keyboard_controller.py --port /dev/ttyUSB0 --continuous
```

**Controls:** WASD/Arrows = D-Pad, K/X = A, J/Z = B, Enter = Start

---

# 📚 Reference Documentation

> Quick reference for project structure and status.

---

## Milestone Progress

| Phase | Milestone | Status |
|:------|:----------|:-------|
| **Phase 1** | LiteX on hardware | ✅ UART working, SDRAM deferred |
| **Phase 2** | CPU + PPU basics | ✅ T65 + VGA verified |
| **Phase 3** | NROM games playable | ✅ **COMPLETE** |
| | • Background tiles | ✅ Full rendering |
| | • Sprite rendering | ✅ All 64 sprites |
| | • Keyboard input | ✅ UART 16x oversampling |
| | • Game switching | ✅ switch_game.py tool |
| **Phase 4** | MMC3 + large games | ⏳ Next |

---

## What Works Now (Phase 3)

✅ **Complete NES emulator** running standalone on FPGA  
✅ **Background rendering** with scrolling  
✅ **All 64 sprites** with correct priority  
✅ **Keyboard input** via UART (laptop → FPGA)  
✅ **VGA output** at 640x480@60Hz  
✅ **Game switching** - compile-time ROM change  
✅ **NROM games** fully playable (Donkey Kong, Balloon Fight, etc.)

---

## Architecture Overview (Phase 3)

Standalone NES core, no LiteX (SDRAM deferred to Phase 4):
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
```

**Phase 4 Target:** Add LiteX SoC with SDRAM for MMC3 games. See [phase4/PHASE4_PLAN.md](phase4/PHASE4_PLAN.md).

---

## File Organization

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
│   └── bios_manager.py         # LiteX utilities (Phase 4)
├── rom_data/                   # Extracted .hex ROM files (gitignored)
├── roms/                       # Original .nes files (gitignored)
├── plan/                       # **Documentation**
│   ├── README.md               # This file (index)
│   ├── LESSONS_LEARNED.md      # Debug wisdom
│   ├── phase3/                 # Phase 3 documentation
│   │   ├── PHASE3_SUMMARY.md   # What was built
│   │   ├── BUILD_GUIDE.md      # How to build/debug
│   │   └── HARDWARE.md         # Specs, pins, resources
│   ├── phase4/                 # Phase 4 planning
│   │   └── PHASE4_PLAN.md      # MMC3 + SDRAM roadmap
│   └── archive/                # Old phase docs
├── quartus_nes_vga/            # Quartus project files
└── build/                      # LiteX outputs (Phase 4)
```

---

## Resource Usage (Phase 3)

| Resource | Used | Available | % |
|:---------|-----:|----------:|--:|
| Logic Elements | ~23,000 | 49,760 | 46% |
| M9K Blocks | ~55 | 182 | 30% |
| Memory Bits | ~450,000 | 1,677,312 | 27% |

**Timing:** Worst-case setup slack 0.316ns @ 50MHz ✅

**Headroom:** 54% logic, 70% M9K, 73% RAM bits available for Phase 4

---

## Tested Games

| Game | Mapper | Status | Notes |
|------|--------|--------|-------|
| Donkey Kong | NROM | ✅ Perfect | Full game playable |
| Balloon Fight | NROM | ✅ Perfect | All features work |
| Ice Climber | NROM | ✅ Expected | NROM compatible |
| Excitebike | NROM | ✅ Expected | NROM compatible |
| SMB3 | MMC3 | ⏳ Phase 4 | Needs SDRAM + mapper |

---

## Key Technical Achievements

### DMA Timing Fix (Jan 6-7)
Fixed critical bug where sprites didn't render due to registered output timing.  
**Solution:** Pre-set write signals one state early for stable cross-module sampling.

### 16x Oversampling UART (Jan 7)
Fixed unreliable controller input (only 0x80/0xFF worked initially).  
**Solution:** 16x oversampling with majority-vote filtering for baud rate tolerance.

### 64-Sprite Rendering (Jan 7)
Scaled from 1 sprite to 64 sprites with priority encoder.  
**Solution:** Combinational hit detection + lookahead for pipeline compensation.

Full details in [LESSONS_LEARNED.md](LESSONS_LEARNED.md).

---

## What's Next (Phase 4)

See [phase4/PHASE4_PLAN.md](phase4/PHASE4_PLAN.md) for detailed roadmap:

1. **SDRAM Bulk Upload** - Etherbone or custom binary loader
2. **Wishbone Bridge** - NES CPU ↔ SDRAM interface  
3. **MMC3 Mapper** - Bank switching + scanline IRQ
4. **Large Games** - Super Mario Bros 3, Mega Man 3, etc.

**Estimated:** ~35K LE total (70%), well within FPGA capacity.

---

## Development Resources

- **Build Guide:** [phase3/BUILD_GUIDE.md](phase3/BUILD_GUIDE.md)
- **Hardware Specs:** [phase3/HARDWARE.md](phase3/HARDWARE.md)  
- **Debug Tips:** [LESSONS_LEARNED.md](LESSONS_LEARNED.md)
- **NESDev Wiki:** https://wiki.nesdev.com/
- **T65 CPU Core:** https://github.com/Tennfors/NES-FPGA

---

## Known Limitations (Phase 3)

| Limitation | Impact | Future Fix |
|------------|--------|------------|
| NROM only | Can't run SMB, Mega Man | Phase 4: MMC3 mapper |
| 1-pixel sprite gap | Minor visual artifact | Fine-tune boundary logic |
| No sprite 0 hit | Some games may glitch | Add collision detection |
| No audio | Silent gameplay | Phase 5: APU |
| 8x8 sprites only | No tall sprites | Add ppuctrl[5] support |

---

## Project History

- **Jan 2, 2026:** Phase 1 - LiteX UART working
- **Jan 4, 2026:** Phase 2 - T65 CPU verified with LED counter
- **Jan 5, 2026:** Phase 2 - PPU + VGA, Donkey Kong title screen!
- **Jan 6, 2026:** Phase 3 - Background tiles, game switching tool
- **Jan 7, 2026:** Phase 3 - Sprites + UART input → **FULLY PLAYABLE!**

---

## Credits

- **T65 6502 Core:** Tennfors/NES-FPGA
- **NES Reference:** MiSTer-devel/NES_MiSTer
- **LiteX Framework:** enjoy-digital/litex
- **DE10-Lite Board:** Terasic

---

*Last Updated: January 7, 2026 - Phase 3 Complete*

- ⏳ CDC between LiteX and NES clock domains
- ⏳ CHR cache for >32KB games  
- ⏳ SDRAM arbitration
- ⏳ PRG-ROM latency optimization
- ⏳ Audio output (beyond frame counter IRQ)
