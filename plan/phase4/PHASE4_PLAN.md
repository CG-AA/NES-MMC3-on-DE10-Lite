# Phase 4: Mapper Support (BRAM-Only)

**Goal:** Add mapper support for games larger than NROM, without SDRAM complexity.

**Status:** 🚀 IN PROGRESS

**Prerequisites:** Phase 3 complete ✅

---

## Strategy: Expand Game Library with BRAM

Instead of fighting SDRAM bulk uploads, we maximize our existing BRAM:

| Resource | Used (Phase 3) | Available | Can Fit |
|----------|----------------|-----------|---------|
| M9K Blocks | 63 | 119 | +119KB |
| RAM Bits | 509K | 1,168K | +146KB |

**This is enough for ~70% of the NES library!**

### Mapper Coverage

| Mapper | Name | % of Games | Max ROM Size | Fits in BRAM? |
|--------|------|-----------|--------------|---------------|
| 0 | NROM | ~10% | 40KB | ✅ Already working |
| 1 | MMC1 | ~25% | 256KB PRG + 128KB CHR | ⚠️ Most games fit |
| 2 | UxROM | ~10% | 256KB PRG + CHR-RAM | ✅ PRG fits, CHR-RAM |
| 3 | CNROM | ~5% | 32KB PRG + 32KB CHR | ✅ Easily fits |
| 4 | MMC3 | ~25% | 512KB+ | ❌ Needs SDRAM (Phase 5) |
| 7 | AxROM | ~3% | 256KB PRG | ✅ Fits |

**Phase 4 targets: Mappers 1, 2, 3, 7 → unlocks ~45% more games!**

---

## Success Criteria

### Phase 4A: UxROM (Mapper 2) - Simplest bank switching
- [ ] PRG bank switching works (16KB switchable + 16KB fixed)
- [ ] CHR-RAM support (writable pattern table)
- [ ] Test: Contra, Castlevania, Mega Man

### Phase 4B: CNROM (Mapper 3) - CHR banking
- [ ] CHR bank switching works (8KB banks)
- [ ] Test: Solomon's Key, Paperboy

### Phase 4C: MMC1 (Mapper 1) - Most popular
- [ ] PRG banking (16KB or 32KB modes)
- [ ] CHR banking (4KB or 8KB modes)
- [ ] Mirroring control
- [ ] Test: Legend of Zelda, Metroid, Super Mario Bros

### Phase 4D: AxROM (Mapper 7) - Large PRG
- [ ] 32KB PRG bank switching
- [ ] Single-screen mirroring
- [ ] Test: Battletoads, Marble Madness

---

## Target Games (All Fit in BRAM)

| Game | Mapper | PRG | CHR | Total | Status |
|------|--------|-----|-----|-------|--------|
| **Contra** | UxROM | 128KB | 0 (RAM) | 128KB | 🎯 First target |
| Castlevania | UxROM | 128KB | 0 (RAM) | 128KB | Phase 4A |
| Mega Man | UxROM | 128KB | 0 (RAM) | 128KB | Phase 4A |
| Legend of Zelda | MMC1 | 128KB | 0 (RAM) | 128KB | Phase 4C |
| Metroid | MMC1 | 128KB | 0 (RAM) | 128KB | Phase 4C |
| Super Mario Bros | MMC1 | 32KB | 8KB | 40KB | Phase 4C |

---

## Phase 4A: UxROM Implementation

### How UxROM Works
```
CPU Address Space:
$8000-$BFFF: Switchable 16KB PRG bank (selected by writing to $8000-$FFFF)
$C000-$FFFF: Fixed to LAST 16KB bank

CHR: Uses 8KB RAM (pattern table is writable)
```

### Memory Layout (128KB PRG example)
```
PRG-ROM (128KB = 8 banks of 16KB):
  Bank 0: $00000-$03FFF → mapped to $8000 when bank_select=0
  Bank 1: $04000-$07FFF → mapped to $8000 when bank_select=1
  ...
  Bank 7: $1C000-$1FFFF → FIXED at $C000-$FFFF (always accessible)
```

### Implementation Plan

1. **Expand PRG BRAM from 32KB to 128KB**
   - Change `nes_prg_bram.v` parameter
   - Uses ~12 more M9K blocks

2. **Add bank register**
   ```verilog
   reg [2:0] prg_bank;  // 3 bits for 8 banks
   always @(posedge clk)
       if (prg_write && addr >= 16'h8000)
           prg_bank <= cpu_data[2:0];
   ```

3. **Modify address translation**
   ```verilog
   wire [16:0] prg_addr = (addr[15:14] == 2'b10) ?  // $8000-$BFFF
                          {prg_bank, addr[13:0]} :   // Banked
                          {3'b111, addr[13:0]};      // $C000-$FFFF = last bank
   ```

4. **Add CHR-RAM**
   - Replace CHR-ROM with CHR-RAM (writable)
   - PPU writes to $0000-$1FFF go to CHR-RAM

### Files to Modify
- `nes_prg_bram.v` → Expand to 128KB
- `nes_top_ppu.v` → Add bank register, address translation
- `nes_chr_multiport.v` → Make writable (CHR-RAM)
- `extract_nes_rom.py` → Handle CHR-RAM games (no CHR data)

---

## Phase 4B: CNROM Implementation

### How CNROM Works
```
PRG: Fixed 16KB or 32KB (no banking)
CHR: Bank switching, 8KB banks, write to $8000-$FFFF selects bank
```

### Implementation
Simple CHR bank register:
```verilog
reg [1:0] chr_bank;  // 2 bits for 4 banks (32KB max)
always @(posedge clk)
    if (prg_write && addr >= 16'h8000)
        chr_bank <= cpu_data[1:0];

wire [14:0] chr_addr = {chr_bank, ppu_addr[12:0]};
```

---

## Phase 4C: MMC1 Implementation

### How MMC1 Works
Most complex of the BRAM-compatible mappers:
- Serial interface (5 writes to shift register)
- Multiple banking modes
- Mirroring control

### Registers
```
$8000-$9FFF: Control register (mirroring, PRG/CHR mode)
$A000-$BFFF: CHR bank 0
$C000-$DFFF: CHR bank 1
$E000-$FFFF: PRG bank
```

### Implementation Complexity
- Need 5-bit shift register
- Multiple PRG/CHR banking modes
- Worth it: 25% of NES games!

---

## Phase 5 (Future): MMC3 + SDRAM

MMC3 requires SDRAM due to ROM sizes (256KB+ PRG, 128KB+ CHR).

Options for Phase 5:
1. **Etherbone** - Ethernet bulk uploads
2. **SD Card** - SPI interface + FAT filesystem  
3. **Serial Flash** - Dedicated ROM chip

---

## Architecture Changes

### Current (Phase 3)
```
┌─────────────────────────────────────┐
│ PRG-ROM (32KB BRAM, fixed)          │
│ CHR-ROM (8KB BRAM, fixed)           │
└─────────────────────────────────────┘
```

### Phase 4 Target
```
┌─────────────────────────────────────┐
│ PRG-ROM (128KB BRAM, banked)        │
│ CHR-ROM/RAM (8-32KB, banked/write)  │
│ Mapper logic (UxROM/CNROM/MMC1)     │
└─────────────────────────────────────┘
```

### Resource Estimate
| Component | M9K Blocks | Notes |
|-----------|------------|-------|
| PRG 128KB | 16 | +12 from current 32KB |
| CHR 32KB | 4 | +4 from current 8KB (if needed) |
| Mapper logic | 0 | Just registers |
| **Total** | 83 | 46% of 182 available |

Still have 99 M9K blocks (54%) for future expansion!

---

## Step-by-Step Plan

### Step 1: UxROM (First Mapper)
1. Expand PRG BRAM to 128KB
2. Add bank register
3. Add CHR-RAM support
4. Test with Contra

### Step 2: CNROM (Quick Win)
1. Add CHR bank register
2. Test with small games

### Step 3: MMC1 (Major Milestone)
1. Implement shift register
2. Add PRG/CHR banking modes
3. Add mirroring control
4. Test with Zelda, Metroid

### Step 4: Game Detection
1. Read mapper from iNES header
2. Configure mapper at compile time
3. Update switch_game.py

---

## What NOT To Do

- Don't implement MMC3 yet (needs SDRAM)
- Don't add audio (Phase 6)
- Don't optimize - get it working first

---

## Ready to Start!

Let's begin with UxROM and Contra!

---

## Implementation Progress (Updated: Jan 7, 2026)

### ✅ Completed

#### 1. PRG BRAM Expansion (`nes_prg_bram.v`)
- Expanded address width from 15-bit to 17-bit (32KB → 128KB)
- Added `SIZE_BYTES` parameter (default 131072)
- Memory now supports full UxROM addressing

#### 2. UxROM Bank Switching (`nes_top_ppu.v`)
- Added module parameters:
  - `MAPPER_TYPE` (0=NROM, 2=UxROM)
  - `PRG_SIZE` (32KB or 128KB)
  - `CHR_RAM_MODE` (0=ROM, 1=RAM)
- Bank register: `reg [2:0] prg_bank`
- Bank write detection: Captures writes to $8000-$FFFF for UxROM
- Address translation via generate block:
  - NROM: Direct 32KB access (`{2'b00, addr[14:0]}`)
  - UxROM: Banked addressing (`{effective_bank, addr[13:0]}`)
- Fixed bank always at $C000-$FFFF (bank 7 for 128KB ROMs)

#### 3. CHR-RAM Support (`nes_chr_multiport.v`)
- Added `CHR_RAM_MODE` parameter
- Added write port (wdata1, we1) to Port 1
- Writes enabled only when `CHR_RAM_MODE=1`
- Propagated parameter from `nes_top_ppu.v`

#### 4. ROM Extraction Script (`extract_nes_rom.py`)
- Added mapper name lookup table
- Detects CHR-RAM games (CHR size = 0)
- UxROM ROMs mirrored to 128KB (so bank 7 = last real bank)
- Shows UxROM bank count and fixed bank info
- Prints reminder about CHR_RAM_MODE parameter

### 🔧 Issues Discovered

#### Issue 1: Quartus Project Configuration
The Quartus project (`nes_vga.qsf`) expects top-level module `nes_vga` but the actual module is `nes_top_ppu`. Options:
1. **Rename module** to `nes_vga` (requires updating all docs)
2. **Create wrapper** `nes_vga.v` that instantiates `nes_top_ppu`
3. **Update QSF** to use `nes_top_ppu`

**Recommended:** Option 3 - just update the QSF file.

#### Issue 2: ROM File Paths are Hardcoded
The module has hardcoded paths like:
```verilog
.INIT_FILE("../rom_data/donkey_kong_prg.hex")
```
For UxROM games, need to change these manually or use `switch_game.py`.

#### Issue 3: Mirroring Configuration
Currently hardcoded to horizontal mirroring (Donkey Kong). UxROM games may need different mirroring. Need to add mirroring mode parameter.

### ⏳ Next Steps

1. ~~**Fix Quartus configuration**~~ ✅ Used correct project directory (`quartus_nes_vga/`)
2. ~~**Compile test**~~ ✅ Compiled successfully: 0 errors, 70 warnings
3. **Hardware test NROM** - Program SOF, verify Donkey Kong still works
4. **Get Contra ROM** - Need a UxROM test ROM
5. **Test UxROM** - Compile with Contra and verify bank switching

### 📊 Compilation Results (Jan 7, 2026 04:53)

| Metric | Value |
|--------|-------|
| Errors | 0 |
| Warnings | 70 (all benign - unused signals, truncations) |
| Compile Time | 7 min 7 sec |
| SOF Size | 3.2 MB |
| Project Dir | `quartus_nes_vga/` |

### 📁 Files Modified

| File | Changes |
|------|---------|
| `rtl/nes_prg_bram.v` | 17-bit addr, SIZE_BYTES param |
| `rtl/nes_top_ppu.v` | MAPPER_TYPE, PRG_SIZE, CHR_RAM_MODE, MIRROR_V params; bank switching logic |
| `rtl/nes_chr_multiport.v` | CHR_RAM_MODE param, write port |
| `scripts/tools/extract_nes_rom.py` | Mapper detection, UxROM mirroring, CHR-RAM handling |
| `scripts/tools/switch_game.py` | Auto-detect mapper params, update MIRROR_V |

---

## 🐛 Active Bug: Super Mario Bros Frozen (Jan 7, 2026)

### Symptoms
- **Display**: Title screen renders correctly (logo, menu text, background)
- **Mario sprite**: MISSING from title screen
- **Coin**: NOT spinning (no animation)
- **Controls**: Unresponsive (game frozen)
- **CPU address**: Rapidly changing on HEX display (CPU IS running)

### What Works
- **Donkey Kong**: Fully functional with same codebase
  - All sprites visible
  - Animation working (DK pounding barrels)
  - Controls responsive

### Key Differences: DK vs SMB

| Aspect | Donkey Kong | Super Mario Bros |
|--------|-------------|------------------|
| PRG Size | 16KB (mirrored to 32KB) | 32KB (no mirroring) |
| Reset Vector | $C79E (in $C000-$FFFF) | $8000 (start of PRG) |
| NMI Vector | $C85F | $8082 |
| Mirroring | Horizontal (MIRROR_V=0) | Vertical (MIRROR_V=1) |

### Verified Correct
1. ✅ Reset vector in hex file: $8000 at offset $7FFC-$7FFD
2. ✅ NMI vector in hex file: $8082 at offset $7FFA-$7FFB
3. ✅ First bytes at offset 0: `78 D8 A9 10 8D 00 20...` (valid 6502 init code)
4. ✅ MIRROR_V=1 parameter set for vertical mirroring
5. ✅ PRG_SIZE=32768 parameter set
6. ✅ MAPPER_TYPE=0 (NROM)
7. ✅ CPU is executing (address rapidly changing on HEX display)
8. ✅ Background nametables render correctly
9. ✅ CHR data loaded (graphics visible)

### Hypothesis

Since the CPU is running but sprites are missing and there's no animation:

1. **OAM DMA might not be working for SMB**
   - DK and SMB may use different RAM pages for sprite data
   - OAM DMA reads from CPU RAM and writes to PPU OAM
   
2. **NMI might not be firing**
   - No animation = NMI handler not running
   - But background rendered = at least initial setup completed
   
3. **Game stuck in an infinite loop**
   - Could be waiting for something specific (APU register? Controller?)
   - SMB does more complex initialization than DK

### Debug Steps Attempted
1. Added CPU address to HEX display → Address IS changing (CPU running)
2. Compared ROM extraction → Vectors correct
3. Verified MIRROR_V parameter → Set to 1 (vertical)
4. Switched back to DK → Works perfectly
5. Switched back to SMB → Still frozen

### Next Debug Steps to Try
1. **Add NMI debug** - LED that toggles on each NMI
2. **Add DMA debug** - Show OAM DMA source page and byte count
3. **Slow down CPU** - Use SW[9] to enable single-step mode
4. **Check $2002 status** - Show PPU status register on HEX
5. **Compare with emulator** - Trace SMB startup sequence

### Files Involved
- `rtl/nes_top_ppu.v` - Main integration
- `rtl/nes_ppu_vga_sync.v` - PPU with OAM
- `rtl/nes_dma_controller.v` - OAM DMA
- `rom_data/super_mario_bros_prg.hex` - PRG ROM
- `rom_data/super_mario_bros_chr.hex` - CHR ROM

