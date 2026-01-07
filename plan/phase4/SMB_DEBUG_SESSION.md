# SMB Debug Session - January 7, 2026

## Problem Summary
Super Mario Bros displays title screen for ~1 second then freezes.
Donkey Kong works perfectly with the same codebase.

---

## Hardware Observations

### LED Status (Current Debug Build)
| LED | Signal | During 1st Second | After Freeze |
|-----|--------|-------------------|--------------|
| [3:0] | NMI counter | Counting at 60Hz | Frozen |
| [4] | NMI active | Flashing | Off |
| [5] | DMA active | Flashing | Off |
| [6] | ppuctrl[7] | Bright/flashing | Off |
| [7] | ppustatus[7] | Flashing | Dim flash |
| [8] | UART active | - | - |
| [9] | UART RX | - | - |

### HEX Display (Final Reading)
```
HEX5:HEX4 = XX (CPU address, was changing)
HEX3:HEX2 = 00 (ppustatus = 0x00)
HEX1:HEX0 = 10 (ppuctrl = 0x10)
```

### Key Finding
- **ppuctrl = 0x10** → NMI is DISABLED (bit 7 = 0)
- **ppustatus = 0x00** → VBlank flag is 0 (either not set or constantly cleared)
- Game intentionally writes 0x10 to $2000 (PPUCTRL) at startup

---

## What Works vs What Doesn't

| Feature | Donkey Kong | Super Mario Bros |
|---------|-------------|------------------|
| Title screen displays | ✅ Yes | ✅ Yes (for ~1 sec) |
| Sprites visible | ✅ Yes | ❌ Mario missing |
| Animation | ✅ Yes | ❌ Frozen |
| Controls | ✅ Yes | ❌ No response |
| ppuctrl stable value | 0x9x (NMI on) | 0x10 (NMI off) |
| Game continues running | ✅ Yes | ❌ Freezes |

---

## ROM Differences

| Aspect | Donkey Kong | Super Mario Bros |
|--------|-------------|------------------|
| PRG Size | 16KB (mirrored to 32KB) | 32KB |
| CHR Size | 8KB | 8KB |
| Mapper | 0 (NROM) | 0 (NROM) |
| Mirroring | Horizontal (MIRROR_V=0) | Vertical (MIRROR_V=1) |
| Reset Vector | $C79E | $8000 |
| NMI Vector | $C85F | $8082 |

---

## Startup Code Comparison

Both games have IDENTICAL startup sequence:
```asm
$RESET:
    78      SEI           ; Disable interrupts
    D8      CLD           ; Clear decimal mode
    A9 10   LDA #$10
    8D 00 20 STA $2000    ; PPUCTRL = $10 (NMI disabled)
    A2 FF   LDX #$FF
    9A      TXS           ; Stack pointer = $FF
    AD 02 20 LDA $2002    ; Read PPUSTATUS
    29 80   AND #$80      ; Check VBlank bit
    F0 xx   BEQ (loop)    ; Wait for VBlank
```

**Both write 0x10 to PPUCTRL and poll $2002 waiting for VBlank.**

---

## Debug Tests Performed

### Test 1: Forced NMI
Changed PPU to always fire NMI on VBlank (ignore ppuctrl[7]):
```verilog
nmi_n <= ~ppustatus[7];  // Instead of ~(ppustatus[7] && ppuctrl[7])
```
**Result:** Screen went BLACK. NMI counter ran at 60Hz.
**Conclusion:** Game actively disables rendering when unexpected NMI occurs.

### Test 2: Disabled APU IRQ
Changed CPU IRQ input:
```verilog
.IRQ_n(1'b1)  // Instead of .IRQ_n(apu_irq_n)
```
**Result:** Mario sprite appeared! But game still frozen.
**Conclusion:** APU IRQ was interfering, but not the root cause.

### Test 3: Fixed P2 Controller
Added proper $4017 read response:
```verilog
wire [7:0] ctrl_rdata_p1 = {7'b0100000, ctrl_shift[0]};
wire [7:0] ctrl_rdata_p2 = 8'b01000000;  // P2: no buttons
assign ctrl_rdata = addr16[0] ? ctrl_rdata_p2 : ctrl_rdata_p1;
```
**Result:** No change. Still frozen.

---

## Current RTL Parameters (for SMB)

```verilog
parameter MAPPER_TYPE = 0,    // NROM
parameter PRG_SIZE = 32768,   // 32KB
parameter CHR_RAM_MODE = 0,   // CHR-ROM
parameter MIRROR_V = 1        // Vertical mirroring
```

ROM files:
- PRG: `../rom_data/super_mario_bros_prg.hex`
- CHR: `../rom_data/super_mario_bros_chr.hex`

---

## Hypotheses (Not Yet Tested)

### Hypothesis 1: VBlank Polling Issue
Both games poll $2002 waiting for VBlank at startup. If VBlank never appears to set, the game loops forever.

**Why DK might pass but SMB might fail:**
- Timing difference due to different reset vector locations?
- SMB does more between VBlank checks?

### Hypothesis 2: RAM Initialization
SMB clears all RAM during initialization. If something goes wrong during RAM clear, game could get stuck.

### Hypothesis 3: Sprite 0 Hit
SMB uses sprite 0 hit for screen split timing. If sprite 0 never hits, game could be waiting forever.

### Hypothesis 4: Different NMI Handler Behavior
After initial setup, SMB enables NMI. If NMI handler has a bug path for our hardware, it could disable NMI and hang.

---

## Files Modified During Debug

| File | Changes |
|------|---------|
| `rtl/nes_top_ppu.v` | Added debug outputs, P2 controller fix, MIRROR_V param |
| `rtl/nes_ppu_vga_sync.v` | Added debug_ppuctrl/ppustatus outputs |
| `rtl/nes_apu_stub.v` | (IRQ disabled by connection change) |

---

## Next Steps to Try

1. **Add VBlank pulse counter** - Verify VBlank is actually pulsing at 60Hz
2. **Check RAM reads** - Verify CPU can read back what it wrote to RAM
3. **Trace $2002 reads** - Count how many times CPU reads PPUSTATUS
4. **Compare with working emulator** - Run SMB in Mesen/FCEUX with logging
5. **Check if stuck in loop** - Sample CPU address to see if it's in a tight loop

---

## Commands to Resume

### Switch to SMB and compile:
```bash
cd /home/cg/risc-v_on_de10-lite/nes/scripts/tools
python3 switch_game.py super_mario_bros
# Then manually set MIRROR_V = 1 in nes_top_ppu.v
cd /home/cg/risc-v_on_de10-lite/nes/quartus_nes_vga
quartus_sh --flow compile nes_vga
quartus_pgm -m jtag -o "p;nes_vga.sof"
```

### Switch to DK (known working):
```bash
cd /home/cg/risc-v_on_de10-lite/nes/scripts/tools
python3 switch_game.py donkey_kong
cd /home/cg/risc-v_on_de10-lite/nes/quartus_nes_vga
quartus_sh --flow compile nes_vga
quartus_pgm -m jtag -o "p;nes_vga.sof"
```

### Run keyboard controller:
```bash
cd /home/cg/risc-v_on_de10-lite/nes/scripts/tools
python3 keyboard_controller.py --port /dev/ttyUSB0 --continuous
```

---

## Current HEX Debug Layout

```
HEX5:HEX4 = DMA source page
HEX3:HEX2 = Sprite 0 Y position
HEX1:HEX0 = PPUCTRL value
```

(Note: This was just changed but not compiled/tested)

---

## Key Insight

The fundamental mystery: **Both DK and SMB have identical startup code, but DK progresses while SMB freezes.**

The difference must be in:
1. What happens AFTER the initial VBlank wait
2. How the different ROM layout affects execution
3. Something specific to SMB's game logic that fails on our hardware

---

## ROOT CAUSE FOUND - January 7, 2026

### The Problem
**Sprite 0 hit (`ppustatus[6]`) was never implemented!**

Super Mario Bros uses sprite 0 hit for timing the status bar scroll split:
1. SMB positions sprite 0 at the bottom of the status bar area
2. Game loops waiting for `ppustatus[6]` to be set (sprite 0 hit)
3. When hit occurs, game changes scroll position for the playfield
4. Without sprite 0 hit, the game enters an infinite wait loop

### Why Donkey Kong Worked
Donkey Kong does NOT use sprite 0 hit for timing. It only uses:
- VBlank for frame synchronization
- Simple scroll values (no mid-frame splits)

### The Fix (nes_ppu_vga_sync.v)

1. **Added `spr0_hit_flag` wire** after sprite pixel extraction:
```verilog
wire spr0_hit_flag = is_spr0_p1 && 
                     !spr_transparent && 
                     !bg_transparent && 
                     bg_enabled && 
                     spr_enabled && 
                     in_visible_p2;
```

2. **Set ppustatus[6] when sprite 0 hit detected**:
```verilog
if (spr0_hit_flag)
    ppustatus[6] <= 1'b1;
```

3. **Clear ppustatus[6] at pre-render scanline** (same time as VBlank clear):
```verilog
else if (v_count == 261 && h_count == 1) begin
    ppustatus[7] <= 1'b0;
    ppustatus[6] <= 1'b0;  // Clear sprite 0 hit at start of pre-render
end
```

### Key Lesson
**Always verify which PPU features a game requires.** The sprite 0 detection logic (`is_spr0_p1`) already existed but wasn't wired to set the status flag. Games that rely on sprite 0 hit (most scrolling games) will hang without it.

---

## ONGOING: Visual Glitches After Sprite 0 Fix - January 7, 2026

### Current Symptoms
After implementing sprite 0 hit, SMB runs (demo plays, controls work) but has visual glitches:

1. **Horizontal strips** - Solid background-colored strips moving from bottom to top of screen (constant)
2. **Flashing when scrolling** - Screen alternates between current scroll position and scroll=0 (only when Mario walks and screen scrolls)
3. **Status bar shifts** - The top status bar shifts left/right in sync with the flashing
4. **LED counter uneven** - NMI counter (LED[3:0]) accelerates and decelerates instead of smooth 60Hz

### What Doesn't Flash
- Title screen (no scrolling) is stable except for the horizontal strips
- When Mario stands still (no scroll change), display is stable except strips

### Attempted Fixes (All Failed)

| Fix | Rationale | Result |
|-----|-----------|--------|
| Clock domain fix - VGA timing on clk50 with clk25_en | Eliminate metastability between clk25 and clk50 | No change |
| Scroll register latching at frame start | Prevent mid-frame scroll changes from causing tearing | No change |
| vga_ce gating for pipeline registers | Pipeline was advancing 2x per pixel (50MHz vs 25MHz rate) | No change |
| Reset initialization for scroll latches | Uninitialized registers could cause random values | No change |

### Current Architecture Analysis

**Two Independent Timing Systems:**
1. **PPU timing** (`h_count`/`v_count` at ~5.5 MHz via `ppu_ce`)
   - 341 × 262 = 89,342 cycles/frame
   - Frame rate: 5.5MHz / 89342 = **61.7 Hz**
   
2. **VGA timing** (`pixel_x`/`pixel_y` at 25 MHz via `clk25_en`)
   - 800 × 525 = 420,000 cycles/frame  
   - Frame rate: 25MHz / 420000 = **59.5 Hz**

**The PPU runs ~3.7% faster than VGA!** This causes:
- Frames to drift relative to each other
- CPU writes scroll values based on PPU VBlank timing
- VGA reads scroll values at different phase each frame
- Result: Some frames catch "old" scroll, some catch "new" scroll

### Hypothesis: Frame Rate Mismatch

The ~2.2 Hz difference between PPU (61.7Hz) and VGA (59.5Hz) means:
- Every ~0.45 seconds, the two are exactly out of phase
- This could explain the periodic flashing pattern

### Possible Solutions (Not Yet Tried)

1. **Sync PPU timing to VGA timing** - Derive PPU VBlank from VGA vsync instead of independent counter
2. **Add frame buffer** - Double-buffer the entire frame (requires significant RAM)
3. **Adjust PPU clock divider** - Match PPU frame rate to VGA (would affect game timing)

### Files Currently Modified

| File | Changes |
|------|---------|
| `rtl/nes_ppu_vga_sync.v` | Sprite 0 hit, scroll latching, vga_ce gating, reset init |
| `rtl/nes_top_ppu.v` | vga_ce connection, clk25_en generation |
| `rtl/vga_timing.v` | clk_en input for same-domain operation |

### Current Code State

Scroll latch with reset (nes_ppu_vga_sync.v ~line 235):
```verilog
always @(posedge clk) begin
    if (reset) begin
        scroll_x_latched <= 8'h00;
        scroll_y_latched <= 8'h00;
        ppuctrl_latched <= 8'h00;
        vga_y_prev <= 8'hFF;
    end else if (vga_ce) begin
        vga_y_prev <= vga_y;
        if (vga_y == 8'd0 && vga_y_prev != 8'd0) begin
            scroll_x_latched <= ppuscroll_x;
            scroll_y_latched <= ppuscroll_y;
            ppuctrl_latched <= ppuctrl;
        end
    end
end
```

### Next Steps

1. **Synchronize PPU VBlank to VGA VBlank** - Make the PPU's NMI timing match when VGA actually starts a new frame
2. **Debug with logic analyzer** - Capture scroll_x_latched vs ppuscroll_x to see timing relationship
3. **Try removing scroll latching** - Use live scroll values to see if flashing pattern changes (diagnostic only)
