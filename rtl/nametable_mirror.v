// NES Nametable Mirroring Logic
// Implements horizontal, vertical, and single-screen mirroring
// Maps 4KB logical nametable space to 2KB physical BRAM

module nametable_mirror (
    input  wire [11:0] ppu_vram_addr,  // $2000-$2FFF -> 12 bits
    input  wire [1:0]  mirroring,      // 0=Horiz, 1=Vert, 2=Single0, 3=Single1
    output wire [10:0] bram_addr       // 2KB = 11 bits
);

    wire [1:0] nt_select = ppu_vram_addr[11:10];
    
    // Determine which physical bank to use based on mirroring mode
    wire mapped_bank = (mirroring == 2'd0) ? nt_select[1] :  // Horizontal: use bit 11
                       (mirroring == 2'd1) ? nt_select[0] :  // Vertical: use bit 10
                       (mirroring == 2'd2) ? 1'b0 :          // Single screen 0
                                             1'b1;           // Single screen 1
    
    // Combine bank select with lower 10 bits
    assign bram_addr = {mapped_bank, ppu_vram_addr[9:0]};

endmodule
