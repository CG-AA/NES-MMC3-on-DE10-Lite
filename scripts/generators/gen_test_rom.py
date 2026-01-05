#!/usr/bin/env python3
"""
Generate a simple test ROM for 6502 LED blinker
Creates a 32KB ROM with a simple program that increments a counter
and writes it to $00FF (LED port)
"""

def main():
    # 32KB ROM
    rom = [0x00] * 32768
    
    # Program starts at $8000 (offset 0 in our BRAM)
    # We'll put the main code at the beginning
    
    # Simple LED blinker program
    # Assembled by hand:
    #
    # reset:    ; $8000
    #   SEI           ; 78
    #   CLD           ; D8
    #   LDX #$FF      ; A2 FF
    #   TXS           ; 9A
    #   LDA #$00      ; A9 00
    #   STA $00       ; 85 00    ; counter in zero page
    # loop:     ; $800A
    #   INC $00       ; E6 00
    #   LDA $00       ; A5 00
    #   STA $FF       ; 85 FF    ; write to LED port
    #   ; Delay loop
    #   LDX #$00      ; A2 00
    # delay1:   ; $8012
    #   LDY #$00      ; A0 00
    # delay2:   ; $8014
    #   DEY           ; 88
    #   BNE delay2    ; D0 FD    ; branch to $8014
    #   DEX           ; CA
    #   BNE delay1    ; D0 F8    ; branch to $8012
    #   JMP loop      ; 4C 0A 80 ; jump to $800A
    # nmi:
    # irq:
    #   RTI           ; 40
    
    program = [
        0x78,             # $8000: SEI
        0xD8,             # $8001: CLD
        0xA2, 0xFF,       # $8002: LDX #$FF
        0x9A,             # $8004: TXS
        0xA9, 0x00,       # $8005: LDA #$00
        0x85, 0x00,       # $8007: STA $00
        # loop: offset $09 = address $8009
        0xE6, 0x00,       # $8009: INC $00
        0xA5, 0x00,       # $800B: LDA $00
        0x85, 0xFF,       # $800D: STA $FF
        0xA2, 0x00,       # $800F: LDX #$00
        # delay1: offset $11 = address $8011
        0xA0, 0x00,       # $8011: LDY #$00
        # delay2: offset $13 = address $8013
        0x88,             # $8013: DEY
        0xD0, 0xFD,       # $8014: BNE delay2 (-3 -> $8013)
        0xCA,             # $8016: DEX
        0xD0, 0xF8,       # $8017: BNE delay1 (-8 -> $8011)
        0x4C, 0x09, 0x80, # $8019: JMP $8009 (loop) -- FIXED!
        # nmi/irq: offset $1C = address $801C
        0x40,             # $801C: RTI
    ]
    
    # Copy program to start of ROM
    for i, byte in enumerate(program):
        rom[i] = byte
    
    # Set up vectors at end of ROM
    # Vectors are at $FFFA-$FFFF, which is offset $7FFA-$7FFF in our 32KB ROM
    # NMI vector: $801C (RTI handler)
    rom[0x7FFA] = 0x1C
    rom[0x7FFB] = 0x80
    # Reset vector: $8000
    rom[0x7FFC] = 0x00
    rom[0x7FFD] = 0x80
    # IRQ vector: $801C (RTI handler)
    rom[0x7FFE] = 0x1C
    rom[0x7FFF] = 0x80
    
    # Write as hex file (Verilog $readmemh format)
    with open('rtl/test_rom.hex', 'w') as f:
        for i, byte in enumerate(rom):
            f.write(f'{byte:02X}\n')
    
    print(f"Generated test_rom.hex ({len(rom)} bytes)")
    print(f"Reset vector: ${rom[0x7FFC]:02X}{rom[0x7FFD]:02X}")
    print(f"Program at $8000:")
    for i, byte in enumerate(program[:20]):
        print(f"  ${0x8000+i:04X}: ${byte:02X}")

if __name__ == '__main__':
    main()
