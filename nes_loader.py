#!/usr/bin/env python3
import sys
import os
import argparse
import time
from litex.tools.litex_client import RemoteClient

# =============================================================================
# CONSTANTS
# =============================================================================
INES_HEADER_SIZE = 16
SDRAM_BASE_ADDR = 0x40000000
PRG_RAM_OFFSET  = 0x00000000
CHR_RAM_OFFSET  = 0x00080000  # +512KB

# =============================================================================
# NES PARSER
# =============================================================================
class NESParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.prg_data = bytearray()
        self.chr_data = bytearray()
        
    def parse(self):
        print(f"[INFO] Parsing {self.filepath}...")
        with open(self.filepath, "rb") as f:
            header = f.read(INES_HEADER_SIZE)
            if header[0:4] != b'NES\x1a':
                raise ValueError("Invalid NES ROM: Magic number mismatch.")
            
            prg_chunks = header[4]
            chr_chunks = header[5]
            prg_size = prg_chunks * 16384
            chr_size = chr_chunks * 8192
            
            print(f"       PRG-ROM: {prg_size / 1024:.1f} KB")
            print(f"       CHR-ROM: {chr_size / 1024:.1f} KB")
            
            self.prg_data = f.read(prg_size)
            self.chr_data = f.read(chr_size)
        return True

# =============================================================================
# LITEX BRIDGE
# =============================================================================
def upload_and_verify(host, port, csr_csv, nes_data, is_sim):
    print(f"\n[CONN] Connecting to LiteX Server at {host}:{port}...")
    
    # Simulation Settings: Smaller chunks, slower pace
    if is_sim:
        print("[MODE] Simulation detected. Throttling transfer speed.")
        CHUNK_SIZE = 256  # Small chunks to prevent UDP buffer overflow
        DELAY = 0.05      # Delay between chunks to let Sim catch up
    else:
        print("[MODE] Hardware mode. Full speed.")
        CHUNK_SIZE = 4096
        DELAY = 0.0

    wb = RemoteClient(host=host, port=port, csr_csv=csr_csv)
    wb.open()
    
    if not wb.regs:
        print("[ERR]  Could not connect to LiteX. Is litex_server running?")
        return False

    def process_blob(name, data, offset):
        total_len = len(data)
        if total_len == 0: return True
            
        start_addr = SDRAM_BASE_ADDR + offset
        print(f"[{name}] Uploading {total_len} bytes to 0x{start_addr:08x}...")
        
        # --- WRITE LOOP ---
        start_time = time.time()
        for i in range(0, total_len, CHUNK_SIZE):
            chunk = data[i : i + CHUNK_SIZE]
            addr = start_addr + i
            
            wb.write(addr, chunk)
            
            # SIMULATION THROTTLE
            if is_sim:
                time.sleep(DELAY)
            
            # Progress Bar
            percent = ((i + len(chunk)) / total_len) * 100
            sys.stdout.write(f"\r       Write: {percent:.1f}%")
            sys.stdout.flush()
            
        duration = time.time() - start_time
        speed = (total_len / 1024) / duration if duration > 0 else 0
        print(f"\n       Write Complete ({duration:.2f}s @ {speed:.1f} KB/s)")
        
        # Give the simulator a moment to settle before reading
        if is_sim: time.sleep(1.0)

        # --- VERIFY LOOP ---
        print(f"[{name}] Verifying...")
        errors = 0
        
        for i in range(0, total_len, CHUNK_SIZE):
            chunk_len = min(CHUNK_SIZE, total_len - i)
            addr = start_addr + i
            
            read_data = wb.read(addr, chunk_len)
            # SIMULATION THROTTLE
            if is_sim: time.sleep(DELAY)
            
            read_bytes = bytearray(read_data)
            expected_chunk = data[i : i + chunk_len]
            
            if read_bytes != expected_chunk:
                for j in range(chunk_len):
                    if read_bytes[j] != expected_chunk[j]:
                        if errors < 3:
                            print(f"       [ERR] 0x{addr+j:08x}: Wrote 0x{expected_chunk[j]:02x}, Read 0x{read_bytes[j]:02x}")
                        errors += 1
                if errors > 10:
                    print("       (Too many errors, stopping verification)")
                    return False
                
            sys.stdout.write(f"\r       Verify: {((i + chunk_len) / total_len) * 100:.1f}%")
            sys.stdout.flush()

        print("")
        if errors == 0:
            print(f"[{name}] \033[92mSUCCESS: Verified Bit-Perfect!\033[0m")
            return True
        else:
            print(f"[{name}] \033[91mFAILURE: {errors} mismatches.\033[0m")
            return False

    prg_ok = process_blob("PRG", nes_data.prg_data, PRG_RAM_OFFSET)
    chr_ok = process_blob("CHR", nes_data.chr_data, CHR_RAM_OFFSET)
    
    wb.close()
    return prg_ok and chr_ok

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", help="Path to .nes file")
    parser.add_argument("--csr", default="csr.csv", help="LiteX CSR map")
    parser.add_argument("--sim", action="store_true", help="Enable throttling for Simulation")
    args = parser.parse_args()
    
    if not os.path.exists(args.rom): sys.exit(f"[ERR] File not found: {args.rom}")
    
    nes = NESParser(args.rom)
    nes.parse()
    
    try:
        success = upload_and_verify("localhost", 1234, args.csr, nes, args.sim)
    except Exception as e:
        print(f"\n[CRIT] {e}")
        sys.exit(1)
        
    if success:
        print("\n\033[92m[PHASE 1 COMPLETE]\033[0m")
    else:
        sys.exit(1)