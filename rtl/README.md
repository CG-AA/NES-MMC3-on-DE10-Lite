# NES RTL Modules

Custom Verilog/VHDL modules for NES-on-DE10-Lite project.

**Status:** Phase 2 Complete - Donkey Kong title screen working! 🎮

## Quick Start

```bash
# Compile and program
cd /home/cg/risc-v_on_de10-lite/nes
quartus_sh --flow compile nes_vga
quartus_pgm -m jtag -o "p;nes_vga.sof"

# Load different ROM
python3 extract_nes_rom.py <game.nes>
# Edit INIT_FILE parameters in nes_top_ppu.v, recompile
```

---

## Active Modules (nes_vga project)

### Top Level
| Module | File | Description |
|:-------|:-----|:------------|
| `nes_top_ppu` | `nes_top_ppu.v` | **MAIN** - Full NES: T65 CPU + PPU + VGA |

### CPU (External VHDL)
| Module | File | Description |
|:-------|:-----|:------------|
| `T65` | `NES-FPGA/src/t65/T65.vhd` | 6502 CPU core |
| `T65_Pack` | `NES-FPGA/src/t65/T65_Pack.vhd` | Package definitions |
| `T65_MCode` | `NES-FPGA/src/t65/T65_MCode.vhd` | Microcode ROM |
| `T65_ALU` | `NES-FPGA/src/t65/T65_ALU.vhd` | ALU operations |

### PPU & Video
| Module | File | Description |
|:-------|:-----|:------------|
| `nes_ppu_vga_sync` | `nes_ppu_vga_sync.v` | VGA-synchronized PPU (no frame buffer) |
| `nes_palette` | `nes_palette.v` | 6-bit NES color → 12-bit RGB |
| `vga_timing` | `vga_timing.v` | 640x480 @ 60Hz timing generator |

### Memory (M9K BRAM)
| Module | File | Description |
|:-------|:-----|:------------|
| `nes_prg_bram` | `nes_prg_bram.v` | 32KB PRG-ROM, registered reads |
| `nes_chr_multiport` | `nes_chr_multiport.v` | 8KB CHR-ROM, 4 read ports |
| `nes_vram_dp` | `nes_vram_dp.v` | 2KB nametable VRAM, dual-port |

### Utilities
| Module | File | Description |
|:-------|:-----|:------------|
| `hex_display` | `hex_display.v` | 7-segment driver for DE10-Lite |

---

## Implemented, Not Yet Wired

These modules are complete but not integrated into `nes_top_ppu.v`:

| Module | File | Integration Point |
|:-------|:-----|:------------------|
| `nes_dma_controller` | `nes_dma_controller.v` | Wire to $4014, bus mux |
| `nes_apu_stub` | `nes_apu_stub.v` | frame_irq_n → CPU IRQ_n |
| `nes_controller` | `nes_controller.v` | $4016/$4017, needs button source |
| `nametable_mirror` | `nametable_mirror.v` | Wire into VRAM addressing |

---

## Utility Modules (For Phase 3+)

| Module | File | Description |
|:-------|:-----|:------------|
| `nes_clk_gen` | `nes_clk_gen.v` | Clock divider (currently inlined) |
| `nes_addr_decode` | `nes_addr_decode.v` | Address decoder (currently inlined) |
| `cdc_multibit` | `cdc_multibit.v` | CDC for SDRAM bridge |
| `nes_internal_ram` | `nes_internal_ram.v` | 2KB RAM with debug port |

---

## Legacy/Reference Modules

| Module | File | Notes |
|:-------|:-----|:------|
| `nes_top_test` | `nes_top_test.v` | CPU-only test harness |
| `nes_top` | `nes_top.v` | Intermediate version |
| `nes_ppu_simple` | `nes_ppu_simple.v` | Original PPU (timing-based) |
| `nes_chr_bram` | `nes_chr_bram.v` | Single-port (superseded) |
| `nes_vram` | `nes_vram.v` | Single-port (superseded) |

---

## External References

| Path | Purpose |
|:-----|:--------|
| `NES-FPGA/` | T65 CPU source, reference PPU |
| `NES_MiSTer/` | Full MiSTer NES for mapper reference |

---

## NES Memory Map

```
$0000-$07FF  Internal RAM (2KB, mirrored to $1FFF)
$2000-$2007  PPU registers (mirrored to $3FFF)
$4000-$4013  APU registers
$4014        OAM DMA trigger
$4015        APU status
$4016-$4017  Controller ports
$6000-$7FFF  PRG-RAM (not implemented yet)
$8000-$FFFF  PRG-ROM (32KB BRAM)

PPU Memory:
$0000-$1FFF  CHR-ROM (pattern tables)
$2000-$2FFF  Nametables (2KB + mirroring)
$3F00-$3F1F  Palette RAM
```

---

## Resource Usage (Phase 2)

| Resource | Used | Available | % |
|:---------|-----:|----------:|--:|
| Logic Elements | 22,808 | 49,760 | 46% |
| M9K Blocks | 51 | 182 | 28% |
| Memory Bits | 410,624 | 1,677,312 | 24% |

---

## Switch/LED Reference

### Switches
| Switch | Function |
|:-------|:---------|
| SW[9] | Ultra-slow CPU (1 Hz) |
| SW[8] | VGA test pattern |
| SW[7] | Debug mode (CHR direct) |
| SW[6:0] | Reserved |

### LEDs
| LED | Function |
|:----|:---------|
| [5:0] | PPU pixel color |
| [6] | Vblank (60Hz blink) |
| [7] | Rendering active |
| [8] | CPU sync |
| [9] | Reset state |

### HEX Display
| Display | Content |
|:--------|:--------|
| HEX3-0 | CPU address |
| HEX5-4 | PPU scanline |
