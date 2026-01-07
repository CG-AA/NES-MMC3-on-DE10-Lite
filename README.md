# NES on DE10-Lite FPGA

A complete NES (Nintendo Entertainment System) emulator implemented in Verilog, running standalone on the Terasic DE10-Lite FPGA board.

**Status:** ✅ Phase 3 Complete - Fully Playable!

![FPGA](https://img.shields.io/badge/FPGA-Intel_MAX_10-blue)
![Status](https://img.shields.io/badge/Status-Playable-brightgreen)
![Games](https://img.shields.io/badge/Mapper-NROM-orange)

---

## Features

| Feature | Status | Notes |
|---------|--------|-------|
| T65 6502 CPU | ✅ | ~1.78 MHz, cycle-accurate |
| PPU Graphics | ✅ | VGA-synchronized rendering |
| Background Tiles | ✅ | 32x30 nametable with scrolling |
| Sprites | ✅ | All 64 sprites with priority |
| OAM DMA | ✅ | Hardware sprite transfer |
| VGA Output | ✅ | 640x480@60Hz, 2x scaling |
| Keyboard Input | ✅ | UART with 16x oversampling |
| Game Switching | ✅ | Automated build pipeline |
| NROM Games | ✅ | Mapper 0 fully supported |
| Audio | ❌ | Planned for Phase 5 |
| Other Mappers | ⏳ | Phase 4: MMC1, UxROM, CNROM |

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/CG-AA/NES-MMC3-on-DE10-Lite.git
cd NES-MMC3-on-DE10-Lite/nes

# Add your ROM file (you must provide your own legally-obtained ROMs)
cp /path/to/donkey_kong.nes roms/

# Build and program (requires Quartus Prime)
python3 scripts/tools/switch_game.py roms/donkey_kong.nes --compile --program

# Play with keyboard
python3 scripts/tools/keyboard_controller.py --port /dev/ttyUSB0 --continuous
```

---

## Hardware Requirements

### DE10-Lite FPGA Board
- **FPGA:** Intel MAX 10 (10M50DAF484C7G)
- **Resources Used:** 46% Logic, 30% Memory
- **Clock:** 50 MHz onboard oscillator

### External Connections

| Component | Connection | Notes |
|-----------|------------|-------|
| **VGA Monitor** | VGA Port | Any monitor supporting 640x480@60Hz |
| **USB-UART Adapter** | JP1 Header | CP2102, CH340, or FTDI (3.3V) |

#### UART Wiring (JP1 Header)
```
USB-UART Adapter          DE10-Lite JP1
     TX  ──────────────►  Pin 1  (GPIO[0] = V10)
    GND  ──────────────►  Pin 30 (Ground)
```

> ⚠️ **Note:** Only TX→FPGA connection is needed. The adapter transmits keyboard data to the FPGA.

---

## Software Requirements

### Quartus Prime
- **Version:** Quartus Prime Lite 18.1 or later
- **Device Support:** MAX 10 family
- Download: [Intel FPGA Software](https://www.intel.com/content/www/us/en/software-kit/download/intel-quartus-prime-lite-edition-design-software.html)

### Python 3.8+
```bash
pip install pyserial pynput
```

### Environment Setup
```bash
# Add Quartus to PATH (adjust path as needed)
export PATH="/path/to/intelFPGA_lite/18.1/quartus/bin:$PATH"

# Verify installation
which quartus_sh
which quartus_pgm
```

---

## Build Instructions

### Automated (Recommended)

The `switch_game.py` script handles the complete pipeline:

```bash
cd nes

# Extract ROM, update RTL, compile, and program FPGA
python3 scripts/tools/switch_game.py roms/game.nes --compile --program

# List available games
python3 scripts/tools/switch_game.py --list

# Extract only (no compile)
python3 scripts/tools/switch_game.py roms/game.nes --extract-only
```

### Manual Build

1. **Extract ROM to hex files:**
   ```bash
   python3 scripts/tools/extract_nes_rom.py roms/game.nes
   mv roms/game_prg.hex rom_data/
   mv roms/game_chr.hex rom_data/
   ```

2. **Update RTL paths** in `rtl/nes_top_ppu.v`:
   ```verilog
   .INIT_FILE("../rom_data/game_prg.hex")  // PRG ROM
   .INIT_FILE("../rom_data/game_chr.hex")  // CHR ROM
   ```

3. **Compile with Quartus:**
   ```bash
   cd quartus_nes_vga
   quartus_sh --flow compile nes_vga
   ```
   > Compilation takes ~7 minutes on a 4-core CPU.

4. **Program FPGA:**
   ```bash
   quartus_pgm -m jtag -o "p;nes_vga.sof"
   ```

---

## Controls

### Keyboard Mapping

| Key | NES Button | Alt Key |
|-----|------------|---------|
| W | D-Pad Up | ↑ |
| S | D-Pad Down | ↓ |
| A | D-Pad Left | ← |
| D | D-Pad Right | → |
| K | A Button | X |
| J | B Button | Z |
| Enter | Start | - |
| Right Shift | Select | - |
| Space | A Button | - |
| Esc | Exit | - |

### Hardware Fallback (No UART)
If UART is not connected, use the onboard switches:
- `SW[0-3]`: D-Pad (Right, Left, Down, Up)
- `SW[4]`: Select
- `KEY[1]`: Start
- `SW[5-6]`: B, A

---

## Tested Games

| Game | Mapper | Status |
|------|--------|--------|
| Donkey Kong | NROM | ✅ Perfect |
| Balloon Fight | NROM | ✅ Perfect |
| Ice Climber | NROM | ✅ Works |
| Excitebike | NROM | ✅ Works |
| Popeye | NROM | ✅ Works |
| Mario Bros | NROM | ✅ Works |

> **Note:** Only NROM (Mapper 0) games are currently supported. Games requiring other mappers (Super Mario Bros, Mega Man, Zelda) will be supported in Phase 4.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DE10-Lite FPGA                        │
│  ┌─────────────────────────────────────────────────────┐│
│  │           NES Core (Standalone @ 50 MHz)            ││
│  │                                                      ││
│  │  ┌──────────┐         ┌─────────────────────────┐  ││
│  │  │ T65 CPU  │◄───────►│ PRG-ROM (32KB BRAM)     │  ││
│  │  │ ~1.78MHz │         │ Internal RAM (2KB)      │  ││
│  │  └─────┬────┘         └─────────────────────────┘  ││
│  │        │                                            ││
│  │  ┌─────▼──────┐       ┌─────────────────────────┐  ││
│  │  │    PPU     │◄─────►│ CHR-ROM (8KB, 6-port)   │  ││
│  │  │ VGA-sync   │       │ VRAM (2KB, 3-port)      │  ││
│  │  │ 64 Sprites │       │ OAM (256 bytes)         │  ││
│  │  └─────┬──────┘       └─────────────────────────┘  ││
│  │        │                                            ││
│  │  ┌─────▼──────┐       ┌─────────────────────────┐  ││
│  │  │ VGA Output │       │ UART Controller         │  ││
│  │  │ 640x480    │       │ 115200 baud, 16x sample │  ││
│  │  └────────────┘       └─────────────────────────┘  ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
    VGA Monitor              USB-UART ◄── Laptop Keyboard
```

---

## Project Structure

```
nes/
├── rtl/                         # Verilog/VHDL source
│   ├── nes_top_ppu.v            # Top-level module
│   ├── nes_ppu_vga_sync.v       # PPU + VGA + Sprites
│   ├── nes_dma_controller.v     # OAM DMA
│   ├── nes_uart_controller.v    # Keyboard input
│   ├── nes_prg_bram.v           # PRG-ROM memory
│   ├── nes_chr_multiport.v      # CHR-ROM (6-port)
│   ├── nes_vram_dp.v            # Nametable VRAM
│   └── NES-FPGA/src/t65/        # T65 6502 CPU (VHDL)
│
├── quartus_nes_vga/             # Quartus project
│   ├── nes_vga.qpf              # Project file
│   ├── nes_vga.qsf              # Pin assignments
│   └── nes_vga.sof              # Compiled bitstream
│
├── scripts/tools/               # Python utilities
│   ├── switch_game.py           # Game switching pipeline
│   ├── extract_nes_rom.py       # ROM → .hex converter
│   └── keyboard_controller.py   # Keyboard → UART
│
├── rom_data/                    # Extracted .hex files (gitignored)
├── roms/                        # Original .nes files (gitignored)
└── plan/                        # Detailed documentation
```

---

## Known Limitations

| Limitation | Impact | Planned Fix |
|------------|--------|-------------|
| NROM only | Limited game library | Phase 4: More mappers |
| No audio | Silent gameplay | Phase 5: APU |
| 8x8 sprites only | No 8x16 sprite mode | Add ppuctrl[5] |
| No sprite 0 hit | Some games may glitch | Add detection |
| Compile-time ROMs | Must recompile to switch | SDRAM loading |

---

## Roadmap

### Phase 4: Mapper Support (In Progress)
- [ ] UxROM (Mapper 2) - Contra, Castlevania, Mega Man
- [ ] CNROM (Mapper 3) - Solomon's Key
- [ ] MMC1 (Mapper 1) - Zelda, Metroid, Super Mario Bros
- [ ] AxROM (Mapper 7) - Battletoads

### Phase 5: Audio & Polish
- [ ] APU implementation
- [ ] Full sound synthesis
- [ ] Additional sprite features

### Future
- [ ] MMC3 mapper with SDRAM
- [ ] Runtime ROM loading
- [ ] Save state support

---

## Documentation

Detailed documentation is available in the `plan/` directory:

- **[Build Guide](plan/phase3/BUILD_GUIDE.md)** - Detailed build instructions
- **[Hardware Specs](plan/phase3/HARDWARE.md)** - Pin assignments, timing
- **[Lessons Learned](plan/LESSONS_LEARNED.md)** - Debug techniques, common issues
- **[Phase 4 Plan](plan/phase4/PHASE4_PLAN.md)** - Mapper implementation roadmap

---

## Troubleshooting

### "No USB-Blaster detected"
```bash
# Check connection
jtagconfig

# Linux: Add udev rules
sudo usermod -a -G plugdev $USER
# Log out and back in
```

### "No UART device /dev/ttyUSB0"
```bash
# Check available ports
ls -la /dev/ttyUSB* /dev/ttyACM*

# Add user to dialout group
sudo usermod -a -G dialout $USER
```

### Compilation fails
- Ensure you're compiling from `quartus_nes_vga/` directory
- Check ROM hex files exist in `rom_data/`
- Verify Quartus PATH is set correctly

---

## Credits

- **T65 6502 Core:** [Tennfors/NES-FPGA](https://github.com/Tennfors/NES-FPGA)
- **NES Reference:** [MiSTer-devel/NES_MiSTer](https://github.com/MiSTer-devel/NES_MiSTer)
- **NES Documentation:** [NESDev Wiki](https://wiki.nesdev.com/)
- **DE10-Lite Board:** [Terasic](https://www.terasic.com.tw/)

---

## License

This project is for educational purposes. NES is a trademark of Nintendo.

ROM files are not included - you must provide your own legally-obtained copies.

---

## Contributing

Contributions are welcome! Please see the documentation in `plan/` for architectural details and the roadmap for planned features.

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

*Last Updated: January 7, 2026*
