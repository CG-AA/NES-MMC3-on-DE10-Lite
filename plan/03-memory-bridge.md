# Phase 3: SDRAM Integration

**Goal:** Load ROMs larger than BRAM via UART, run from SDRAM.

## Success Criteria

- [ ] Upload ROM via UART to SDRAM
- [ ] Read back and verify (no corruption)
- [ ] Run NROM game loaded from SDRAM
- [ ] PRG-ROM served from SDRAM (CPU stalls during fetch)

## Strategy: Simple First

Start with the simplest bridge that works:
- Synchronous bridge (no async CDC yet)
- CPU stalls on every PRG-ROM read
- CHR-ROM still in BRAM (avoids PPU timing issues)

Optimize only if it's too slow.

## Steps

### 1. Add CSRs for ROM Loading

Extend LiteX SoC with:
```python
# nes_control: bit 0 = NES reset
# nes_sdram_addr: write address
# nes_sdram_data: write data (triggers write)
```

### 2. Create Simple Wishbone Bridge

```verilog
module nes_wishbone_bridge (
    // NES side (directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly clocked)
    input  wire [15:0] nes_addr,
    input  wire        nes_rd,
    output wire [7:0]  nes_data,
    output wire        nes_ready,  // CPU stalls until this is high
    
    // Wishbone master
    output wire [31:0] wb_adr_o,
    output wire        wb_stb_o,
    input  wire [31:0] wb_dat_i,
    input  wire        wb_ack_i
);
```

### 3. Gate CPU on SDRAM Access

```verilog
// CPU only advances when memory is ready
wire cpu_enable = cpu_clk_en && ~dma_halt && 
                  (prg_rom_cs ? sdram_ready : 1'b1);
```

### 4. Write ROM Loader

Python script to:
1. Parse iNES header
2. Upload PRG-ROM to SDRAM via LiteX CSRs
3. Upload CHR-ROM to BRAM (still fits for NROM)
4. Release NES reset

## What NOT To Do

- Don't implement async CDC yet
- Don't optimize latency
- Don't implement CHR cache bank-swapping
- Don't implement PRG fixed bank cache

## Memory Map (Simple)

```
SDRAM 0x40000000: PRG-ROM (up to 512KB)
BRAM:             CHR-ROM (up to 8KB for now)
```

## Next Phase

Once NROM loads from SDRAM → Phase 4: Add MMC3 mapper

---

## Reference (Deferred Details)

Async CDC, arbitration, and caching strategies are documented
in the archived version but not needed until we hit problems.
