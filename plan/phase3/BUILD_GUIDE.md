# Build & Development Guide

## Quick Reference

### Daily Workflow
```bash
# Switch to a different game and program FPGA
cd /home/cg/risc-v_on_de10-lite/nes
python3 scripts/tools/switch_game.py roms/your_game.nes --compile --program

# Play with keyboard
python3 scripts/tools/keyboard_controller.py --port /dev/ttyUSB0 --continuous
```

### Manual Build Process
```bash
# 1. Extract ROM to .hex files
python3 scripts/tools/extract_nes_rom.py roms/game.nes

# 2. Compile (from project directory)
cd quartus_nes_vga
quartus_sh --flow compile nes_vga

# 3. Program FPGA
quartus_pgm -m jtag -o "p;nes_vga.sof@1"
```

---

## Development Environment

### Required Tools
- **Quartus Prime Lite 18.1** (or later)
- **Python 3.8+** with packages:
  - `pyserial` - UART communication
  - `pynput` - Keyboard input capture

### Install Python Dependencies
```bash
pip install pyserial pynput
```

### Quartus Setup
```bash
# Add to PATH (adjust version as needed)
export PATH="/home/user/intelFPGA_lite/18.1/quartus/bin:$PATH"

# Verify installation
which quartus_sh
which quartus_pgm
```

---

## Project Structure

```
nes/
├── rtl/                         # Verilog/VHDL source files
│   ├── nes_top_ppu.v            # Top-level module
│   ├── nes_ppu_vga_sync.v       # PPU + VGA + Sprites
│   ├── nes_dma_controller.v     # OAM DMA
│   ├── nes_uart_controller.v    # Keyboard input
│   ├── nes_chr_multiport.v      # CHR-ROM (6-port)
│   ├── nes_vram_dp.v            # VRAM (3-port)
│   ├── vga_timing.v             # VGA sync generator
│   ├── nes_palette.v            # NES color palette
│   ├── hex_display.v            # 7-segment decoder
│   └── NES-FPGA/src/t65/        # T65 6502 CPU (VHDL)
│
├── quartus_nes_vga/             # Quartus project
│   ├── nes_vga.qpf              # Project file
│   ├── nes_vga.qsf              # Settings + pin assignments
│   ├── nes_vga.sdc              # Timing constraints
│   ├── nes_vga.sof              # Compiled bitstream (output)
│   └── output_files/            # Build outputs
│
├── scripts/tools/               # Python utilities
│   ├── switch_game.py           # Automated game switching
│   ├── extract_nes_rom.py       # ROM → .hex converter
│   ├── keyboard_controller.py   # Keyboard → NES input
│   └── bios_manager.py          # LiteX utilities (Phase 4)
│
├── rom_data/                    # Extracted .hex files (gitignored)
│   ├── *_prg.hex                # PRG-ROM (32KB max)
│   └── *_chr.hex                # CHR-ROM (8KB max)
│
├── roms/                        # Original .nes files (gitignored)
│   └── *.nes
│
├── plan/                        # Documentation
│   ├── README.md                # Main index
│   ├── LESSONS_LEARNED.md       # Debug wisdom
│   ├── phase3/                  # Phase 3 docs
│   ├── phase4/                  # Phase 4 plans
│   └── archive/                 # Old phase docs
│
└── build/                       # LiteX outputs (Phase 4)
```

---

## Build Process Details

### 1. ROM Extraction

**Tool:** `extract_nes_rom.py`

**What it does:**
- Parses iNES header (16 bytes)
- Extracts PRG-ROM (16KB or 32KB)
- Extracts CHR-ROM (8KB)
- Converts to Intel HEX format for `$readmemh()`
- Saves to `rom_data/`

**Requirements:**
- NROM mapper only (mapper 0)
- PRG ≤ 32KB
- CHR ≤ 8KB

**Example:**
```bash
python3 scripts/tools/extract_nes_rom.py roms/donkey_kong.nes
# Creates:
#   rom_data/donkey_kong_prg.hex  (32KB)
#   rom_data/donkey_kong_chr.hex  (8KB)
```

### 2. Quartus Compilation

**Steps:**
1. Analysis & Synthesis (single-threaded, ~3 min)
2. Fitter (multi-threaded, ~4 min)
3. Assembler (~3 sec)
4. Timing Analyzer (~12 sec)

**Total time:** ~7 minutes on 4-core CPU

**Settings (nes_vga.qsf):**
```tcl
set_global_assignment -name NUM_PARALLEL_PROCESSORS ALL
set_global_assignment -name FAMILY "MAX 10"
set_global_assignment -name DEVICE 10M50DAF484C7G
```

**Incremental compilation:**
Quartus automatically uses incremental if only ROM data changes.  
Full recompile if RTL changes.

### 3. FPGA Programming

**Via USB-Blaster:**
```bash
quartus_pgm -m jtag -o "p;nes_vga.sof@1"
```

**SRAM programming:** Bitstream lost on power-off.  
**Flash programming:** Not currently set up (would persist).

---

## ROM File Management

### Supported Games (NROM Only)

Phase 3 supports **NROM (Mapper 0)** games only.

**Confirmed Working:**
- Donkey Kong
- Balloon Fight
- Ice Climber
- Excitebike
- Popeye
- Mario Bros (not Super Mario Bros)

**Not Supported (Yet):**
- Super Mario Bros (MMC1)
- Super Mario Bros 3 (MMC3) ← Phase 4
- Mega Man series (MMC1/3)
- Castlevania series (MMC1/3)

### .gitignore Configuration

```gitignore
# ROM files (copyright, don't commit)
roms/*.nes
rom_data/*.hex

# Build outputs
quartus_nes_vga/output_files/
quartus_nes_vga/db/
quartus_nes_vga/incremental_db/
quartus_nes_vga/*.sof
quartus_nes_vga/*.rpt
```

---

## Debugging Techniques

### Hardware Debug Displays

**LEDs (current configuration):**
- LED[7:0] = Button state (which buttons pressed)
- LED[8] = UART active timeout
- LED[9] = UART RX line (idle = HIGH)

**7-Segment Displays:**
- HEX0-1 = Controller buttons final value
- HEX2-3 = UART received raw value
- HEX4-5 = PPU scanline number

### Debug Parameters

In `nes_ppu_vga_sync.v`:
```verilog
parameter DEBUG_ENABLE = 0;  // Set to 1 for visual debug bars
```

When enabled:
- Top 4 rows show OAM values as horizontal bars
- Different colors for different data sources

### Slow-Motion Mode

Set `sw[9] = 1` for 1 Hz CPU clock (ultra-slow debug).

### UART Test Script

```bash
# Send test patterns to verify UART reception
python3 << 'EOF'
import serial, time
ser = serial.Serial('/dev/ttyUSB0', 115200)
for val in [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0xFF, 0x00]:
    print(f'Sending 0x{val:02X}')
    for _ in range(60): ser.write(bytes([val])); time.sleep(1/60)
    time.sleep(1)
ser.close()
EOF
```

---

## Common Issues & Fixes

### "No USB-Blaster detected"
```bash
# Check if connected
jtagconfig

# May need udev rules (Linux)
sudo usermod -a -G plugdev $USER
# Log out and back in
```

### "No UART device /dev/ttyUSB0"
```bash
# Check what's available
ls -la /dev/ttyUSB* /dev/ttyACM*

# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Compilation fails - wrong directory
Must compile from `quartus_nes_vga/` directory, not `nes/`.

### Game doesn't boot - wrong mapper
Check ROM header: only Mapper 0 (NROM) supported in Phase 3.

```python
# Quick mapper check
with open('roms/game.nes', 'rb') as f:
    header = f.read(16)
    mapper = ((header[6] >> 4) | (header[7] & 0xF0))
    print(f'Mapper: {mapper}')  # Must be 0 for Phase 3
```

### Sprites flicker - DMA timing
Ensure using fixed `nes_dma_controller.v` (sets signals in READ_WAIT).

### UART unreliable - use 16x oversampling
Ensure `nes_uart_controller.v` has `OVERSAMPLE = 16`.

---

## Performance Tuning

### Compilation Speed
- Use `NUM_PARALLEL_PROCESSORS ALL`
- SSD helps (lots of temp files)
- Close other apps during compilation

### Runtime Performance
Phase 3 runs at native NES speed (~60 FPS):
- CPU: 1.78 MHz (50MHz / 28)
- PPU: 5.37 MHz (50MHz / 9)
- VGA: 25 MHz (50MHz / 2)

No frame drops, timing is cycle-accurate.

---

## Next Steps (Phase 4)

See `phase4/PHASE4_PLAN.md` for:
- SDRAM bulk upload solutions
- MMC3 mapper integration
- Wishbone bridge design
- Etherbone setup

---

## Resources

### Official Documentation
- [DE10-Lite User Manual](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=English&No=1021)
- [Quartus Prime User Guide](https://www.intel.com/content/www/us/en/programmable/documentation/)

### NES Documentation
- [NESDev Wiki](https://wiki.nesdev.com/)
- [6502 Reference](http://www.6502.org/)
- [PPU Rendering](https://wiki.nesdev.com/w/index.php/PPU_rendering)

### External Cores
- [T65 6502](https://github.com/Tennfors/NES-FPGA) (VHDL)
- [NES MiSTer](https://github.com/MiSTer-devel/NES_MiSTer) (Reference)
