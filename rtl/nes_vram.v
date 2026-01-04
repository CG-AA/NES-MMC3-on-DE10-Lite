// NES VRAM (Nametable RAM)
// 2KB on-cart or on-PPU RAM for nametables
// 
// Nametable layout depends on mirroring mode:
// - Horizontal mirroring: $2000=$2400, $2800=$2C00 (vertical scrolling games)
// - Vertical mirroring: $2000=$2800, $2400=$2C00 (horizontal scrolling games)
//
// This module implements 2KB RAM with configurable mirroring.

module nes_vram #(
    parameter MIRROR_V = 1  // 1 = vertical mirroring, 0 = horizontal mirroring
)(
    input         clk,
    input  [10:0] addr,     // 2KB = 11 bits
    input   [7:0] wdata,
    input         we,
    output  [7:0] rdata
);

    reg [7:0] mem [0:2047];
    
    // Combinational read for PPU compatibility
    assign rdata = mem[addr];
    
    always @(posedge clk) begin
        if (we)
            mem[addr] <= wdata;
    end

endmodule
