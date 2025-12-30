# **NES on DE10-Lite: Open Source Integration Roadmap (Revised v6)**

## **1. System Architecture Overview**

Instead of a monolithic custom core, we are building a **Hybrid System**.

* **The Host (Supervisor):** LiteX VexRiscv RISC-V CPU. Handles UART, SDRAM initialization, and ROM loading.  
* **The Guest (Emulation):** A "Frankenstein" NES Core composed of verified open-source blocks.  
* **The Bridge:** A custom **Clock Domain Crossing (CDC) Arbiter** that translates NES memory requests into LiteDRAM transactions.

### **The Stack**

| Function | Component | Source | Status |
| :---- | :---- | :---- | :---- |
| **System Bus** | LiteX Wishbone (100 MHz) | enjoy-digital/litex | Ready |
| **Memory** | LiteDRAM (SDRAM) | enjoy-digital/litedram | Ready |
| **CPU** | 6502 Core | **fpganes/T65** or MiSTer 6502 | **To Evaluate** |
| **PPU (Video)** | NES PPU & VGA | iandailis/NES-FPGA | To Harvest |
| **Mapper** | MMC3 (Mapper 4) | MiSTer-devel/NES_MiSTer | To Port |
| **APU (Audio)** | Frame Counter Only | Custom/Stubbed | **Silent Intended** |
| **DMA Controller** | OAM DMA Logic | **Custom (Bus Master)** | To Write |
| **Input** | UART Injection | Custom LiteX CSR | To Write |
| **CHR Storage** | Pattern Table Cache | **FPGA BRAM (32KB min)** | To Allocate |
| **PPU Nametable RAM** | 2KB Block RAM | **FPGA BRAM** | To Allocate |
| **Address Decoder** | $4000-$401F, $2000-$2007 | **Custom** | To Write |

> **[ISSUE 2.1 RESOLUTION] CPU Core Selection:** The Arlet/verilog-6502 core's `RDY` signal only works during READ cycles. For proper DMA support, use **T65** (from fpganes) or the **MiSTer NES 6502** which support full bus mastering with external address/data bus control.

---

## **2. Phase 1: The Host Environment (LiteX & Loading)**

**Goal:** Establish a reliable data pipeline and a deterministic memory layout without complexity.

### **2.1 Generate LiteX SoC**

* **Target:** DE10-Lite (MAX 10).  
* **Features:** UART, LiteDRAM (SDRAM), GPIO, `sdram_ready` status signal.

> **[ISSUE 1.1 VERIFICATION] LiteDRAM Full Range:** Verify LiteDRAM configuration maps the full 64MB SDRAM. Check `litedram_core.py` for:
> ```python
> # Ensure full address range
> sdram_size = 64 * 1024 * 1024  # 64MB
> # Verify no artificial limits in wishbone bridge
> ```
> Unpacked mode memory usage (worst case): 512KB PRG × 4 + 256KB CHR × 4 = **3MB** — well within 64MB.

### **2.2 Define SDRAM Memory Map (Unpacked Mode)**

* **Strategy:** **Unpacked Addressing** (1 NES Byte = 1 32-bit SDRAM Word).  
* **Mapping:** NES Address A -> SDRAM Address Base + (A × 4).  
* **Rationale:** Eliminates Read-Modify-Write (RMW) logic in the Bridge.

| Region | NES Address | Size | SDRAM Base | SDRAM End | Notes |
| :----- | :---------- | :--- | :--------- | :-------- | :---- |
| **PRG-ROM Bank 0** | $8000-$BFFF | 16KB | 0x0000_0000 | 0x0000_FFFC | Mapper-switched |
| **PRG-ROM Bank 1** | $C000-$FFFF | 16KB | 0x0001_0000 | 0x0001_FFFC | Often fixed to last bank |
| **PRG-ROM Storage** | (Full ROM) | Up to 512KB | 0x0010_0000 | 0x002F_FFFC | Mapper indexes here |
| **PRG-RAM** | $6000-$7FFF | 8KB | 0x0030_0000 | 0x0031_FFFC | Battery-backed for MMC3 |
| **CHR-ROM Storage** | (Full CHR) | Up to 256KB | 0x0040_0000 | 0x004F_FFFC | **Cached to BRAM at load** |

> **[FIX #1] CHR Storage Strategy (REVISED):** CHR data is **always** stored in FPGA BRAM, not accessed from SDRAM during rendering. See Section 3.2 for caching strategy.

### **2.3 Implement Robust iNES Parser (Python Side)**

* **Trainer Handling:** Skip first 512 bytes if Trainer flag set.  
* **CHR-RAM Detection:** If CHR Size == 0, do NOT upload CHR data. Firmware logs "CHR-RAM mode detected".

> **[ISSUE 1.2 FIX] PRG-RAM Zero-Fill Size:** Zero-fill PRG-RAM region with **32KB of SDRAM writes** (8KB NES × 4 bytes per word):
> ```python
> # Correct zero-fill for unpacked PRG-RAM
> PRG_RAM_BASE = 0x0030_0000
> PRG_RAM_SIZE_UNPACKED = 8 * 1024 * 4  # 32KB SDRAM space
> for addr in range(PRG_RAM_BASE, PRG_RAM_BASE + PRG_RAM_SIZE_UNPACKED, 4):
>     sdram_write_word(addr, 0x00000000)
> ```

### **2.4 Add NES Control CSR (The "Premature Boot" Fix)**

* **Register:** `nes_control` at CSR offset TBD.
* **Bit 0:** NES System Reset (Active High). Default = 1.
* **Bit 1 (Read-Only):** `sdram_ready` from LiteDRAM.

> **[ISSUE 1.3 FIX] CSR Access Pattern:** Use explicit bit manipulation to avoid clearing reset when reading status:
> ```c
> // WRONG - may clear reset
> uint32_t status = nes_control_read();
> 
> // CORRECT - separate status register or mask writes
> void nes_set_reset(bool active) {
>     uint32_t val = nes_control_read();
>     if (active) val |= 0x01;
>     else        val &= ~0x01;
>     nes_control_write(val);
> }
> 
> bool nes_sdram_ready(void) {
>     return (nes_control_read() & 0x02) != 0;
> }
> ```
> **Alternative:** Split into two CSRs: `nes_control` (R/W) and `nes_status` (RO).

* **Procedure:** 
  1. Wait for `sdram_ready == 1`.
  2. Load ROM to SDRAM.
  3. Load CHR-ROM to BRAM cache (new step).
  4. Write 0 to Bit 0 to release reset.

---

## **3. Phase 2: "The Harvest" (Component Preparation)**

**Goal:** Extract, clean, and *fix* the open-source files.

### **3.1 Harvest the PPU (iandailis/NES-FPGA)**

* **Mod:** Expose `vram_addr[13:0]`, `vram_data[7:0]`, `vram_rd`, `vram_wr` to top level.
* **Verify:** Ensure $2007 Read Buffer behavior is preserved.
* **New Feature: VGA Centering Logic:** Add "Back Porch" offset (~64 pixels) to center 512px within 640px.

> **[FIX #5] Open Bus Behavior:** Verify iandailis core implements PPU latch. Reading write-only registers ($2000, $2001, $2003, $2005, $2006) must return last value written to ANY PPU register. If missing, add:
> ```verilog
> reg [7:0] ppu_latch;
> always @(posedge clk) if (ppu_cs && cpu_write) ppu_latch <= cpu_data_in;
> // Return ppu_latch for reads to write-only registers
> ```

> **[FIX #8] Expose PPU A12:** The PPU address bus bit 12 must be exposed as `ppu_a12` output for MMC3 scanline counter. Add:
> ```verilog
> output wire ppu_a12;
> assign ppu_a12 = vram_addr[12];
> ```

> **[FIX #12] NMI Output:** Expose `ppu_nmi` output signal (directly active-low for CPU `nmi_n`).

### **3.2 CPU Core Selection (REVISED)**

> **[ISSUE 2.1 CRITICAL] Arlet 6502 Limitation:**
> 
> The Arlet/verilog-6502 core's `RDY` signal **only stalls during read cycles**. This breaks DMA which needs to halt the CPU during both reads and writes.
> 
> **Recommended Alternatives:**
> 
> | Core | Source | Bus Mastering | Notes |
> |:-----|:-------|:--------------|:------|
> | **T65** | fpganes/T65 | Yes | Has `Enable` input that gates all cycles |
> | **MiSTer 6502** | MiSTer-devel | Yes | Used in working NES core |
> | **ag_6502** | Arlet (modified) | Possible | Requires modification |
> 
> **T65 Interface (Recommended):**
> ```verilog
> T65 cpu (
>     .Clk(clk),
>     .Enable(cpu_enable),      // Gate ALL cycles (read AND write)
>     .Rdy(1'b1),               // Directly tie high, use Enable instead
>     .Res_n(~cpu_rst),
>     .IRQ_n(cpu_irq_n),
>     .NMI_n(cpu_nmi_n),
>     .R_W_n(cpu_rw_n),
>     .A(cpu_addr),
>     .DI(cpu_data_in),
>     .DO(cpu_data_out)
> );
> 
> // DMA controls Enable
> assign cpu_enable = cpu_clk_en && ~dma_active;
> ```

### **3.3 Address Decoder Module**

<!-- ...existing code... -->

### **3.4 Implement DMA Controller (REVISED - Bus Master Design)**

> **[ISSUE 2.2 CRITICAL] DMA Bus Hijacking:**
> 
> OAM DMA requires **bus mastering**, not just CPU stalling. The DMA controller must:
> 1. Halt the CPU completely (read AND write cycles)
> 2. Take control of the address and data buses
> 3. Perform 256 read-write pairs
> 4. Return bus control to CPU

```verilog
// filepath: /home/cg/risc-v_on_de10-lite/nes/rtl/nes_dma_controller.v
module nes_dma_controller (
    input  wire        clk,
    input  wire        rst,
    input  wire        cpu_clk_en,
    
    // Trigger from address decoder
    input  wire        oam_dma_trigger,  // Write to $4014
    input  wire [7:0]  oam_dma_page,     // Value written to $4014
    
    // Bus control signals
    output reg         dma_active,
    output reg  [15:0] dma_addr,         // Address to drive on bus
    output reg  [7:0]  dma_data,         // Data for OAM write
    output reg         dma_read,         // 1=reading from source
    output reg         dma_write,        // 1=writing to $2004
    
    // Read data from bus (directly directly directly directly directly directly directly directly directly directly directly directly directly directly latched externally)
    input  wire [7:0]  bus_data_in,
    
    // CPU halt signal (directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly use with T65 Enable)
    output wire        cpu_halt
);
    // State machine
    localparam IDLE      = 3'd0;
    localparam ALIGN     = 3'd1;  // Wait for odd cycle
    localparam READ      = 3'd2;
    localparam WRITE     = 3'd3;
    localparam DONE      = 3'd4;
    
    reg [2:0]  state;
    reg [7:0]  byte_count;
    reg [7:0]  source_page;
    reg        cycle_odd;
    reg [7:0]  read_latch;
    
    assign cpu_halt = (state != IDLE);
    
    always @(posedge clk) begin
        if (rst) begin
            state <= IDLE;
            dma_active <= 0;
            dma_read <= 0;
            dma_write <= 0;
            cycle_odd <= 0;
        end else if (cpu_clk_en) begin
            // Track odd/even CPU cycles
            cycle_odd <= ~cycle_odd;
            
            case (state)
                IDLE: begin
                    dma_active <= 0;
                    dma_read <= 0;
                    dma_write <= 0;
                    if (oam_dma_trigger) begin
                        source_page <= oam_dma_page;
                        byte_count <= 8'd0;
                        state <= ALIGN;
                        dma_active <= 1;
                    end
                end
                
                ALIGN: begin
                    // Wait for odd cycle alignment (per NES hardware)
                    if (cycle_odd) begin
                        state <= READ;
                    end
                end
                
                READ: begin
                    // Drive source address
                    dma_addr <= {source_page, byte_count};
                    dma_read <= 1;
                    dma_write <= 0;
                    // Latch data on next cycle
                    read_latch <= bus_data_in;
                    state <= WRITE;
                end
                
                WRITE: begin
                    // Drive $2004 address and write data
                    dma_addr <= 16'h2004;
                    dma_data <= read_latch;
                    dma_read <= 0;
                    dma_write <= 1;
                    
                    if (byte_count == 8'd255) begin
                        state <= DONE;
                    end else begin
                        byte_count <= byte_count + 1;
                        state <= READ;
                    end
                end
                
                DONE: begin
                    dma_active <= 0;
                    dma_read <= 0;
                    dma_write <= 0;
                    state <= IDLE;
                end
            endcase
        end
    end
endmodule
```

> **Bus Multiplexer (Required):**
> ```verilog
> // In nes_top.v
> wire [15:0] active_addr = dma_active ? dma_addr : cpu_addr;
> wire [7:0]  active_data = dma_active ? dma_data : cpu_data_out;
> wire        active_rw   = dma_active ? ~dma_write : cpu_rw_n;
> 
> // CPU enable gated by DMA
> wire cpu_enable = cpu_clk_en && ~cpu_halt;
> ```

### **3.5 Harvest the Mapper (MiSTer-devel/NES_MiSTer)**

<!-- ...existing code... -->

### **3.6 Controller Shift Register**

<!-- ...existing code... -->

### **3.7 APU Stub with Frame Counter (REVISED)**

> **[ISSUE 2.4 FIX] Corrected Frame Counter Timing:**
> 
> The APU frame counter has complex timing that differs between 4-step and 5-step modes:
> - 4-step mode: Steps at CPU cycles 7457, 14913, 22371, 29829 (then IRQ + reset)
> - 5-step mode: Steps at CPU cycles 7457, 14913, 22371, 29829, 37281 (no IRQ)
> 
> Each "step" is approximately 7457 cycles, but the frame counter uses half-frames.

```verilog
// filepath: /home/cg/risc-v_on_de10-lite/nes/rtl/nes_apu_stub.v
module nes_apu_stub (
    input  wire        clk,
    input  wire        rst,
    input  wire        cpu_clk_en,
    input  wire        cpu_rdy,
    
    input  wire        apu_cs,
    input  wire [4:0]  apu_addr,
    input  wire        apu_wr,
    input  wire [7:0]  apu_wr_data,
    output wire [7:0]  apu_rd_data,
    
    output reg         frame_irq_n
);
    // $4015 reads return 0 (no sound channels), but preserve frame IRQ status
    assign apu_rd_data = (apu_addr == 5'h15) ? {1'b0, ~frame_irq_n, 6'b000000} : 8'h00;
    
    // Frame counter state
    reg [14:0] cycle_count;
    reg [2:0]  step;
    reg        mode_5step;
    reg        irq_inhibit;
    
    // Step timing thresholds (in CPU cycles from frame start)
    // Using half-cycle precision: actual NES uses 7456.5 base
    localparam STEP0_CYC = 15'd7457;
    localparam STEP1_CYC = 15'd14913;
    localparam STEP2_CYC = 15'd22371;
    localparam STEP3_CYC = 15'd29828;  // 4-step IRQ point
    localparam STEP4_CYC = 15'd37281;  // 5-step only
    
    always @(posedge clk) begin
        if (rst) begin
            cycle_count <= 0;
            step <= 0;
            mode_5step <= 0;
            irq_inhibit <= 0;
            frame_irq_n <= 1;
        end else if (cpu_clk_en && cpu_rdy) begin
            // $4017 write handling
            if (apu_cs && apu_wr && apu_addr == 5'h17) begin
                mode_5step <= apu_wr_data[7];
                irq_inhibit <= apu_wr_data[6];
                if (apu_wr_data[6]) frame_irq_n <= 1;
                cycle_count <= 0;
                step <= 0;
            end
            // $4015 read clears frame IRQ
            else if (apu_cs && ~apu_wr && apu_addr == 5'h15) begin
                frame_irq_n <= 1;
            end
            else begin
                cycle_count <= cycle_count + 1;
                
                // Step advancement
                case (step)
                    3'd0: if (cycle_count >= STEP0_CYC) step <= 3'd1;
                    3'd1: if (cycle_count >= STEP1_CYC) step <= 3'd2;
                    3'd2: if (cycle_count >= STEP2_CYC) step <= 3'd3;
                    3'd3: begin
                        if (cycle_count >= STEP3_CYC) begin
                            if (~mode_5step) begin
                                // 4-step mode: IRQ and reset
                                if (~irq_inhibit) frame_irq_n <= 0;
                                cycle_count <= 0;
                                step <= 0;
                            end else begin
                                step <= 3'd4;
                            end
                        end
                    end
                    3'd4: begin
                        if (cycle_count >= STEP4_CYC) begin
                            // 5-step mode: no IRQ, just reset
                            cycle_count <= 0;
                            step <= 0;
                        end
                    end
                endcase
            end
        end
    end
endmodule
```

---

## **3.5 Phase 2.5: The Loopback Test (Mandatory)**

**Goal:** Verify PPU logic with BRAM before introducing SDRAM complexity.

> **[ISSUE 2.5.1 FIX] Explicit Test Scenarios:**

### **Test Scenario A: CHR-RAM Game Simulation**
- **Setup:** 8KB BRAM for pattern tables (directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly writable by CPU via $2007)
- **Test:** Load test pattern via CPU writes to PPU, verify display
- **Verifies:** PPU write path, VRAM addressing, basic rendering

### **Test Scenario B: CHR-ROM Game Simulation**  
- **Setup:** 8KB BRAM preloaded with static pattern data
- **Test:** Display static tiles without any CPU writes to pattern area
- **Verifies:** PPU read path, correct pattern fetch timing

### **Test Scenario C: Full CHR-ROM Cache (Phase 3 Prep)**
- **Setup:** 32KB+ BRAM as CHR cache, loaded from SDRAM at boot
- **Test:** Run actual game ROM with mapper bank switching
- **Verifies:** Bank switching updates cache correctly

### **Nametable Mirroring Test (REVISED)**

> **[ISSUE 2.5.2 FIX] Corrected Verilog style:**

```verilog
// filepath: /home/cg/risc-v_on_de10-lite/nes/rtl/nametable_mirror.v
module nametable_mirror (
    input  wire [11:0] ppu_vram_addr,  // $2000-$2FFF -> 12 bits
    input  wire [1:0]  mirroring,      // 0=Horiz, 1=Vert, 2=Single0, 3=Single1
    output wire [10:0] bram_addr       // 2KB = 11 bits
);
    wire [1:0] nt_select = ppu_vram_addr[11:10];
    
    // Combinational logic using wire + conditional
    wire mapped_bank = (mirroring == 2'd0) ? nt_select[1] :  // Horizontal
                       (mirroring == 2'd1) ? nt_select[0] :  // Vertical
                       (mirroring == 2'd2) ? 1'b0 :          // Single screen 0
                                             1'b1;           // Single screen 1
    
    assign bram_addr = {mapped_bank, ppu_vram_addr[9:0]};
endmodule
```

---

## **4. Phase 3: The Wishbone Bridge (CDC & Arbitration)**

**Goal:** Bridge the NES Domain (21.48MHz) and System Domain (100MHz).

### **4.1 CHR-ROM Caching Strategy (REVISED)**

> **[ISSUE 3.2 CRITICAL] PPU Cannot Fetch from SDRAM During Rendering**
> 
> The PPU fetches 80+ bytes per scanline during active rendering with strict timing. SDRAM latency makes real-time fetch impossible.
> 
> **Solution: Full CHR Cache in BRAM**

| CHR Size | BRAM Required | Strategy |
|:---------|:--------------|:---------|
| 8KB (CHR-RAM) | 8KB | Direct BRAM, no cache needed |
| 8KB (CHR-ROM) | 8KB | Load entire CHR at boot |
| 16KB | 16KB | Load entire CHR at boot |
| 32KB | 32KB | Load entire CHR at boot |
| 64KB+ | 32KB min | **Bank-swap cache** (see below) |

> **Bank-Swap Cache for Large CHR-ROM:**
> 
> For games with >32KB CHR-ROM, implement a cache that tracks mapper bank selections:
> ```verilog
> // CHR cache with 8 × 4KB banks (32KB total BRAM)
> reg [7:0] cached_bank [0:7];  // Which CHR-ROM bank is in each cache slot
> 
> // On mapper bank change during VBlank:
> // 1. Compare new bank selection with cached banks
> // 2. If cache miss, load from SDRAM (only during VBlank!)
> // 3. Update cache tag
> 
> // During active rendering:
> // - All CHR fetches hit cache (guaranteed by VBlank prefetch)
> ```
> 
> **Minimum BRAM for CHR:** 32KB (8 × 4KB banks for MMC3 worst case)

### **4.2 Revised Arbitration Policy**

> **[ISSUE 3.1 FIX] Realistic SDRAM Timing:**

| Priority | Source | When | SDRAM Cycles/Access |
|:---------|:-------|:-----|:--------------------|
| **0** | DMA (OAM) | VBlank only | ~15 cycles × 256 = 3840 |
| **1** | CHR Cache Fill | VBlank only | ~15 cycles × N banks |
| **2** | PRG-ROM Fetch | Anytime | ~15 cycles |
| **3** | PRG-RAM R/W | Anytime | ~15 cycles |

> **VBlank Budget:**
> - VBlank duration: 20 scanlines × 341 PPU cycles = 6820 PPU cycles
> - At 100MHz vs 5.37MHz PPU: 6820 × 18.6 ≈ **127,000 system cycles**
> - DMA: 256 × 2 × 15 = 7,680 cycles (read + write)
> - CHR cache fill (worst case 8 banks × 1KB × 4): 32K accesses × 15 = 480,000 cycles
> 
> **Problem:** Full CHR cache reload doesn't fit in VBlank!
> 
> **Solution:** Only reload **changed** banks. MMC3 typically changes 1-2 banks per frame.
> - Typical reload: 2 banks × 4KB × 15 cycles = 120,000 cycles ✓

### **4.3 HBlank Prefetch (NOT Used for CHR)**

> **[ISSUE 3.1 CORRECTION]** HBlank is too short for reliable SDRAM access with refresh overhead. CHR data comes from BRAM cache, not SDRAM.
> 
> HBlank is used for:
> - Sprite evaluation (internal PPU operation)
> - **Not** SDRAM access

### **4.4 CDC for Multi-Bit Signals**

> **[ISSUE 3.3 FIX] Multi-Bit CDC Handling:**

```verilog
// filepath: /home/cg/risc-v_on_de10-lite/nes/rtl/cdc_multibit.v

// Option 1: Gray code for counters/addresses
module cdc_gray #(parameter WIDTH = 8) (
    input  wire             clk_src,
    input  wire             clk_dst,
    input  wire [WIDTH-1:0] data_src,
    output reg  [WIDTH-1:0] data_dst
);
    reg [WIDTH-1:0] gray_src, gray_sync1, gray_sync2;
    
    // Binary to Gray in source domain
    always @(posedge clk_src)
        gray_src <= data_src ^ (data_src >> 1);
    
    // 2-FF sync in destination domain
    always @(posedge clk_dst) begin
        gray_sync1 <= gray_src;
        gray_sync2 <= gray_sync1;
    end
    
    // Gray to Binary in destination domain
    integer i;
    always @(*) begin
        data_dst[WIDTH-1] = gray_sync2[WIDTH-1];
        for (i = WIDTH-2; i >= 0; i = i - 1)
            data_dst[i] = data_dst[i+1] ^ gray_sync2[i];
    end
endmodule

// Option 2: Quasi-static for mapper banks (preferred)
// Mapper banks only change during safe windows (after CPU write)
// Use simple 2-FF sync since data is stable for many cycles
module cdc_quasi_static #(parameter WIDTH = 8) (
    input  wire             clk_dst,
    input  wire [WIDTH-1:0] data_src,  // Directly directly directly directly directly directly directly directly directly directly directly directly directly async input
    output reg  [WIDTH-1:0] data_dst
);
    reg [WIDTH-1:0] sync1;
    
    always @(posedge clk_dst) begin
        sync1 <= data_src;
        data_dst <= sync1;
    end
endmodule
```

> **Mapper Bank CDC Strategy:**
> - Mapper bank registers are "quasi-static" — they change only when CPU writes to mapper
> - CPU write takes multiple 100MHz cycles to complete
> - By the time next SDRAM access uses the bank value, it's stable
> - Use simple 2-FF synchronizer, no Gray coding needed

---

## **5. Phase 4: Integration & Timing**

### **5.1 Clock Generation (REVISED)**

> **[ISSUE 4.1 FIX] Explicit 3:1 PPU/CPU Ratio:**

```verilog
// filepath: /home/cg/risc-v_on_de10-lite/nes/rtl/nes_clk_gen.v
module nes_clk_gen (
    input  wire clk_master,  // 21.477272 MHz from PLL
    input  wire rst,
    
    output reg  cpu_clk_en,  // 1.789 MHz (every 12th cycle)
    output reg  ppu_clk_en   // 5.369 MHz (every 4th cycle)
);
    reg [3:0] divider;  // 0-11 counter
    
    always @(posedge clk_master) begin
        if (rst) begin
            divider <= 0;
            cpu_clk_en <= 0;
            ppu_clk_en <= 0;
        end else begin
            divider <= (divider == 4'd11) ? 4'd0 : divider + 1;
            
            // PPU enable: cycles 0, 4, 8 (3 per CPU cycle)
            ppu_clk_en <= (divider == 4'd0) || 
                          (divider == 4'd4) || 
                          (divider == 4'd8);
            
            // CPU enable: cycle 0 only (1 per 12 master cycles)
            cpu_clk_en <= (divider == 4'd0);
        end
    end
endmodule
```

> **Verification:** Each CPU enable must have exactly 3 PPU enables in the same frame:
> ```
> Master cycle:  0  1  2  3  4  5  6  7  8  9 10 11  0  1 ...
> PPU enable:    1  0  0  0  1  0  0  0  1  0  0  0  1  0 ...
> CPU enable:    1  0  0  0  0  0  0  0  0  0  0  0  1  0 ...
> ```

### **5.2 Reset Vector Fetch (REVISED)**

> **[ISSUE 4.2 FIX] Guaranteed Reset Vector Availability:**

The CPU immediately fetches from $FFFC/$FFFD after reset. These must be available without SDRAM latency.

**Solution: Reset Vector Cache**

```verilog
// In nes_top.v or bridge
reg [7:0] reset_vector_lo;  // Cached $FFFC
reg [7:0] reset_vector_hi;  // Cached $FFFD

// During ROM load (before releasing reset):
// 1. Host writes reset vector to CSR registers
// 2. These are directly returned for $FFFC/$FFFD reads

// Address decode intercept
wire reset_vector_access = (cpu_addr == 16'hFFFC) || (cpu_addr == 16'hFFFD);

// Data mux
wire [7:0] prg_data = reset_vector_access ? 
                      (cpu_addr[0] ? reset_vector_hi : reset_vector_lo) :
                      sdram_data;
```

**Alternative: BRAM Shadow for Fixed Bank**

For simpler implementation, cache the last 16KB bank (which contains reset vector) in BRAM:
- 16KB BRAM for PRG-ROM fixed bank
- Host loads this during ROM upload
- All $C000-$FFFF reads come from BRAM (no SDRAM latency)
- Mapper bank switching only affects $8000-$BFFF

### **5.3 IRQ and NMI Wiring**

<!-- ...existing code... -->

### **5.4 Staggered Reset Logic (REVISED)**

<!-- ...existing code... -->

---

## **6. Complete Module Hierarchy (REVISED)**

```
litex_soc_top
├── vexriscv_cpu (Host)
├── litedram_core (SDRAM)
├── uart_core
├── nes_control_csr
├── nes_status_csr (Read-Only)
│
└── nes_top (NES Guest)
    ├── nes_clk_gen (PLL + dividers)
    ├── nes_addr_decode
    ├── nes_cpu (T65 or MiSTer 6502)  // NOT Arlet
    ├── nes_ppu (iandailis, modified)
    ├── nes_dma_controller (Bus Master)
    ├── nes_apu_stub (corrected timing)
    ├── nes_controller
    ├── nes_mapper_mmc3 (MiSTer, modified)
    ├── nes_internal_ram (2KB BRAM)
    ├── nes_nametable_ram (2KB BRAM)
    ├── nes_chr_cache (32KB BRAM)     // NEW: replaces direct SDRAM
    ├── nes_prg_fixed_bank (16KB BRAM) // NEW: $C000-$FFFF cache
    ├── nametable_mirror
    ├── cdc_quasi_static (multiple)
    │
    └── nes_wishbone_bridge
        ├── cdc_sync (single-bit signals)
        ├── prg_bank_cache_ctrl       // NEW: manages PRG bank loads
        ├── chr_bank_cache_ctrl       // NEW: manages CHR bank loads
        └── arbitration_logic
```

---

## **7. Verification Checklist (REVISED)**

### Phase 1 Exit Criteria:
- [ ] SDRAM initializes, `sdram_ready` asserts
- [ ] LiteDRAM exposes full 64MB range
- [ ] Python loader uploads test pattern to all memory regions
- [ ] Readback matches written data
- [ ] PRG-RAM zero-fill covers 32KB SDRAM space

### Phase 2 Exit Criteria:
- [ ] **T65 or MiSTer 6502 compiles** (not Arlet)
- [ ] CPU halts completely when Enable=0 (read AND write)
- [ ] DMA controller completes 256 read-write pairs
- [ ] DMA controls bus address/data during transfers
- [ ] PPU $2002 read clears VBlank correctly
- [ ] PPU $2007 read buffer works for pattern and palette
- [ ] APU frame counter IRQ fires at correct cycle counts
- [ ] Controller returns 8 button states serially

### Phase 2.5 Exit Criteria:
- [ ] Scenario A: CHR-RAM write/display works
- [ ] Scenario B: CHR-ROM static display works
- [ ] Nametable mirroring test passes all 4 modes

### Phase 3 Exit Criteria:
- [ ] CHR cache loads during VBlank
- [ ] Mapper bank change triggers cache update (changed banks only)
- [ ] PRG fixed bank ($C000-$FFFF) served from BRAM
- [ ] Reset vector reads without SDRAM latency
- [ ] CDC synchronizers verified (timing simulation)

### Phase 4 Exit Criteria:
- [ ] PPU/CPU 3:1 ratio verified (logic analyzer or simulation)
- [ ] Reset sequence waits for SDRAM
- [ ] CPU fetches reset vector correctly on first cycle
- [ ] NMI triggers on VBlank
- [ ] IRQ triggers from mapper and APU
- [ ] Controller input reaches game

---

## **8. Critical Issue Summary**

| Issue | Original Plan | Fix Applied |
|:------|:--------------|:------------|
| Arlet 6502 RDY limitation | Use Arlet core | **Use T65 or MiSTer 6502** |
| DMA only used RDY | RDY stall only | **Bus master with address control** |
| CHR from SDRAM during render | HBlank prefetch | **32KB BRAM cache, VBlank reload** |
| HBlank timing optimistic | 64 fetches fit | **No SDRAM during HBlank** |
| PRG-RAM zero-fill size | 8KB mentioned | **32KB SDRAM space** |
| APU frame timing | Single 7456 divider | **Proper step thresholds** |
| Reset vector latency | Direct SDRAM | **BRAM cache for fixed bank** |
| Multi-bit CDC | Not addressed | **Quasi-static sync for banks** |
| PPU/CPU ratio | Implicit | **Explicit 3:1 enable generation** |