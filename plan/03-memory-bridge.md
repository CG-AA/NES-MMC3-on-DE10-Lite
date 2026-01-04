# Phase 3: SDRAM Integration

**Goal:** Load ROMs larger than BRAM via UART, run from SDRAM.

**Status:** Not Started

**Prerequisites:** Phase 2 complete (Donkey Kong title screen working ✅)

---

## Success Criteria

- [ ] LiteX BIOS SDRAM test passes (fix current 256/256 errors)
- [ ] Upload ROM via UART to SDRAM
- [ ] Read back and verify (no corruption)
- [ ] Run NROM game loaded from SDRAM
- [ ] PRG-ROM served from SDRAM (CPU stalls during fetch)

---

## Current Situation

### What Works
- DE10-Lite basic LiteX build with VexRiscv
- UART communication (115200 baud)
- Pure Verilog NES core (T65 + VGA-sync PPU)

### What Doesn't Work
- SDRAM memtest fails: "256/256 errors"
- Likely issues: SDRAM PHY timing, wrong module parameters

### SDRAM Chip Details
DE10-Lite has IS42S16320D-7TL:
- 32M x 16 bits (64 MB total)
- 16-bit data bus
- 3.3V, 143 MHz max
- CAS latency: 2 or 3

---

## Strategy: Fix SDRAM First

Before building NES→SDRAM bridge, must fix the basic SDRAM interface.

### Step 1: Debug SDRAM PHY

1. Check LiteX SDRAM module selection
2. Verify timing parameters match IS42S16320D
3. Try different CAS latency settings
4. Use LiteScope to capture SDRAM signals

### Step 2: Simple Integration

Once SDRAM works:
- Synchronous bridge (no async CDC initially)
- CPU stalls on every PRG-ROM read
- CHR-ROM stays in BRAM (avoids PPU timing issues)

---

## Implementation Steps

### 1. Fix LiteX SDRAM

```python
# Check current configuration in de10lite target
# May need custom PHY timing for IS42S16320D
```

### 2. Add CSRs for ROM Loading

```python
class NESControl(Module, AutoCSR):
    def __init__(self):
        self.reset = CSRStorage(1, description="NES reset")
        self.prg_addr = CSRStorage(19, description="PRG write address")
        self.prg_data = CSRStorage(8, description="PRG write data")
        self.prg_wr = CSR(1, description="Trigger PRG write")
```

### 3. Create Simple Wishbone Bridge

```verilog
module nes_wishbone_bridge (
    // NES clock domain
    input  wire        nes_clk,
    input  wire        nes_reset,
    
    // NES PRG-ROM interface
    input  wire [18:0] nes_addr,      // 512KB max
    input  wire        nes_rd,
    output wire [7:0]  nes_data,
    output wire        nes_ready,     // CPU stalls until high
    
    // Wishbone master (LiteX clock domain)
    input  wire        wb_clk,
    output wire [31:0] wb_adr_o,
    output wire        wb_stb_o,
    output wire        wb_cyc_o,
    input  wire [31:0] wb_dat_i,
    input  wire        wb_ack_i
);
```

### 4. Gate CPU on SDRAM Access

```verilog
// CPU only advances when memory is ready
wire prg_from_sdram = addr16[15] && use_sdram;
wire cpu_enable = cpu_clk_en && ~dma_halt && 
                  (prg_from_sdram ? sdram_ready : 1'b1);
```

### 5. ROM Loader Script

```python
def load_nes_rom(filename, csr):
    """Upload NES ROM to SDRAM via LiteX CSRs"""
    with open(filename, 'rb') as f:
        header = f.read(16)
        prg_size = header[4] * 16384
        chr_size = header[5] * 8192
        
        # Upload PRG to SDRAM
        prg_data = f.read(prg_size)
        for i, byte in enumerate(prg_data):
            csr.nes_prg_addr.write(i)
            csr.nes_prg_data.write(byte)
            csr.nes_prg_wr.write(1)
        
        # Upload CHR to BRAM (for now)
        # ...
        
        # Release NES reset
        csr.nes_reset.write(0)
```

---

## What NOT To Do (Yet)

- ❌ Async CDC (add only if clock domain issues appear)
- ❌ Latency optimization (add only if games are too slow)
- ❌ CHR-ROM from SDRAM (keep in BRAM for PPU timing)
- ❌ PRG-RAM (save game support) - future enhancement
- ❌ MMC3 bank switching - that's Phase 4

---

## Memory Map

### SDRAM Layout
```
0x40000000 - 0x4007FFFF: PRG-ROM (512KB max)
0x40080000 - 0x400FFFFF: Reserved for expansion
```

### NES Address Mapping
```
$8000-$FFFF: 32KB window into SDRAM PRG-ROM
             For larger ROMs, mapper handles bank switching
```

---

## Risk Assessment

| Risk | Mitigation |
|:-----|:-----------|
| SDRAM PHY timing issues | Use LiteScope, try different settings |
| CPU stalls too slow | Cache frequently accessed banks |
| Clock domain crossing | Use proper CDC synchronizers |
| UART too slow for large ROMs | ~30 seconds for 512KB, acceptable |

---

## Dependencies

### From LiteX
- Working SDRAM controller
- CSR infrastructure
- Wishbone interconnect

### From NES Core
- CPU Enable signal (already exists)
- Address decode for $8000-$FFFF (already exists)

---

## Estimated Effort

| Task | Effort |
|:-----|:-------|
| Debug SDRAM PHY | 2-4 hours |
| Add CSRs | 1 hour |
| Wishbone bridge | 2-3 hours |
| ROM loader script | 1 hour |
| Integration & testing | 2-3 hours |

**Total: 8-12 hours**

---

## Next Phase

Once NROM loads from SDRAM → Phase 4: MMC3 Mapper
