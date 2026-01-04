#!/usr/bin/env python3
"""
Generate a simple NES test ROM that immediately enables PPU rendering
Skips vblank waits to work with simplified PPU
"""

def main():
    # 32KB PRG-ROM
    rom = [0x00] * 32768
    
    # 8KB CHR-ROM (pattern table)
    chr_rom = [0x00] * 8192
    
    # =========================================================================
    # CHR-ROM: Create simple tile patterns
    # =========================================================================
    # Each tile is 8x8 pixels, 16 bytes (8 bytes plane 0, 8 bytes plane 1)
    
    # Tile $00: Empty (all zeros) - background
    
    # Tile $01: Solid block (color 3 - both planes set)
    for row in range(8):
        chr_rom[0x010 + row] = 0xFF  # Plane 0
        chr_rom[0x018 + row] = 0xFF  # Plane 1
    
    # Tile $02: Horizontal stripes (color 1)
    for row in range(8):
        chr_rom[0x020 + row] = 0xFF if (row % 2) == 0 else 0x00
        chr_rom[0x028 + row] = 0x00
    
    # Tile $03: Vertical stripes (color 1)
    for row in range(8):
        chr_rom[0x030 + row] = 0xAA  # 10101010
        chr_rom[0x038 + row] = 0x00
    
    # Tile $04: Checkerboard (color 1)
    for row in range(8):
        chr_rom[0x040 + row] = 0xAA if (row % 2) == 0 else 0x55
        chr_rom[0x048 + row] = 0x00
    
    # Tile $05: Color 2 solid (plane 1 only)
    for row in range(8):
        chr_rom[0x050 + row] = 0x00
        chr_rom[0x058 + row] = 0xFF
    
    # Tile $06: Border box (color 1)
    chr_rom[0x060] = 0xFF
    for row in range(1, 7):
        chr_rom[0x060 + row] = 0x81
    chr_rom[0x067] = 0xFF
    for row in range(8):
        chr_rom[0x068 + row] = 0x00
    
    # Tile $07: X pattern (color 1)
    for row in range(8):
        left = 0x80 >> row
        right = 0x01 << row
        chr_rom[0x070 + row] = left | right
        chr_rom[0x078 + row] = 0x00
    
    # =========================================================================
    # PRG-ROM: Minimal program - just set up PPU and enable rendering
    # =========================================================================
    pc = 0  # Offset in ROM (maps to $8000)
    
    # reset: Entry point at $8000
    rom[pc] = 0x78; pc += 1  # SEI - disable IRQs
    rom[pc] = 0xD8; pc += 1  # CLD - disable decimal mode
    
    # Disable PPU during setup
    rom[pc] = 0xA9; rom[pc+1] = 0x00; pc += 2  # LDA #$00
    rom[pc] = 0x8D; rom[pc+1] = 0x00; rom[pc+2] = 0x20; pc += 3  # STA $2000
    rom[pc] = 0x8D; rom[pc+1] = 0x01; rom[pc+2] = 0x20; pc += 3  # STA $2001
    
    # Small delay loop instead of vblank wait
    rom[pc] = 0xA2; rom[pc+1] = 0x10; pc += 2  # LDX #$10
    delay1 = pc
    rom[pc] = 0xCA; pc += 1  # DEX
    rom[pc] = 0xD0; rom[pc+1] = 0xFD; pc += 2  # BNE delay1
    
    # =========================================================================
    # Load palette at $3F00
    # =========================================================================
    # Reset PPU latch by reading $2002
    rom[pc] = 0xAD; rom[pc+1] = 0x02; rom[pc+2] = 0x20; pc += 3  # LDA $2002
    
    # Set PPU address to $3F00
    rom[pc] = 0xA9; rom[pc+1] = 0x3F; pc += 2  # LDA #$3F
    rom[pc] = 0x8D; rom[pc+1] = 0x06; rom[pc+2] = 0x20; pc += 3  # STA $2006
    rom[pc] = 0xA9; rom[pc+1] = 0x00; pc += 2  # LDA #$00
    rom[pc] = 0x8D; rom[pc+1] = 0x06; rom[pc+2] = 0x20; pc += 3  # STA $2006
    
    # Write background palette (4 colors x 4 palettes = 16 bytes)
    # Palette 0: Sky blue theme
    palette = [
        0x21,  # $3F00: Light blue (universal background)
        0x0F, 0x10, 0x30,  # $3F01-03: black, gray, white
        0x21,  # $3F04: (mirror of bg)
        0x06, 0x16, 0x26,  # $3F05-07: red shades
        0x21,  # $3F08: (mirror of bg)  
        0x09, 0x19, 0x29,  # $3F09-0B: green shades
        0x21,  # $3F0C: (mirror of bg)
        0x02, 0x12, 0x22,  # $3F0D-0F: blue shades
    ]
    
    for color in palette:
        rom[pc] = 0xA9; rom[pc+1] = color; pc += 2  # LDA #color
        rom[pc] = 0x8D; rom[pc+1] = 0x07; rom[pc+2] = 0x20; pc += 3  # STA $2007
    
    # =========================================================================
    # Fill nametable at $2000 with tile pattern
    # =========================================================================
    # Reset PPU latch
    rom[pc] = 0xAD; rom[pc+1] = 0x02; rom[pc+2] = 0x20; pc += 3  # LDA $2002
    
    # Set PPU address to $2000
    rom[pc] = 0xA9; rom[pc+1] = 0x20; pc += 2  # LDA #$20
    rom[pc] = 0x8D; rom[pc+1] = 0x06; rom[pc+2] = 0x20; pc += 3  # STA $2006
    rom[pc] = 0xA9; rom[pc+1] = 0x00; pc += 2  # LDA #$00
    rom[pc] = 0x8D; rom[pc+1] = 0x06; rom[pc+2] = 0x20; pc += 3  # STA $2006
    
    # Fill with tiles (32x30 = 960 tiles)
    # Outer loop: 4 pages (256 bytes each = 1024, close enough)
    rom[pc] = 0xA0; rom[pc+1] = 0x04; pc += 2  # LDY #$04
    
    page_loop = pc
    rom[pc] = 0xA2; rom[pc+1] = 0x00; pc += 2  # LDX #$00
    
    tile_loop = pc
    # Write tile number = X & 0x07 (cycles through tiles 0-7)
    rom[pc] = 0x8A; pc += 1  # TXA
    rom[pc] = 0x29; rom[pc+1] = 0x07; pc += 2  # AND #$07
    rom[pc] = 0x8D; rom[pc+1] = 0x07; rom[pc+2] = 0x20; pc += 3  # STA $2007
    rom[pc] = 0xE8; pc += 1  # INX
    rom[pc] = 0xD0; rom[pc+1] = (tile_loop - (pc + 2)) & 0xFF; pc += 2  # BNE tile_loop
    
    rom[pc] = 0x88; pc += 1  # DEY
    rom[pc] = 0xD0; rom[pc+1] = (page_loop - (pc + 2)) & 0xFF; pc += 2  # BNE page_loop
    
    # =========================================================================
    # Fill attribute table at $23C0 with palette 0
    # =========================================================================
    rom[pc] = 0xAD; rom[pc+1] = 0x02; rom[pc+2] = 0x20; pc += 3  # LDA $2002
    rom[pc] = 0xA9; rom[pc+1] = 0x23; pc += 2  # LDA #$23
    rom[pc] = 0x8D; rom[pc+1] = 0x06; rom[pc+2] = 0x20; pc += 3  # STA $2006
    rom[pc] = 0xA9; rom[pc+1] = 0xC0; pc += 2  # LDA #$C0
    rom[pc] = 0x8D; rom[pc+1] = 0x06; rom[pc+2] = 0x20; pc += 3  # STA $2006
    
    # Write 64 bytes of attribute (all zeros = palette 0)
    rom[pc] = 0xA9; rom[pc+1] = 0x00; pc += 2  # LDA #$00
    rom[pc] = 0xA2; rom[pc+1] = 0x40; pc += 2  # LDX #$40 (64 bytes)
    attr_loop = pc
    rom[pc] = 0x8D; rom[pc+1] = 0x07; rom[pc+2] = 0x20; pc += 3  # STA $2007
    rom[pc] = 0xCA; pc += 1  # DEX
    rom[pc] = 0xD0; rom[pc+1] = (attr_loop - (pc + 2)) & 0xFF; pc += 2  # BNE attr_loop
    
    # =========================================================================
    # Reset scroll position
    # =========================================================================
    rom[pc] = 0xAD; rom[pc+1] = 0x02; rom[pc+2] = 0x20; pc += 3  # LDA $2002
    rom[pc] = 0xA9; rom[pc+1] = 0x00; pc += 2  # LDA #$00
    rom[pc] = 0x8D; rom[pc+1] = 0x05; rom[pc+2] = 0x20; pc += 3  # STA $2005 (X scroll)
    rom[pc] = 0x8D; rom[pc+1] = 0x05; rom[pc+2] = 0x20; pc += 3  # STA $2005 (Y scroll)
    
    # =========================================================================
    # ENABLE RENDERING!
    # =========================================================================
    # PPUCTRL: Use pattern table 0 for BG, nametable 0
    rom[pc] = 0xA9; rom[pc+1] = 0x00; pc += 2  # LDA #$00
    rom[pc] = 0x8D; rom[pc+1] = 0x00; rom[pc+2] = 0x20; pc += 3  # STA $2000
    
    # PPUMASK: Enable BG rendering (bit 3), show BG in left 8 pixels (bit 1)
    rom[pc] = 0xA9; rom[pc+1] = 0x0A; pc += 2  # LDA #$0A (BG enable + show left)
    rom[pc] = 0x8D; rom[pc+1] = 0x01; rom[pc+2] = 0x20; pc += 3  # STA $2001
    
    # =========================================================================
    # Main loop - blink LED to show we're running
    # =========================================================================
    rom[pc] = 0xA9; rom[pc+1] = 0x00; pc += 2  # LDA #$00
    rom[pc] = 0x85; rom[pc+1] = 0x00; pc += 2  # STA $00 (zero page counter)
    
    main_loop = pc
    # Increment counter
    rom[pc] = 0xE6; rom[pc+1] = 0x00; pc += 2  # INC $00
    # Write to LED register at $00FF
    rom[pc] = 0xA5; rom[pc+1] = 0x00; pc += 2  # LDA $00
    rom[pc] = 0x8D; rom[pc+1] = 0xFF; rom[pc+2] = 0x00; pc += 3  # STA $00FF
    
    # Delay loop
    rom[pc] = 0xA2; rom[pc+1] = 0xFF; pc += 2  # LDX #$FF
    delay_loop = pc
    rom[pc] = 0xA0; rom[pc+1] = 0xFF; pc += 2  # LDY #$FF
    inner_delay = pc
    rom[pc] = 0x88; pc += 1  # DEY
    rom[pc] = 0xD0; rom[pc+1] = 0xFD; pc += 2  # BNE inner_delay
    rom[pc] = 0xCA; pc += 1  # DEX
    rom[pc] = 0xD0; rom[pc+1] = (delay_loop - (pc + 2)) & 0xFF; pc += 2  # BNE delay_loop
    
    # Loop back
    rom[pc] = 0x4C  # JMP main_loop
    rom[pc+1] = (0x8000 + main_loop) & 0xFF
    rom[pc+2] = ((0x8000 + main_loop) >> 8) & 0xFF
    pc += 3
    
    # NMI/IRQ handlers (just RTI)
    nmi_irq = pc
    rom[pc] = 0x40; pc += 1  # RTI
    
    # Set up vectors at end of ROM
    rom[0x7FFA] = (0x8000 + nmi_irq) & 0xFF  # NMI low
    rom[0x7FFB] = ((0x8000 + nmi_irq) >> 8) & 0xFF  # NMI high
    rom[0x7FFC] = 0x00  # Reset low ($8000)
    rom[0x7FFD] = 0x80  # Reset high
    rom[0x7FFE] = (0x8000 + nmi_irq) & 0xFF  # IRQ low
    rom[0x7FFF] = ((0x8000 + nmi_irq) >> 8) & 0xFF  # IRQ high
    
    print(f"Program size: {pc} bytes")
    print(f"Reset vector: $8000")
    print(f"NMI/IRQ handler at: ${0x8000 + nmi_irq:04X}")
    
    # Write PRG-ROM hex file
    with open('rtl/ppu_test_prg.hex', 'w') as f:
        for byte in rom:
            f.write(f'{byte:02X}\n')
    print("Wrote rtl/ppu_test_prg.hex")
    
    # Write CHR-ROM hex file
    with open('rtl/ppu_test_chr.hex', 'w') as f:
        for byte in chr_rom:
            f.write(f'{byte:02X}\n')
    print("Wrote rtl/ppu_test_chr.hex")

if __name__ == '__main__':
    main()
