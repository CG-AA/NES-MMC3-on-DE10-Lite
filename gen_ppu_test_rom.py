#!/usr/bin/env python3
"""
Generate a NES test ROM that displays a pattern on screen
This tests the full PPU integration (nametable, pattern table, palette)
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
    # Pattern table 0: tiles $00-$FF at CHR $0000-$0FFF
    # Pattern table 1: tiles $00-$FF at CHR $1000-$1FFF
    
    # Tile $00: Empty (all zeros) - already done
    
    # Tile $01: Solid block (all ones)
    for row in range(8):
        chr_rom[0x010 + row] = 0xFF  # Plane 0
        chr_rom[0x018 + row] = 0xFF  # Plane 1
    
    # Tile $02: Horizontal lines
    for row in range(8):
        chr_rom[0x020 + row] = 0xFF if (row % 2) == 0 else 0x00
        chr_rom[0x028 + row] = 0x00
    
    # Tile $03: Vertical lines
    for row in range(8):
        chr_rom[0x030 + row] = 0xAA  # 10101010
        chr_rom[0x038 + row] = 0x00
    
    # Tile $04: Checkerboard
    for row in range(8):
        chr_rom[0x040 + row] = 0xAA if (row % 2) == 0 else 0x55
        chr_rom[0x048 + row] = 0x00
    
    # Tile $05: Diagonal
    for row in range(8):
        chr_rom[0x050 + row] = (0x80 >> row) | (0x80 >> (row + 1)) if row < 7 else 0x01
        chr_rom[0x058 + row] = 0x00
    
    # Tile $06: Border (outline)
    chr_rom[0x060] = 0xFF
    for row in range(1, 7):
        chr_rom[0x060 + row] = 0x81
    chr_rom[0x067] = 0xFF
    for row in range(8):
        chr_rom[0x068 + row] = 0x00
    
    # Tile $07: X pattern
    for row in range(8):
        left = 0x80 >> row
        right = 0x01 << row
        chr_rom[0x070 + row] = left | right
        chr_rom[0x078 + row] = 0x00
    
    # =========================================================================
    # PRG-ROM: NES program to display the pattern
    # =========================================================================
    # 
    # Memory map:
    # $2000 PPUCTRL - PPU control register
    # $2001 PPUMASK - PPU mask register
    # $2002 PPUSTATUS - PPU status register
    # $2005 PPUSCROLL - PPU scroll register
    # $2006 PPUADDR - PPU address register (write twice for 16-bit addr)
    # $2007 PPUDATA - PPU data register
    
    pc = 0  # Offset in ROM (maps to $8000)
    
    # reset: Entry point at $8000
    # Initialize the NES
    rom[pc] = 0x78; pc += 1  # SEI - disable IRQs
    rom[pc] = 0xD8; pc += 1  # CLD - disable decimal mode
    rom[pc] = 0xA9; rom[pc+1] = 0x00; pc += 2  # LDA #$00
    rom[pc] = 0x8D; rom[pc+1] = 0x00; rom[pc+2] = 0x20; pc += 3  # STA $2000 - disable NMI
    rom[pc] = 0x8D; rom[pc+1] = 0x01; rom[pc+2] = 0x20; pc += 3  # STA $2001 - disable rendering
    
    # Wait for first vblank
    # vblank1:
    vblank1 = pc
    rom[pc] = 0x2C; rom[pc+1] = 0x02; rom[pc+2] = 0x20; pc += 3  # BIT $2002
    rom[pc] = 0x10  # BPL vblank1
    rom[pc+1] = (vblank1 - (pc + 2)) & 0xFF; pc += 2
    
    # Wait for second vblank (PPU warm up)
    # vblank2:
    vblank2 = pc
    rom[pc] = 0x2C; rom[pc+1] = 0x02; rom[pc+2] = 0x20; pc += 3  # BIT $2002
    rom[pc] = 0x10  # BPL vblank2
    rom[pc+1] = (vblank2 - (pc + 2)) & 0xFF; pc += 2
    
    # Load palette
    # Set PPU address to $3F00 (palette RAM)
    rom[pc] = 0x2C; rom[pc+1] = 0x02; rom[pc+2] = 0x20; pc += 3  # BIT $2002 - reset latch
    rom[pc] = 0xA9; rom[pc+1] = 0x3F; pc += 2  # LDA #$3F
    rom[pc] = 0x8D; rom[pc+1] = 0x06; rom[pc+2] = 0x20; pc += 3  # STA $2006
    rom[pc] = 0xA9; rom[pc+1] = 0x00; pc += 2  # LDA #$00
    rom[pc] = 0x8D; rom[pc+1] = 0x06; rom[pc+2] = 0x20; pc += 3  # STA $2006
    
    # Write palette data (32 bytes)
    # Background palettes (16 bytes)
    palette = [
        0x0F, 0x00, 0x10, 0x20,  # BG palette 0: black, dark gray, light gray, white
        0x0F, 0x06, 0x16, 0x26,  # BG palette 1: black, red tones
        0x0F, 0x09, 0x19, 0x29,  # BG palette 2: black, green tones
        0x0F, 0x02, 0x12, 0x22,  # BG palette 3: black, blue tones
        # Sprite palettes (16 bytes)
        0x0F, 0x00, 0x10, 0x20,  # Sprite palette 0
        0x0F, 0x06, 0x16, 0x26,  # Sprite palette 1
        0x0F, 0x09, 0x19, 0x29,  # Sprite palette 2
        0x0F, 0x02, 0x12, 0x22,  # Sprite palette 3
    ]
    
    for color in palette:
        rom[pc] = 0xA9; rom[pc+1] = color; pc += 2  # LDA #color
        rom[pc] = 0x8D; rom[pc+1] = 0x07; rom[pc+2] = 0x20; pc += 3  # STA $2007
    
    # Fill nametable 0 ($2000-$23BF) with a pattern
    # Set PPU address to $2000
    rom[pc] = 0x2C; rom[pc+1] = 0x02; rom[pc+2] = 0x20; pc += 3  # BIT $2002
    rom[pc] = 0xA9; rom[pc+1] = 0x20; pc += 2  # LDA #$20
    rom[pc] = 0x8D; rom[pc+1] = 0x06; rom[pc+2] = 0x20; pc += 3  # STA $2006
    rom[pc] = 0xA9; rom[pc+1] = 0x00; pc += 2  # LDA #$00
    rom[pc] = 0x8D; rom[pc+1] = 0x06; rom[pc+2] = 0x20; pc += 3  # STA $2006
    
    # Write 960 bytes of nametable (32x30 tiles)
    # Use Y for outer loop (pages), X for inner loop
    rom[pc] = 0xA0; rom[pc+1] = 0x04; pc += 2  # LDY #$04 (4 pages = 1024 bytes, close enough)
    
    page_loop = pc
    rom[pc] = 0xA2; rom[pc+1] = 0x00; pc += 2  # LDX #$00
    
    tile_loop = pc
    # Create a pattern: tile number = (X + Y*4) mod 8
    rom[pc] = 0x8A; pc += 1  # TXA
    rom[pc] = 0x29; rom[pc+1] = 0x07; pc += 2  # AND #$07 - use low 3 bits
    rom[pc] = 0x8D; rom[pc+1] = 0x07; rom[pc+2] = 0x20; pc += 3  # STA $2007
    rom[pc] = 0xE8; pc += 1  # INX
    rom[pc] = 0xD0  # BNE tile_loop
    rom[pc+1] = (tile_loop - (pc + 2)) & 0xFF; pc += 2
    
    rom[pc] = 0x88; pc += 1  # DEY
    rom[pc] = 0xD0  # BNE page_loop
    rom[pc+1] = (page_loop - (pc + 2)) & 0xFF; pc += 2
    
    # Reset scroll position
    rom[pc] = 0x2C; rom[pc+1] = 0x02; rom[pc+2] = 0x20; pc += 3  # BIT $2002
    rom[pc] = 0xA9; rom[pc+1] = 0x00; pc += 2  # LDA #$00
    rom[pc] = 0x8D; rom[pc+1] = 0x05; rom[pc+2] = 0x20; pc += 3  # STA $2005 (X scroll)
    rom[pc] = 0x8D; rom[pc+1] = 0x05; rom[pc+2] = 0x20; pc += 3  # STA $2005 (Y scroll)
    
    # Enable rendering
    rom[pc] = 0xA9; rom[pc+1] = 0x00; pc += 2  # LDA #$00 - use pattern table 0 for BG
    rom[pc] = 0x8D; rom[pc+1] = 0x00; rom[pc+2] = 0x20; pc += 3  # STA $2000
    rom[pc] = 0xA9; rom[pc+1] = 0x1E; pc += 2  # LDA #$1E - enable BG and sprites, show all
    rom[pc] = 0x8D; rom[pc+1] = 0x01; rom[pc+2] = 0x20; pc += 3  # STA $2001
    
    # Infinite loop (also write to LED register for debug)
    loop = pc
    rom[pc] = 0xE6; rom[pc+1] = 0x00; pc += 2  # INC $00
    rom[pc] = 0xA5; rom[pc+1] = 0x00; pc += 2  # LDA $00
    rom[pc] = 0x85; rom[pc+1] = 0xFF; pc += 2  # STA $FF (LED register)
    rom[pc] = 0x4C  # JMP loop
    rom[pc+1] = (0x8000 + loop) & 0xFF
    rom[pc+2] = ((0x8000 + loop) >> 8) & 0xFF
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
