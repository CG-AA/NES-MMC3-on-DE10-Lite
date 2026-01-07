#!/usr/bin/env python3
"""
Switch NES game by extracting ROM, updating RTL, and recompiling.

Usage:
    python switch_game.py <game.nes>
    python switch_game.py super_mario_bros.nes --compile
    python switch_game.py --list  # Show available pre-extracted games
"""

import sys
import os
import subprocess
import shutil
import argparse

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
ROM_DATA_DIR = os.path.join(PROJECT_DIR, "rom_data")
RTL_DIR = os.path.join(PROJECT_DIR, "rtl")
QUARTUS_DIR = os.path.join(PROJECT_DIR, "quartus_nes_vga")
ROMS_DIR = os.path.join(PROJECT_DIR, "roms")

# Import extract function
sys.path.insert(0, SCRIPT_DIR)
from extract_nes_rom import extract_nes, MAPPER_NAMES


def get_rom_info_only(filename):
    """Get ROM info without extracting files. Returns dict or None."""
    try:
        with open(filename, 'rb') as f:
            data = f.read(16)  # Just need header
        
        if data[0:4] != b'NES\x1a':
            return None
        
        prg_size = data[4] * 16384
        chr_size = data[5] * 8192
        flags6 = data[6]
        flags7 = data[7]
        
        mapper = (flags6 >> 4) | (flags7 & 0xF0)
        mirroring = 'V' if (flags6 & 1) else 'H'
        mirror_v = 1 if (flags6 & 1) else 0
        chr_ram = (chr_size == 0)
        mapper_name = MAPPER_NAMES.get(mapper, f"Unknown ({mapper})")
        
        return {
            'prg_size': prg_size,
            'chr_size': chr_size,
            'mapper': mapper,
            'mapper_name': mapper_name,
            'mirroring': mirroring,
            'mirror_v': mirror_v,
            'chr_ram': chr_ram,
        }
    except Exception as e:
        print(f"Error reading ROM info: {e}")
        return None


def find_nes_file(name):
    """Find NES file by name in roms/ directory."""
    # Direct path
    if os.path.exists(name):
        return name
    
    # Check roms/ directory
    rom_path = os.path.join(ROMS_DIR, name)
    if os.path.exists(rom_path):
        return rom_path
    
    # Add .nes extension
    if not name.endswith('.nes'):
        rom_path = os.path.join(ROMS_DIR, name + '.nes')
        if os.path.exists(rom_path):
            return rom_path
    
    return None


def list_available_games():
    """List games with pre-extracted hex files."""
    print("\n=== Available Pre-Extracted Games ===")
    
    if not os.path.exists(ROM_DATA_DIR):
        print("No rom_data/ directory found")
        return
    
    games = set()
    for f in os.listdir(ROM_DATA_DIR):
        if f.endswith('_prg.hex'):
            games.add(f.replace('_prg.hex', ''))
    
    if games:
        for game in sorted(games):
            prg = os.path.join(ROM_DATA_DIR, f"{game}_prg.hex")
            chr_file = os.path.join(ROM_DATA_DIR, f"{game}_chr.hex")
            prg_size = os.path.getsize(prg) // 3 if os.path.exists(prg) else 0  # Approx bytes
            chr_size = os.path.getsize(chr_file) // 3 if os.path.exists(chr_file) else 0
            
            # Try to get mapper/mirroring info from original NES file
            nes_file = os.path.join(ROMS_DIR, f"{game}.nes")
            info_str = ""
            if os.path.exists(nes_file):
                rom_info = get_rom_info_only(nes_file)
                if rom_info:
                    info_str = f" | Mapper {rom_info['mapper']} | Mirror={rom_info['mirroring']}"
            
            print(f"  {game}: PRG={prg_size//1024}KB, CHR={chr_size//1024}KB{info_str}")
    else:
        print("  No pre-extracted games found")
    
    print("\n=== Available ROM Files ===")
    if os.path.exists(ROMS_DIR):
        roms = [f for f in os.listdir(ROMS_DIR) if f.endswith('.nes')]
        for rom in sorted(roms):
            rom_path = os.path.join(ROMS_DIR, rom)
            rom_info = get_rom_info_only(rom_path)
            if rom_info:
                mapper_name = rom_info.get('mapper_name', '?')
                mirroring = rom_info['mirroring']
                print(f"  {rom}: {mapper_name}, Mirror={mirroring}")
            else:
                print(f"  {rom}")
    else:
        print("  No roms/ directory found")


def update_rtl_init_files(game_name, rom_info=None):
    """Update nes_top_ppu.v to use new ROM files and parameters."""
    top_file = os.path.join(RTL_DIR, "nes_top_ppu.v")
    
    if not os.path.exists(top_file):
        print(f"Error: {top_file} not found")
        return False
    
    with open(top_file, 'r') as f:
        content = f.read()
    
    # Update PRG ROM init file
    import re
    
    # Match .INIT_FILE("...xxx_prg.hex") pattern - may include rom_data/ prefix
    prg_pattern = r'\.INIT_FILE\s*\(\s*"[^"]*_prg\.hex"\s*\)'
    chr_pattern = r'\.INIT_FILE\s*\(\s*"[^"]*_chr\.hex"\s*\)'
    
    # Use ../rom_data/ prefix - paths are relative to quartus_nes_vga/ directory
    new_prg = f'.INIT_FILE("../rom_data/{game_name}_prg.hex")'
    new_chr = f'.INIT_FILE("../rom_data/{game_name}_chr.hex")'
    
    # Check if patterns exist (even if replacement is the same)
    prg_matches = re.findall(prg_pattern, content)
    chr_matches = re.findall(chr_pattern, content)
    
    if not prg_matches and not chr_matches:
        print("Warning: No INIT_FILE patterns found to update")
        return False
    
    new_content = re.sub(prg_pattern, new_prg, content)
    new_content = re.sub(chr_pattern, new_chr, new_content)
    
    # Update MIRROR_V parameter if we have ROM info
    if rom_info:
        mirror_v = rom_info.get('mirror_v', 0)
        mirroring = rom_info.get('mirroring', 'H')
        
        # Match .MIRROR_V(0) or .MIRROR_V(1) with optional comment
        mirror_pattern = r'\.MIRROR_V\s*\(\s*[01]\s*\)\s*,?\s*(//[^\n]*)?'
        mirror_comment = f"// {game_name} uses {'vertical' if mirror_v else 'horizontal'} mirroring"
        new_mirror = f'.MIRROR_V({mirror_v}),  {mirror_comment}'
        
        if re.search(mirror_pattern, new_content):
            new_content = re.sub(mirror_pattern, new_mirror, new_content)
            print(f"  MIRROR_V: {mirror_v} ({mirroring} mirroring)")
        else:
            print(f"  Warning: MIRROR_V pattern not found (mirroring may be wrong)")
    
    with open(top_file, 'w') as f:
        f.write(new_content)
    
    print(f"Updated {top_file}")
    print(f"  PRG: ../rom_data/{game_name}_prg.hex")
    print(f"  CHR: ../rom_data/{game_name}_chr.hex")
    return True


def copy_hex_to_quartus(game_name):
    """Verify hex files exist in rom_data/ directory."""
    prg_src = os.path.join(ROM_DATA_DIR, f"{game_name}_prg.hex")
    chr_src = os.path.join(ROM_DATA_DIR, f"{game_name}_chr.hex")
    
    if not os.path.exists(prg_src):
        print(f"Error: {prg_src} not found")
        return False
    if not os.path.exists(chr_src):
        print(f"Error: {chr_src} not found")
        return False
    
    print(f"ROM files verified in {ROM_DATA_DIR}")
    print(f"  PRG: {os.path.basename(prg_src)} ({os.path.getsize(prg_src)//1024}KB)")
    print(f"  CHR: {os.path.basename(chr_src)} ({os.path.getsize(chr_src)//1024}KB)")
    return True


def run_quartus_compile():
    """Run Quartus compilation from project root directory."""
    print("\n=== Running Quartus Compile ===")
    
    if not os.path.exists(QUARTUS_DIR):
        print(f"Error: Quartus directory {QUARTUS_DIR} not found")
        return False
    
    qpf_files = [f for f in os.listdir(QUARTUS_DIR) if f.endswith('.qpf')]
    if not qpf_files:
        print("Error: No .qpf file found")
        return False
    
    project_name = qpf_files[0].replace('.qpf', '')
    qpf_path = os.path.join(QUARTUS_DIR, f"{project_name}.qpf")
    
    # Run from project root so relative paths (rom_data/, rtl/) resolve correctly
    cmd = ['quartus_sh', '--flow', 'compile', qpf_path]
    print(f"Running: {' '.join(cmd)}")
    print("This may take 2-5 minutes...")
    
    result = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Compilation successful!")
        sof_file = os.path.join(QUARTUS_DIR, f"{project_name}.sof")
        if os.path.exists(sof_file):
            print(f"Bitstream: {sof_file}")
        return True
    else:
        print("❌ Compilation failed!")
        print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
        return False


def program_fpga():
    """Program FPGA with new bitstream."""
    print("\n=== Programming FPGA ===")
    
    sof_files = [f for f in os.listdir(QUARTUS_DIR) if f.endswith('.sof')]
    if not sof_files:
        print("Error: No .sof file found")
        return False
    
    sof_path = os.path.join(QUARTUS_DIR, sof_files[0])
    
    cmd = ['quartus_pgm', '-c', '1', '-m', 'JTAG', '-o', f'P;{sof_path}']
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ FPGA programmed successfully!")
        return True
    else:
        print("❌ Programming failed!")
        print(result.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description='Switch NES game on DE10-Lite')
    parser.add_argument('game', nargs='?', help='NES ROM file or game name')
    parser.add_argument('--list', action='store_true', help='List available games')
    parser.add_argument('--compile', action='store_true', help='Run Quartus compile')
    parser.add_argument('--program', action='store_true', help='Program FPGA after compile')
    parser.add_argument('--extract-only', action='store_true', help='Only extract ROM, do not update RTL')
    
    args = parser.parse_args()
    
    if args.list:
        list_available_games()
        return 0
    
    if not args.game:
        parser.print_help()
        return 1
    
    # Ensure directories exist
    os.makedirs(ROM_DATA_DIR, exist_ok=True)
    
    # Find the NES file
    nes_path = find_nes_file(args.game)
    rom_info = None
    
    if nes_path:
        print(f"\n=== Extracting {nes_path} ===")
        # Extract to rom_data/
        game_name = os.path.splitext(os.path.basename(nes_path))[0]
        
        # Run extraction (returns dict with ROM info or None on error)
        rom_info = extract_nes(nes_path)
        if not rom_info:
            print("Extraction failed!")
            return 1
        
        # Move hex files to rom_data/
        src_prg = nes_path.replace('.nes', '_prg.hex')
        src_chr = nes_path.replace('.nes', '_chr.hex')
        dst_prg = os.path.join(ROM_DATA_DIR, f"{game_name}_prg.hex")
        dst_chr = os.path.join(ROM_DATA_DIR, f"{game_name}_chr.hex")
        
        if os.path.exists(src_prg) and src_prg != dst_prg:
            shutil.move(src_prg, dst_prg)
        if os.path.exists(src_chr) and src_chr != dst_chr:
            shutil.move(src_chr, dst_chr)
        
        print(f"ROM files saved to {ROM_DATA_DIR}/")
    else:
        # Check if pre-extracted
        game_name = args.game.replace('.nes', '')
        prg_hex = os.path.join(ROM_DATA_DIR, f"{game_name}_prg.hex")
        if not os.path.exists(prg_hex):
            print(f"Error: Cannot find NES file or pre-extracted ROM for '{args.game}'")
            print("Use --list to see available games")
            return 1
        print(f"Using pre-extracted ROM: {game_name}")
        
        # Try to get ROM info from original NES file if it exists
        nes_in_roms = os.path.join(ROMS_DIR, f"{game_name}.nes")
        if os.path.exists(nes_in_roms):
            print(f"Reading ROM info from {nes_in_roms}...")
            rom_info = get_rom_info_only(nes_in_roms)
        else:
            print("Warning: Original .nes file not found, cannot determine mirroring mode")
            print("         MIRROR_V parameter will not be updated!")
    
    if args.extract_only:
        print("\nExtraction complete (--extract-only)")
        return 0
    
    # Update RTL
    print(f"\n=== Updating RTL for {game_name} ===")
    if not update_rtl_init_files(game_name, rom_info):
        return 1
    
    # Copy hex files to Quartus directory
    if not copy_hex_to_quartus(game_name):
        return 1
    
    # Compile if requested
    if args.compile:
        if not run_quartus_compile():
            return 1
        
        if args.program:
            if not program_fpga():
                return 1
    else:
        print("\nTo compile and program:")
        print(f"  python switch_game.py {args.game} --compile --program")
    
    # Print summary
    print("\n" + "="*50)
    print(f"✅ Game switch complete: {game_name}")
    print("="*50)
    if rom_info:
        print(f"  Mapper:    {rom_info.get('mapper', '?')} ({rom_info.get('mapper_name', 'Unknown')})")
        print(f"  Mirroring: {rom_info.get('mirroring', '?')} (MIRROR_V={rom_info.get('mirror_v', '?')})")
        print(f"  PRG Size:  {rom_info.get('prg_size', 0) // 1024}KB")
        if rom_info.get('chr_ram'):
            print(f"  CHR:       RAM (writable)")
        else:
            print(f"  CHR Size:  {rom_info.get('chr_size', 0) // 1024}KB")
    print("="*50)
    return 0


if __name__ == '__main__':
    sys.exit(main())
