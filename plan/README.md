# NES on DE10-Lite: Implementation Plan

**Goal:** Build a hybrid NES emulator using LiteX (host) + custom NES core (guest) on DE10-Lite FPGA.

**Philosophy:** Build minimal working systems, then iterate. Don't solve problems you don't have yet.

**Current Status:** Phase 3 In Progress ⚠️ - SDRAM small blocks work, large uploads unreliable

---

## Quick Start Milestones

| Milestone | Target | Status |
|:----------|:-------|:-------|
| M1 | LiteX on real hardware | ✅ UART + SDRAM working |
| M2 | SDRAM read/write | ⚠️ **Small blocks OK, large uploads fail** |
| M3 | 6502 runs from BRAM | ✅ LED counter working |
| M4 | PPU outputs test pattern | ✅ VGA test pattern |
| M5 | NROM game boots | ✅ **Donkey Kong title screen!** |
| M6 | MMC3 game boots | ⏳ Phase 4 |

---

## Latest Update (2026-01-06)

**SDRAM Status: Partial Success**

| Test | Result |
|------|--------|
| Individual writes | ✅ PASS at all addresses |
| 256B - 4KB blocks | ✅ PASS with 10-20ms delays |
| 8KB+ blocks | ❌ FAIL - data reads as 0 |
| Full ROM (32KB) | ❌ FAIL - verification errors |

**Root cause hypothesis:** L2 cache not flushing to SDRAM during large uploads, or row buffer conflicts causing data loss.

**Recommended next steps:**
1. Rebuild with L2 cache disabled
2. Try Etherbone instead of UART
3. Use BRAM-only for NROM games (they fit!)

**See:** [03-memory-bridge.md](03-memory-bridge.md) for detailed findings

**The Fix:** Doubled SDRAM timing parameters (tRP, tRCD, tWR: 40ns→80ns, tRFC: 140ns→200ns) to prevent write collisions with refresh cycles.

**Next Steps:**
1. Test full ROM upload with new timings
2. Verify bulk upload reliability
3. Integrate ROM loading with NES core

**See:** [03-memory-bridge.md](03-memory-bridge.md) for detailed implementation

---

## Architecture Overview

### Current (Phase 2 - BRAM Only)
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

### Target (Phase 3+ - SDRAM)
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

### Phase 3: SDRAM Integration ⏳ NEXT
**Goal:** Load ROMs larger than BRAM

| Task | Status |
|:-----|:-------|
| Fix SDRAM PHY | ⏳ TODO |
| Wishbone bridge | ⏳ TODO |
| ROM loader script | ⏳ TODO |

**See:** [03-memory-bridge.md](03-memory-bridge.md)

### Phase 4: MMC3 Support
**Goal:** Run Super Mario Bros 3

| Task | Status |
|:-----|:-------|
| MMC3 mapper | ⏳ Future |
| PRG bank switching | ⏳ Future |
| CHR bank switching | ⏳ Future |
| Scanline counter IRQ | ⏳ Future |

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
├── plan/                   # Documentation
│   ├── README.md           # This file
│   ├── 01-litex-setup.md   # Phase 1 details
│   ├── 02-components.md    # Phase 2 details
│   ├── 03-memory-bridge.md # Phase 3 details
│   └── 04-integration.md   # Phase 4 details
├── nes_vga.qpf/qsf/sdc     # Quartus project
├── extract_nes_rom.py      # ROM extractor
├── gen_ppu_test_rom_v2.py  # Test ROM generator
└── donkey_kong.nes         # Test ROM
```

---

## Build & Run

```bash
# Compile
cd /home/cg/risc-v_on_de10-lite/nes
quartus_sh --flow compile nes_vga

# Program FPGA
quartus_pgm -m jtag -o "p;nes_vga.sof"

# Load different game
python3 extract_nes_rom.py <game.nes>
# Edit INIT_FILE in nes_top_ppu.v, recompile
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
