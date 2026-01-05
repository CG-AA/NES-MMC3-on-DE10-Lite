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
    ├── upload_rom.py          # Upload NES ROM to SDRAM
    └── extract_nes_rom.py     # Extract PRG/CHR from NES file
```

## Quick Reference

### Test SDRAM
```bash
python3 scripts/tests/test_simple.py
```

### Upload ROM
```bash
python3 scripts/tools/upload_rom.py roms/donkey_kong.nes
```

### Rebuild with Safe SDRAM Timings
```bash
./scripts/build_with_safe_sdram.sh
```
