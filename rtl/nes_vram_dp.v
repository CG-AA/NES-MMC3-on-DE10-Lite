// NES VRAM - Triple Port with registered reads for M9K inference
// 2KB nametable RAM
// Port A: CPU access (read/write)
// Port B: PPU nametable rendering (read-only)
// Port C: PPU attribute table rendering (read-only)
// Note: Quartus may duplicate memory to achieve 3 ports

module nes_vram_dp #(
    parameter MIRROR_V = 1,
    parameter INIT_FILE = ""
)(
    input         clk,
    
    // Port A - CPU access (read/write)
    input  [10:0] addr_a,
    input   [7:0] wdata_a,
    input         we_a,
    output reg [7:0] rdata_a,
    
    // Port B - PPU nametable rendering (read-only)
    input  [10:0] addr_b,
    output reg [7:0] rdata_b,
    
    // Port C - PPU attribute table rendering (read-only)
    input  [10:0] addr_c,
    output reg [7:0] rdata_c
);

    (* ram_init_file = INIT_FILE *)
    (* ramstyle = "M9K" *)
    reg [7:0] mem [0:2047];
    
    initial begin
        if (INIT_FILE != "") begin
            $readmemh(INIT_FILE, mem);
        end
    end
    
    // Port A - CPU access
    always @(posedge clk) begin
        if (we_a)
            mem[addr_a] <= wdata_a;
        rdata_a <= mem[addr_a];
    end
    
    // Port B - PPU nametable rendering (registered read)
    always @(posedge clk) begin
        rdata_b <= mem[addr_b];
    end
    
    // Port C - PPU attribute table rendering (registered read)
    always @(posedge clk) begin
        rdata_c <= mem[addr_c];
    end

endmodule
