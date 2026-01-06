# NES on DE10-Lite Scripts

## Directory Structure

```
scripts/
├── build_with_safe_sdram.sh   # Rebuild FPGA with safe SDRAM timings
├── generators/                 # ROM and test pattern generators
│   ├── gen_test_rom.py        # Generate 6502 test ROM
│   ├── gen_ppu_test_rom.py    # Generate PPU test ROM
│   └── gen_ppu_test_rom_v2.py # PPU test ROM v2 (skip vblank)
├── tests/                      # SDRAM and hardware test scripts
│   ├── test_simple.py         # Quick SDRAM write/read test
│   ├── test_sdram_geometry.py # Test address/bank mapping
│   ├── test_bulk_upload.py    # Test block uploads
│   └── ...
└── tools/                      # ROM loaders and utilities
    ├── bios_manager.py        # BIOS auto-detect and recovery
    ├── switch_game.py         # Switch NES games (extract + compile)
    ├── extract_nes_rom.py     # Extract PRG/CHR from NES file
    ├── keyboard_controller.py # Laptop keyboard → NES controller
    └── upload_rom.py          # Upload NES ROM to SDRAM (unreliable)
```

## Quick Reference

### Switch Games (Recommended - BRAM approach)
```bash
# List available games
python3 scripts/tools/switch_game.py --list

# Extract ROM only (no compile)
python3 scripts/tools/switch_game.py some_game.nes --extract-only

# Full switch with recompile and FPGA programming
python3 scripts/tools/switch_game.py some_game.nes --compile --program
```

### Keyboard Controller (Play with Laptop Keyboard)
```bash
# Install dependency
pip install pynput

# Run in debug mode (shows button state, no UART)
python3 scripts/tools/keyboard_controller.py --debug

# Connect to FPGA (requires controller CSR in RTL)
python3 scripts/tools/keyboard_controller.py --port /dev/ttyUSB0
```

**Controls:**
| Key | NES Button |
|-----|------------|
| W / ↑ | D-Pad Up |
| S / ↓ | D-Pad Down |
| A / ← | D-Pad Left |
| D / → | D-Pad Right |
| J / Z | B |
| K / X | A |
| Enter | Start |
| Right Shift | Select |
| ESC | Quit |

### Test SDRAM (for debugging)
```bash
python3 scripts/tests/test_simple.py
```

### Rebuild with Safe SDRAM Timings
```bash
./scripts/build_with_safe_sdram.sh
```
