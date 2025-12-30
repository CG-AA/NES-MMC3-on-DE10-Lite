# Phase 2: Minimal NES Core

**Goal:** 6502 CPU executes code from BRAM, PPU shows graphics on VGA.

## Success Criteria

- [ ] 6502 runs test program (LED toggle)
- [ ] PPU outputs to VGA (any pattern)
- [ ] Donkey Kong (NROM) shows title screen

## Strategy: BRAM Only, No SDRAM

For Phase 2, **everything runs from BRAM**:
- PRG-ROM: 32KB BRAM
- CHR-ROM: 8KB BRAM
- No mapper, no bank switching (NROM only)
- No Wishbone bridge needed

This tests the NES core in isolation before adding SDRAM complexity.

## Steps

### 1. Get T65 6502 Core

```bash
cd /home/cg/risc-v_on_de10-lite/nes/rtl
git clone https://github.com/fpganes/T65.git
# Or copy just T65.vhd / T65_Pack.vhd / T65_MCode.vhd
```

### 2. Get PPU Core

```bash
git clone https://github.com/iandailis/NES-FPGA.git
# Copy PPU-related files
```

### 3. Create Minimal nes_top.v

Wire together:
- T65 CPU
- PPU from iandailis
- 2KB internal RAM (existing)
- 32KB PRG BRAM (new, preloaded with ROM)
- 8KB CHR BRAM (new, preloaded with ROM)
- Clock generator (existing)
- Address decoder (existing)

### 4. Test with LED Toggle Program

Before loading a game, test with a simple 6502 program:

```asm
; Reset vector points here
reset:
    lda #$01
loop:
    sta $FF       ; Write to some address (triggers LED)
    eor #$01      ; Toggle
    jmp loop
```

### 5. Load Donkey Kong

Donkey Kong is NROM (mapper 0):
- PRG-ROM: 32KB (fits in BRAM)
- CHR-ROM: 8KB (fits in BRAM)
- No bank switching

## What NOT To Do

- No SDRAM integration
- No ROM loader from UART
- No MMC3 mapper
- No optimization

## Files to Create

| File | Purpose |
|:-----|:--------|
| `rtl/nes_top.v` | Top-level wiring |
| `rtl/nes_prg_bram.v` | 32KB PRG BRAM |
| `rtl/nes_chr_bram.v` | 8KB CHR BRAM |

## External Components

| Component | Source | Status |
|:----------|:-------|:-------|
| T65 6502 | github.com/fpganes/T65 | Get it |
| PPU | github.com/iandailis/NES-FPGA | Get it |

## Next Phase

Once Donkey Kong boots → Phase 3: Add SDRAM for larger ROMs

---

## Reference (Archived Details)

### Implement PPU Latch (Open Bus)
```verilog
// Reading write-only registers returns last PPU write
reg [7:0] ppu_latch;
always @(posedge clk) 
    if (ppu_cs && cpu_write) 
        ppu_latch <= cpu_data_in;

// Return latch for $2000, $2001, $2003, $2005, $2006
```

### VGA Centering
```verilog
// Add back porch offset to center 512px in 640px
parameter H_OFFSET = 64;  // ~64 pixels offset
assign vga_h_pos = h_count + H_OFFSET;
```

**Verify:** $2007 read buffer behavior preserved

## 2. CPU Selection

**Requirement:** Full bus mastering support (halt during read AND write cycles)

### Option A: T65 (Recommended)
**Source:** https://github.com/fpganes/T65

**Interface:**
```verilog
T65 cpu (
    .Clk(clk),
    .Enable(cpu_enable),      // Gates ALL cycles
    .Rdy(1'b1),               // Tie high, use Enable
    .Res_n(~cpu_rst),
    .IRQ_n(cpu_irq_n),
    .NMI_n(cpu_nmi_n),
    .R_W_n(cpu_rw_n),
    .A(cpu_addr),
    .DI(cpu_data_in),
    .DO(cpu_data_out)
);

assign cpu_enable = cpu_clk_en && ~dma_halt;
```

**Pros:** Simple Enable control, proven in fpganes project

### Option B: MiSTer 6502
**Source:** https://github.com/MiSTer-devel/NES_MiSTer

**Pros:** Used in production MiSTer NES core, well-tested

**Cons:** Requires extraction from larger codebase

**Do NOT use:** Arlet 6502 (RDY only stalls reads, breaks DMA)

## 3. DMA Controller

**Location:** `rtl/nes_dma_controller.v` ✅ IMPLEMENTED

**Function:** OAM DMA with full bus mastering

**Features:**
- Triggered by write to $4014
- Halts CPU completely (Enable=0)
- Takes control of address/data bus
- Performs 256 read-write pairs ($XX00-$XXFF → $2004)
- Aligns to odd CPU cycle
- Returns bus control when done
- **READ_WAIT state** ensures memory response before data latch

**State Machine:**
```
IDLE → ALIGN → READ → READ_WAIT → WRITE → (loop or DONE)
```

**Interface:**
```verilog
// Inputs
input  wire        oam_dma_trigger,
input  wire [7:0]  oam_dma_page,
input  wire [7:0]  bus_data_in,
input  wire        mem_ack,       // Memory acknowledge for variable-latency sources

// Outputs
output reg         dma_active,
output reg  [15:0] dma_addr,
output reg  [7:0]  dma_data,
output reg         dma_read,      // Assert during read cycle
output reg         dma_write,     // Assert during write cycle
output wire        cpu_halt
```

**Memory acknowledge routing:**
```verilog
// Generate mem_ack based on DMA source address
wire dma_source_is_ram = (dma_addr < 16'h2000);
wire dma_source_is_prg_ram = (dma_addr >= 16'h6000) && (dma_addr < 16'h8000);

// BRAM sources: immediate ack
// SDRAM sources (PRG-RAM): wait for bridge ack
wire dma_mem_ack = dma_source_is_ram ? 1'b1 :           // Internal RAM (BRAM)
                   dma_source_is_prg_ram ? bridge_ack :  // PRG-RAM (SDRAM)
                   1'b1;                                 // Other (shouldn't happen)
```

**Bus multiplexer:**
```verilog
wire [15:0] active_addr = dma_active ? dma_addr : cpu_addr;
wire [7:0]  active_data = dma_active ? dma_data : cpu_data_out;
wire        active_rw   = dma_active ? ~dma_write : cpu_rw_n;
```

## 4. APU Stub

**Location:** `rtl/nes_apu_stub.v` ✅ IMPLEMENTED

**Function:** Frame counter only (no audio output)

**Features:**
- Frame counter IRQ (4-step and 5-step modes)
- $4015 read returns frame IRQ status
- $4017 write controls mode and IRQ inhibit
- Cycle-accurate timing (7457, 14913, 22371, 29829, 37281)
- Advances on `cpu_clk_en` only (no separate `cpu_rdy` needed)

**Interface:**
```verilog
input  wire        clk,
input  wire        rst,
input  wire        cpu_clk_en,    // Frame counter advances on this enable
input  wire        apu_cs,
input  wire [4:0]  apu_addr,
input  wire        apu_wr,
input  wire [7:0]  apu_wr_data,
output wire [7:0]  apu_rd_data,
output reg         frame_irq_n
```

## 5. Mapper (MMC3)

**Source:** MiSTer-devel/NES_MiSTer (extract MMC3.sv)

**Required adaptations:**
- Convert SystemVerilog to Verilog if needed
- Adapt interface to match our bus structure
- Connect PPU A12 to scanline counter
- Expose PRG/CHR bank select outputs

**Interface:**
```verilog
input  wire        cpu_write,
input  wire [15:0] cpu_addr,
input  wire [7:0]  cpu_data,
input  wire        ppu_a12,        // Scanline counter
output wire [2:0]  prg_bank_select,
output wire [7:0]  chr_bank_select [0:7],
output wire        irq_n
```

## 6. Address Decoder

**Location:** `rtl/nes_addr_decode.v` ✅ IMPLEMENTED

**Function:** Decode NES memory map to chip selects

**Regions:**
```verilog
// $0000-$1FFF: Internal RAM (2KB mirrored to 8KB)
output wire ram_cs,

// $2000-$2007: PPU registers (mirrored to $3FFF)
output wire ppu_cs,

// $4000-$4013: APU registers
output wire apu_cs,

// $4014: OAM DMA
output wire oam_dma_cs,

// $4016-$4017: Controller
output wire ctrl_cs,

// $6000-$7FFF: PRG-RAM
output wire prg_ram_cs,

// $8000-$FFFF: PRG-ROM (read)
output wire prg_rom_cs,

// $8000-$FFFF: Mapper registers (write)
// MMC3 bank switching, IRQ control, mirroring
output wire mapper_cs
```

## 7. Controller

**Location:** `rtl/nes_controller.v`

**Function:** Shift register for reading button states

**Interface:**
```verilog
module nes_controller (
    input  wire        clk,
    input  wire        rst,
    input  wire        cpu_clk_en,
    
    // CPU interface
    input  wire        ctrl_cs,
    input  wire        ctrl_wr,
    input  wire        ctrl_rd,
    input  wire        addr_bit,     // 0=$4016, 1=$4017
    output wire [7:0]  ctrl_data,
    
    // External button inputs (directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly from host via CSR or directly from directly directly directly directly directly directly directly GPIO)
    input  wire [7:0]  buttons_p1,   // A,B,Sel,Start,U,D,L,R
    input  wire [7:0]  buttons_p2
);
```

**Operation:**
- Write to $4016 bit 0: Strobe (1=load, 0=enable shifting)
- Read $4016: Shift out P1 buttons, bit 0
- Read $4017: Shift out P2 buttons, bit 0
- Bits 1-7 of read are open bus (return 0 or latch)

**Features:**
- $4016: Strobe and read button states
- 8-bit shift register (A, B, Select, Start, Up, Down, Left, Right)
- Input from UART or GPIO

## Verification Checklist

- [ ] T65 or MiSTer 6502 compiles
- [ ] CPU halts when Enable=0 (read AND write)
- [ ] DMA completes 256 transfers
- [ ] DMA controls bus during transfer
- [ ] PPU $2002 read clears VBlank flag
- [ ] PPU $2007 read buffer works
- [ ] APU frame IRQ fires at correct cycles
- [ ] Controller returns 8 button states
- [ ] PPU A12 exposed for mapper
- [ ] PPU NMI signal connected
- [ ] PPU latch implements open bus
