// CHR-ROM BRAM for NES - Registered read for M9K inference
// 8KB addressable via PPU address $0000-$1FFF

module nes_chr_bram #(
    parameter INIT_FILE = ""
)(
    input         clk,
    input  [12:0] addr,
    input   [7:0] wdata,
    input         we,
    output reg [7:0] rdata
);

    (* ram_init_file = INIT_FILE *)
    (* ramstyle = "M9K" *)
    reg [7:0] mem [0:8191];
    
    initial begin
        if (INIT_FILE != "") begin
            $readmemh(INIT_FILE, mem);
        end
    end
    
    always @(posedge clk) begin
        if (we)
            mem[addr] <= wdata;
        rdata <= mem[addr];
    end

endmodule
