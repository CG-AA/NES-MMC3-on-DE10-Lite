// NES Clock Generator
// Generates CPU and PPU clock enables from master NES clock
// Maintains 3:1 PPU/CPU ratio for accurate NES timing

module nes_clk_gen (
    input  wire clk_master,  // 21.477272 MHz from PLL
    input  wire rst,
    
    output reg  cpu_clk_en,  // 1.789773 MHz (every 12th cycle)
    output reg  ppu_clk_en   // 5.369318 MHz (every 4th cycle)
);

    reg [3:0] divider;  // 0-11 counter
    
    // Combinational enables - no 1-cycle delay
    // This ensures PPU and CPU see enables on the correct master cycle
    wire [3:0] next_divider = (divider == 4'd11) ? 4'd0 : divider + 4'd1;
    
    always @(posedge clk_master) begin
        if (rst) begin
            divider <= 4'd0;
        end else begin
            divider <= next_divider;
        end
    end
    
    // Combinational outputs - enables are valid on the cycle they're needed
    // PPU enable: cycles 0, 4, 8 (3 times per CPU cycle)
    always @(*) begin
        ppu_clk_en = (divider == 4'd0) || 
                     (divider == 4'd4) || 
                     (divider == 4'd8);
        
        // CPU enable: cycle 0 only (once per 12 master cycles)
        cpu_clk_en = (divider == 4'd0);
    end

endmodule
