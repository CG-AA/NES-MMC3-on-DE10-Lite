# Hardware Specifications

## DE10-Lite FPGA Board

### FPGA Chip
- **Model:** Intel MAX 10 10M50DAF484C7G
- **Logic Elements:** 49,760
- **Memory (M9K blocks):** 182 blocks = 1,677,312 bits total
- **User I/O:** 360 pins
- **PLLs:** 4

### Onboard Peripherals
- **Clock:** 50 MHz oscillator
- **SDRAM:** 64MB (IS42S16400J-7TL)
  - 16-bit data bus
  - 133 MHz capable
  - Currently configured for 100 MHz (conservative timing)
- **USB-Blaster:** Built-in JTAG programming
- **VGA Port:** DB-15 with 4-bit R/G/B DAC (resistor network)
- **GPIO Headers:** 2x 40-pin (JP1, JP2), 3.3V logic

### User Interface
- **LEDs:** 10x green
- **7-Segment Displays:** 6x common-cathode
- **Push Buttons:** 2x (KEY0, KEY1), active-low
- **Slide Switches:** 10x

---

## Pin Assignments (nes_vga.qsf)

### System
| Signal | Pin | Notes |
|--------|-----|-------|
| clk50 | P11 | 50 MHz input |
| reset_n | B8 | KEY[0], active-low |
| key1 | A7 | KEY[1], Start button fallback |

### VGA Output
| Signal | Pins | Notes |
|--------|------|-------|
| vga_r[3:0] | Y1, Y2, V1, AA1 | 4-bit red |
| vga_g[3:0] | R1, R2, T2, W1 | 4-bit green |
| vga_b[3:0] | N2, P4, T1, P1 | 4-bit blue |
| vga_hs | N3 | Horizontal sync |
| vga_vs | N1 | Vertical sync |

### UART Controller Input
| Signal | Pin | GPIO Header | Notes |
|--------|-----|-------------|-------|
| uart_ctrl_rx | V10 | JP1 Pin 1 | 3.3V TTL, 115200 baud |
| GND | - | JP1 Pin 30 | Common ground |

**UART Wiring:**
```
CP2102 USB-UART Adapter:
  TX  → JP1 Pin 1 (V10)  # Adapter transmits, FPGA receives
  GND → JP1 Pin 30
```

### Switches & LEDs
| Signal | Pins | Usage |
|--------|------|-------|
| sw[9:0] | F15, B14, A14, A13, B12, A12, C12, D12, C11, C10 | Controller fallback + debug |
| led[9:0] | B11, A11, D14, E14, C13, D13, B10, A10, A9, A8 | Button state + UART status |

### 7-Segment Displays
6 displays (HEX5-HEX0), 8 pins each (7 segments + decimal point).  
Current usage: Controller buttons (HEX3-HEX0), PPU scanline (HEX5-HEX4).

---

## SDRAM (Phase 4 Ready)

### Chip: IS42S16400J-7TL
- **Capacity:** 64MB (4M x 16-bit)
- **Speed Grade:** -7 (7ns = 133 MHz max)
- **Organization:** 4 banks × 4096 rows × 512 columns
- **Refresh:** 4096 cycle / 64ms

### Pin Assignments (not yet used in Phase 3)
Available in QSF for Phase 4 integration.

### Current Status
- Individual read/write verified ✅
- Bulk uploads unreliable via UART ❌
- **Phase 4 Plan:** Etherbone or custom binary loader

---

## Timing Constraints (nes_vga.sdc)

### Clock Domains
```tcl
# System clock
create_clock -period 20.0 [get_ports clk50]  # 50 MHz

# VGA pixel clock (derived, 25 MHz)
create_generated_clock -source [get_ports clk50] -divide_by 2 ...

# Asynchronous domains
set_clock_groups -asynchronous -group {clk50} -group {clk_vga}
```

### False Paths
- Reset signals
- Async GPIO inputs (UART RX, switches)

### Current Slack
- **Setup:** +0.316 ns @ 50 MHz ✅
- **Hold:** Passing ✅

---

## External Connections

### USB-Blaster (Programming)
Built-in, no external connection needed.  
Use: `quartus_pgm -m jtag -o "p;nes_vga.sof"`

### VGA Monitor
Standard VGA cable to any monitor supporting 640x480@60Hz.

### UART Keyboard Adapter
- **Adapter:** CP2102, CH340, or FTDI
- **Voltage:** 3.3V logic (DE10-Lite compatible)
- **Speed:** 115200 baud, 8N1
- **Connection:** See pin table above

---

## Resource Budget (Phase 3 → Phase 4)

### Current Usage (Phase 3)
| Resource | Used | Available | % | Remaining |
|----------|------|-----------|---|-----------|
| Logic Elements | 23,000 | 49,760 | 46% | 26,760 |
| M9K Blocks | 55 | 182 | 30% | 127 |
| Memory Bits | 450K | 1,677K | 27% | 1,227K |

### Phase 4 Additions (Estimated)
| Component | LE | M9K | Notes |
|-----------|----|----|-------|
| MMC3 Mapper | 2,000 | 5 | Bank switching, IRQ counter |
| Wishbone Bridge | 1,500 | 0 | NES ↔ SDRAM interface |
| SDRAM Controller | 0 | 0 | Already in LiteX build |
| APU (future) | 8,000 | 10 | Full sound synthesis |

**Projected Total:** ~35K LE (70%), 70 M9K (38%) - fits comfortably!

---

## Power & Thermal

Phase 3 build runs cool (<40°C ambient):
- No heatsink needed
- FPGA power: ~1.5W estimated
- USB-powered via USB-Blaster cable

Phase 4 should be similar (no high-speed SERDES, modest clock rates).
