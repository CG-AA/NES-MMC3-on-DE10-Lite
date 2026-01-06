// CHR-ROM with multiple read ports for PPU rendering
// Uses M9K blocks with different access patterns
// Port 1: CPU access via PPU registers
// Port 2: Low bitplane for BG rendering
// Port 3: High bitplane for BG rendering
// Port 4: Debug display
// Port 5: Low bitplane for sprite rendering
// Port 6: High bitplane for sprite rendering

module nes_chr_multiport #(
    parameter INIT_FILE = ""
)(
    input         clk,
    
    // Port 1 - CPU access
    input  [12:0] addr1,
    output reg [7:0] rdata1,
    
    // Port 2 - BG Rendering low bitplane  
    input  [12:0] addr2,
    output reg [7:0] rdata2,
    
    // Port 3 - BG Rendering high bitplane
    input  [12:0] addr3,
    output reg [7:0] rdata3,
    
    // Port 4 - Debug
    input  [12:0] addr4,
    output reg [7:0] rdata4,
    
    // Port 5 - Sprite Rendering low bitplane
    input  [12:0] addr5,
    output reg [7:0] rdata5,
    
    // Port 6 - Sprite Rendering high bitplane
    input  [12:0] addr6,
    output reg [7:0] rdata6
);

    // Single memory array - Quartus will duplicate for ports if needed
    (* ram_init_file = INIT_FILE *)
    (* ramstyle = "M9K" *)
    reg [7:0] mem [0:8191];
    
    initial begin
        if (INIT_FILE != "") begin
            $readmemh(INIT_FILE, mem);
        end
    end
    
    // All ports are read-only, registered
    always @(posedge clk) begin
        rdata1 <= mem[addr1];
        rdata2 <= mem[addr2];
        rdata3 <= mem[addr3];
        rdata4 <= mem[addr4];
        rdata5 <= mem[addr5];
        rdata6 <= mem[addr6];
    end

endmodule
