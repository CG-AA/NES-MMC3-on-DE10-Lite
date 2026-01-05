#!/usr/bin/env python3
"""
Extract PRG and CHR ROM from NES file for FPGA loading.
Outputs .hex files compatible with Verilog $readmemh.
"""

import sys
import os

def extract_nes(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    
    # Parse iNES header
    if data[0:4] != b'NES\x1a':
        print("Error: Not a valid NES file")
        return False
    
    prg_size = data[4] * 16384  # 16KB units
    chr_size = data[5] * 8192   # 8KB units
    flags6 = data[6]
    flags7 = data[7]
    
    mapper = (flags6 >> 4) | (flags7 & 0xF0)
    mirroring = 'V' if (flags6 & 1) else 'H'
    has_trainer = bool(flags6 & 4)
    
    print(f"NES ROM: {filename}")
    print(f"  PRG ROM: {prg_size // 1024}KB")
    print(f"  CHR ROM: {chr_size // 1024}KB")
    print(f"  Mapper: {mapper}")
    print(f"  Mirroring: {mirroring}")
    print(f"  Trainer: {has_trainer}")
    
    if mapper != 0:
        print(f"Warning: Mapper {mapper} not supported, only NROM (0) works")
    
    # Calculate offsets
    header_size = 16
    trainer_size = 512 if has_trainer else 0
    prg_offset = header_size + trainer_size
    chr_offset = prg_offset + prg_size
    
    # Extract PRG ROM
    prg_data = data[prg_offset:prg_offset + prg_size]
    print(f"  PRG data: {len(prg_data)} bytes at offset {prg_offset}")
    
    # Extract CHR ROM
    chr_data = data[chr_offset:chr_offset + chr_size]
    print(f"  CHR data: {len(chr_data)} bytes at offset {chr_offset}")
    
    # For 16KB PRG, mirror to 32KB (NROM-128 style)
    if len(prg_data) == 16384:
        print("  Mirroring 16KB PRG to 32KB...")
        prg_data = prg_data + prg_data
    
    # Pad PRG to 32KB if needed
    if len(prg_data) < 32768:
        prg_data = prg_data + bytes(32768 - len(prg_data))
    
    # Pad CHR to 8KB if needed
    if len(chr_data) < 8192:
        chr_data = chr_data + bytes(8192 - len(chr_data))
    
    # Generate output filenames
    base = os.path.splitext(filename)[0]
    prg_hex = f"{base}_prg.hex"
    chr_hex = f"{base}_chr.hex"
    
    # Write PRG hex file
    with open(prg_hex, 'w') as f:
        for i, byte in enumerate(prg_data):
            f.write(f"{byte:02X}\n")
    print(f"  Wrote {prg_hex} ({len(prg_data)} bytes)")
    
    # Write CHR hex file
    with open(chr_hex, 'w') as f:
        for i, byte in enumerate(chr_data):
            f.write(f"{byte:02X}\n")
    print(f"  Wrote {chr_hex} ({len(chr_data)} bytes)")
    
    # Show reset vector
    reset_lo = prg_data[0x7FFC]  # $FFFC in 32KB PRG
    reset_hi = prg_data[0x7FFD]  # $FFFD
    reset_vec = (reset_hi << 8) | reset_lo
    print(f"  Reset vector: ${reset_vec:04X}")
    
    # Show NMI vector
    nmi_lo = prg_data[0x7FFA]
    nmi_hi = prg_data[0x7FFB]
    nmi_vec = (nmi_hi << 8) | nmi_lo
    print(f"  NMI vector: ${nmi_vec:04X}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: extract_nes_rom.py <rom.nes>")
        sys.exit(1)
    
    if not extract_nes(sys.argv[1]):
        sys.exit(1)
