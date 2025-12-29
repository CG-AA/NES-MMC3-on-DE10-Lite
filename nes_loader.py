#!/usr/bin/env python3
import sys
import os
import argparse
import time
from litex.tools.litex_client import RemoteClient

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================
INES_HEADER_SIZE = 16
PRG_RAM_OFFSET   = 0x00000000
CHR_RAM_OFFSET   = 0x00080000  # +512KB

# STRUCTURAL FIX: BATCHING
# Instead of Read-After-Write (too slow) or Blind-Write (overflows),
# We write N packets, then read 1 word to force a pipeline sync.
# This prevents the UDP buffer from filling up and dropping packets.
SYNC_INTERVAL_PACKETS = 32  # Sync every 32 packets
PACKET_SIZE_SIM       = 128 # Bytes per UDP packet (Sim)
PACKET_SIZE_HW        = 255 # Bytes per UART packet (Hardware)

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
# ROBUST TRANSFER PROTOCOL
# =============================================================================
def robust_write(wb, base_addr, data, packet_size, is_sim):
    """
    Writes data using a Batched Window strategy to prevent buffer overflow.
    """
    total_len = len(data)
    packets_sent = 0
    start_time = time.time()
    
    # Pre-calculate chunks to avoid slicing overhead in loop
    chunks = [data[i:i + packet_size] for i in range(0, total_len, packet_size)]
    total_chunks = len(chunks)

    print(f"       Mode: {'Simulation (Throttled)' if is_sim else 'Hardware (Fast)'}")
    print(f"       Batch Size: Sync every {SYNC_INTERVAL_PACKETS} packets")

    for i, chunk in enumerate(chunks):
        current_addr = base_addr + (i * packet_size)
        
        # 1. Send Data (Blind Write)
        # RemoteClient handles the low-level packet construction
        wb.write(current_addr, list(chunk))
        packets_sent += 1

        # 2. Pipeline Sync (The Structural Fix)
        # If we have sent enough blind packets, force a read-back.
        # This blocks Python until the Sim/Board confirms it processed up to here.
        # It clears the UDP/UART buffer and prevents "Ghost Bytes".
        if packets_sent >= SYNC_INTERVAL_PACKETS:
            # Read 4 bytes from the last address we just wrote to confirm it's there
            # We don't even check the value here, we just want the 'ack' delay.
            _ = wb.read(current_addr, 4)
            packets_sent = 0 
            
            # Update UI only on sync (improves performance)
            percent = (i / total_chunks) * 100
            sys.stdout.write(f"\r       Uploading: {percent:.1f}%")
            sys.stdout.flush()

    duration = time.time() - start_time
    speed = (total_len / 1024) / duration if duration > 0 else 0
    print(f"\n       Write Finished ({duration:.2f}s @ {speed:.1f} KB/s)")
    return True

def robust_verify(wb, base_addr, data, packet_size):
    """
    Reads back data to verify integrity.
    """
    print("       Verifying Integrity...")
    total_len = len(data)
    errors = 0
    
    # We can read in larger chunks for verification usually, 
    # but let's stick to safe sizes to avoid timeouts.
    read_chunk_size = packet_size * 2
    
    for i in range(0, total_len, read_chunk_size):
        chunk_len = min(read_chunk_size, total_len - i)
        addr = base_addr + i
        
        # Read
        try:
            read_data = wb.read(addr, chunk_len)
        except Exception as e:
            print(f"\n[CRIT] Read timeout at 0x{addr:08x}: {e}")
            return False
            
        read_bytes = bytearray(read_data)
        expected_chunk = data[i : i + chunk_len]
        
        if read_bytes != expected_chunk:
            for j in range(chunk_len):
                if read_bytes[j] != expected_chunk[j]:
                    if errors < 5:
                        print(f"       [ERR] 0x{addr+j:08x}: Expected 0x{expected_chunk[j]:02x}, Got 0x{read_bytes[j]:02x}")
                    errors += 1
            if errors > 20:
                print("       (Error limit reached, aborting verify)")
                return False
                
        sys.stdout.write(f"\r       Progress: {((i+chunk_len)/total_len)*100:.1f}%")
        sys.stdout.flush()
        
    print("")
    return errors == 0

# =============================================================================
# MAIN LOGIC
# =============================================================================
def upload_sequence(host, port, csr_csv, nes_data, is_sim):
    print(f"\n[CONN] Connecting to LiteX Bridge ({host}:{port})...")
    wb = RemoteClient(host=host, port=port, csr_csv=csr_csv)
    wb.open()

    try:
        base_addr = wb.mems.main_ram.base
        print(f"[CONF] SDRAM Base: 0x{base_addr:08x}")
    except:
        base_addr = 0x40000000
        print(f"[WARN] Defaulting SDRAM to 0x{base_addr:08x}")

    # Tune settings based on target
    packet_size = PACKET_SIZE_SIM if is_sim else PACKET_SIZE_HW

    # --- PROCESS PRG ---
    print(f"\n[PRG] Processing {len(nes_data.prg_data)} bytes...")
    robust_write(wb, base_addr + PRG_RAM_OFFSET, nes_data.prg_data, packet_size, is_sim)
    if not robust_verify(wb, base_addr + PRG_RAM_OFFSET, nes_data.prg_data, packet_size):
        print("\n\033[91m[FAIL] PRG-ROM Verify Failed.\033[0m")
        return False
    print("\033[92m[PASS] PRG-ROM Verified.\033[0m")

    # --- PROCESS CHR ---
    print(f"\n[CHR] Processing {len(nes_data.chr_data)} bytes...")
    robust_write(wb, base_addr + CHR_RAM_OFFSET, nes_data.chr_data, packet_size, is_sim)
    if not robust_verify(wb, base_addr + CHR_RAM_OFFSET, nes_data.chr_data, packet_size):
        print("\n\033[91m[FAIL] CHR-ROM Verify Failed.\033[0m")
        return False
    print("\033[92m[PASS] CHR-ROM Verified.\033[0m")

    wb.close()
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", help="Path to .nes file")
    parser.add_argument("--csr", default="csr.csv", help="LiteX CSR map")
    parser.add_argument("--sim", action="store_true", help="Enable simulation tuning (slower, safer)")
    args = parser.parse_args()
    
    if not os.path.exists(args.rom): sys.exit(f"[ERR] File not found: {args.rom}")
    
    nes = NESParser(args.rom)
    nes.parse()
    
    try:
        success = upload_sequence("localhost", 1234, args.csr, nes, args.sim)
    except Exception as e:
        print(f"\n[CRIT] {e}")
        sys.exit(1)
        
    if success:
        print("\n\033[92m[PHASE 1 COMPLETE] Memory Integrity Verified.\033[0m")
    else:
        sys.exit(1)