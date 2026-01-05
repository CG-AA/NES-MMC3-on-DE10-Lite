#!/usr/bin/env python3
"""
NES ROM Loader using LiteX SFL protocol (fast binary transfers)

Uses litex_term's serial boot functionality for fast uploads.

Usage:
    python3 nes_sfl_loader.py donkey_kong.nes
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


# SDRAM addresses
PRG_ROM_BASE = 0x40000000
CHR_ROM_BASE = 0x40080000


def parse_nes_header(data: bytes) -> dict:
    """Parse iNES header and return ROM info."""
    if len(data) < 16:
        raise ValueError("File too small for NES header")
    
    if data[0:4] != b'NES\x1a':
        raise ValueError("Not a valid NES file (missing NES header)")
    
    prg_banks = data[4]
    chr_banks = data[5]
    flags6 = data[6]
    flags7 = data[7]
    
    return {
        'prg_size': prg_banks * 16384,
        'chr_size': chr_banks * 8192,
        'mapper': (flags6 >> 4) | (flags7 & 0xF0),
        'mirroring': 'vertical' if (flags6 & 1) else 'horizontal',
        'has_trainer': bool(flags6 & 4),
        'prg_banks': prg_banks,
        'chr_banks': chr_banks,
    }


def main():
    parser = argparse.ArgumentParser(description='Load NES ROM via SFL protocol')
    parser.add_argument('rom', help='NES ROM file (.nes)')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--speed', type=int, default=115200, help='Baud rate')
    parser.add_argument('--chr', action='store_true', help='Also upload CHR-ROM')
    args = parser.parse_args()
    
    # Read ROM
    rom_path = Path(args.rom)
    if not rom_path.exists():
        print(f"Error: File not found: {args.rom}")
        return 1
    
    with open(args.rom, 'rb') as f:
        rom_data = f.read()
    
    # Parse header
    try:
        info = parse_nes_header(rom_data)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    print(f"\nNES ROM: {args.rom}")
    print(f"  PRG-ROM: {info['prg_size'] // 1024}KB")
    print(f"  CHR-ROM: {info['chr_size'] // 1024}KB")
    print(f"  Mapper:  {info['mapper']}")
    print()
    
    # Extract ROM data
    header_size = 16
    trainer_size = 512 if info['has_trainer'] else 0
    prg_offset = header_size + trainer_size
    chr_offset = prg_offset + info['prg_size']
    
    prg_data = rom_data[prg_offset:prg_offset + info['prg_size']]
    chr_data = rom_data[chr_offset:chr_offset + info['chr_size']] if info['chr_size'] > 0 else b''
    
    # Create temp files for binary data
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        prg_file = f.name
        f.write(prg_data)
    
    # Build images JSON
    images = {prg_file: f"0x{PRG_ROM_BASE:08x}"}
    
    if args.chr and chr_data:
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
            chr_file = f.name
            f.write(chr_data)
        images[chr_file] = f"0x{CHR_ROM_BASE:08x}"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json_file = f.name
        json.dump(images, f)
    
    print(f"Uploading via SFL protocol...")
    print(f"  Images: {json_file}")
    for path, addr in images.items():
        size = Path(path).stat().st_size
        print(f"    {path}: {size} bytes -> {addr}")
    
    # Run litex_term with serial boot
    cmd = [
        'litex_term',
        args.port,
        '--speed', str(args.speed),
        '--serial-boot',
        '--images', json_file,
    ]
    
    print(f"\nRunning: {' '.join(cmd)}")
    print("Press Ctrl+C when upload is complete...\n")
    
    try:
        result = subprocess.run(cmd, timeout=60)
        return result.returncode
    except subprocess.TimeoutExpired:
        print("\nUpload timed out")
        return 1
    except KeyboardInterrupt:
        print("\nUpload interrupted")
        return 0
    finally:
        # Cleanup temp files
        Path(prg_file).unlink(missing_ok=True)
        if args.chr and chr_data:
            Path(chr_file).unlink(missing_ok=True)
        Path(json_file).unlink(missing_ok=True)


if __name__ == '__main__':
    sys.exit(main())
