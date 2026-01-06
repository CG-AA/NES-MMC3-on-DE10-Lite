# Lessons Learned - Common Errors During NES FPGA Debugging

## 1. Quartus Project/Compilation Errors

### Wrong Device Family in QSF
**Error:** `set_global_assignment -name FAMILY "Cyclone V"` instead of `"MAX 10"`
**Cause:** Copy-pasting from wrong project or template
**Fix:** Always verify device family matches DE10-Lite's MAX 10 (10M50DAF484C7G)

### Compiling from Wrong Directory
**Error:** Running `quartus_sh --flow compile nes_vga` from `/nes/` instead of `/nes/quartus_nes_vga/`
**Cause:** QSF file in root `/nes/` directory is incomplete (no source files listed)
**Fix:** Always compile from the proper project directory: `/nes/quartus_nes_vga/`

### Not Using Parallel Compilation
**Error:** Sequential compilation wastes time
**Fix:** Add to QSF: `set_global_assignment -name NUM_PARALLEL_PROCESSORS ALL`

---

## 2. Verilog/RTL Errors

### Accessing Wrong Signal for Debug
**Error:** Using `dma_addr[7:0]` to track byte count when `dma_addr = 16'h2004` during writes
**Cause:** During DMA write phase, `dma_addr` holds the destination ($2004), not the byte offset
**Fix:** Export `byte_count` from DMA controller as a separate output signal

### Forgetting Pipeline Latency
**Error:** Expecting data immediately after setting address
**Cause:** BRAM has 1-cycle registered reads
**Fix:** Always account for 1-cycle latency; use pipeline registers for correct timing

### Signal Not Connected in Module Instantiation
**Error:** Adding ports to module but forgetting to connect them in parent instantiation
**Fix:** When adding new ports, update ALL instantiations immediately

---

## 3. Coordinate System Errors

### VGA vs NES Coordinate Confusion
**Error:** Using raw `pixel_x`/`pixel_y` instead of converted NES coordinates
**Cause:** VGA is 640x480, NES is 256x240 with 2x scaling and 64px border
**Correct Conversion:**
```verilog
wire [7:0] nes_x = (pixel_x >= 64 && pixel_x < 576) ? ((pixel_x - 64) >> 1) : 8'd0;
wire [7:0] nes_y = pixel_y >> 1;
```

### Off-by-One in Sprite Y Position
**Error:** Sprites render 1 line too high/low
**Cause:** NES stores Y as (actual_Y - 1) in OAM
**Fix:** Add 1 to OAM Y value: `spr0_screen_y = spr0_y + 1`

---

## 4. Debug Methodology Errors

### Not Isolating Variables
**Error:** Testing multiple unknowns simultaneously
**Fix:** Use "ghost sprite" technique - hardcode known values to isolate what works

### Reading Changing Values Without Snapshot
**Error:** OAM values flickering because read during active rendering
**Fix:** Snapshot values at VBlank start when they're stable

### Complex Debug Before Simple Debug
**Error:** Adding complex sprite rendering before verifying basic coordinate system
**Fix:** Start with solid color test at known position (e.g., 8x8 orange square at 50,50)

---

## 5. DMA-Specific Errors

### Not Verifying Source Page
**Error:** Assuming DMA reads from correct address without verification
**Fix:** Capture and display `dma_debug_page` to verify source address

### Timing Mismatch Between Read and Latch
**Error:** DMA latches data before RAM output is valid
**Cause:** Combinational vs registered read timing
**Fix:** Ensure address is stable for at least 1 cycle before latching

---

## 6. Best Practices Going Forward

### Compilation
```bash
# Always compile from correct directory with parallel processors
cd /home/cg/risc-v_on_de10-lite/nes/quartus_nes_vga
quartus_sh --flow compile nes_vga
```

### QSF Settings
```tcl
set_global_assignment -name FAMILY "MAX 10"
set_global_assignment -name DEVICE 10M50DAF484C7G
set_global_assignment -name NUM_PARALLEL_PROCESSORS ALL
```

### Debug Visualization Pattern
1. Use horizontal bars at top of screen (value = bar length in pixels)
2. Snapshot values at VBlank for stability
3. Use distinct colors for different data sources
4. Row 1: Data from destination (OAM)
5. Row 2: Data from source (RAM via DMA)
6. Compare rows to identify where data is lost

### Isolation Testing Order
1. Solid color at known position → verify coordinate system
2. Ghost sprite with hardcoded OAM → verify CHR path and rendering
3. Real OAM with debug bars → verify DMA data flow
4. Full sprite rendering → integration test

---

## 7. THE CRITICAL DMA BUG (Root Cause Found!)

### The Problem
DMA appeared to complete (oamaddr=0 at vblank), but OAM contained garbage data.

### What We Observed
- Debug bars for DMA-captured data showed **correct** values (60-80% screen width)
- Debug bars for OAM data showed **wrong** values (~1 pixel)
- This proved: DMA reads correct data, but OAM doesn't receive it

### Root Cause: Registered Output Timing
```verilog
// BROKEN CODE:
WRITE: begin
    dma_data <= read_latch;   // Registered - updates at END of clock cycle
    dma_write <= 1'b1;        // Registered - updates at END of clock cycle
    state <= READ;            // Move to next byte
end

// PPU samples:
if (cpu_wr) begin             // cpu_wr = dma_write && ...
    oam[oamaddr] <= cpu_din;  // But dma_data is still OLD value!
end
```

On the clock edge:
1. State machine is in WRITE state
2. `dma_write` is set to 1 (takes effect at END of cycle)
3. `dma_data` is set to `read_latch` (takes effect at END of cycle)
4. PPU samples `cpu_wr` (sees NEW `dma_write=1`)
5. PPU samples `cpu_din` (sees OLD `dma_data` - wrong value!)

### The Fix: Pre-set Signals One State Earlier
```verilog
READ_WAIT: begin
    if (mem_ack) begin
        // Set these HERE so they're stable when WRITE state is entered
        dma_addr <= 16'h2004;
        dma_data <= bus_data_in;  // Use bus_data directly
        dma_write <= 1'b1;
        state <= WRITE;
    end
end

WRITE: begin
    dma_write <= 1'b0;  // Clear after one cycle
    if (byte_count == 255) state <= DONE;
    else begin
        byte_count <= byte_count + 1;
        state <= READ;
    end
end
```

Now when PPU samples on the WRITE state clock edge:
- `dma_write=1` (set in previous READ_WAIT)
- `dma_data=correct` (set in previous READ_WAIT)
- OAM receives correct data! ✅

### Key Lesson
**Registered outputs are visible to other modules NEXT cycle, not THIS cycle.**
When crossing module boundaries with registered signals, set them one state/cycle early.

---

## 8. UART Receiver Timing Issues

### The Problem
UART controller worked intermittently - only 0x80 (Right button) and 0xFF (all buttons) were received correctly. Other values like 0x01, 0x02, 0x10 failed.

### What We Observed
- Values with bit 7 set worked (0x80, 0xFF)
- Values with only lower bits set failed (0x01, 0x02, 0x10)
- Sometimes worked briefly, then failed on subsequent runs

### Root Cause: Baud Rate Timing Drift
```verilog
// Original 1x sampling approach:
localparam BAUD_DIV = CLK_FREQ / BAUD_RATE;  // 50MHz / 115200 = 434.03

// Error: 0.03 cycles per bit × 8 bits = 0.24 cycles drift
// By bit 7, sampling is ~25% off-center
```

The CP2102 USB-UART adapter's crystal and the FPGA's 50MHz oscillator are not perfectly matched. With 1x sampling, the accumulated timing error caused late bits to be sampled at wrong times.

### Why 0x80 Worked
0x80 = `10000000` binary. The only set bit is bit 7 (last data bit received). By the time we sample bit 7, we've drifted ~0.24 cycles - still within the valid window. But for patterns like 0x01 = `00000001`, bit 0 is the first received and bits 1-7 are all 0. Any sampling error on the middle bits causes corruption.

### The Fix: 16x Oversampling with Noise Filtering
```verilog
// 16x oversampling: sample 16 times per bit period
localparam OVERSAMPLE = 16;
localparam SAMPLE_DIV = CLK_FREQ / (BAUD_RATE * OVERSAMPLE);  // = 27 cycles

// 3-stage synchronizer + majority vote filter
reg [2:0] rx_filter;
case (rx_filter)
    3'b000, 3'b001, 3'b010, 3'b100: rx_filtered <= 0;
    default: rx_filtered <= 1;
endcase

// Sample at middle of each bit (tick 7-8 out of 16)
if (tick_cnt == 7) begin
    // Much more robust - error is now only 0.03/16 = 0.002 cycles per sample
end
```

### Key Lessons
1. **16x oversampling is standard for UART** - provides ±3% baud rate tolerance
2. **Majority vote filtering** eliminates noise glitches
3. **Test with varied bit patterns** - 0x01, 0x02, 0x04, etc. catch timing issues
4. **Visual debug helps** - LEDs showing button state revealed which values worked

### Hardware Notes
- CP2102 TX → FPGA GPIO[0] (PIN_V10 on JP1 header)
- CP2102 GND → FPGA GND (Pin 30 on JP1 header)
- 3.3V logic levels (DE10-Lite compatible)
- Don't connect RX - we only need TX→FPGA direction
