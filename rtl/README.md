# NES RTL Modules

Custom Verilog modules for NES-on-DE10-Lite project.

## Module List

### Core Timing
- **nes_clk_gen.v** - Clock divider for NES timing. Generates CPU (1.789 MHz) and PPU (5.369 MHz) enables from 21.477 MHz master clock. Maintains 3:1 PPU/CPU ratio.

### Bus & Memory
- **nes_addr_decode.v** - Address decoder for NES memory map. Generates chip selects for RAM, PPU, APU, controllers, PRG-RAM, and PRG-ROM.
- **nes_internal_ram.v** - 2KB internal RAM with dual-port access (NES + host debug).
- **nametable_mirror.v** - Nametable mirroring logic for horizontal, vertical, and single-screen modes.
- **cdc_multibit.v** - Clock domain crossing utilities (Gray code + quasi-static sync).

### Peripherals
- **nes_dma_controller.v** - OAM DMA controller with full bus mastering. Transfers 256 bytes to PPU sprite RAM.
- **nes_apu_stub.v** - APU frame counter stub (no audio synthesis). Generates frame IRQ only.
- **nes_controller.v** - Controller shift register for reading button states via $4016/$4017.

## Not Yet Implemented

These modules are referenced in the plan but not yet created:
- `nes_top.v` - Top-level integration
- `nes_wishbone_bridge.v` - CDC bridge to LiteX/SDRAM
- `nes_chr_cache.v` - 32KB CHR-ROM cache
- `nes_prg_fixed_bank.v` - 16KB PRG-ROM fixed bank cache
- `nes_mapper_mmc3.v` - MMC3 mapper (to port from MiSTer)

## External Components (To Harvest)

- **T65** - 6502 CPU core from fpganes/T65
- **PPU** - NES PPU from iandailis/NES-FPGA (requires modifications)

## Usage

Include these modules in your NES core top-level. See `../plan/` for integration details.

## Simulation

```bash
# Compile and run testbench
iverilog -o sim tb/test_<module>.v <module>.v
vvp sim
gtkwave dump.vcd
```
