// NES Controller Interface
// Implements shift register for reading button states
// Connected to host CSR for button state input

module nes_controller (
    input  wire        clk,
    input  wire        rst,
    input  wire        cpu_clk_en,
    
    // CPU interface
    input  wire        ctrl_cs,
    input  wire        ctrl_wr,
    input  wire        ctrl_rd,
    input  wire        addr_bit,     // 0=$4016, 1=$4017
    input  wire [7:0]  cpu_data_in,
    output wire [7:0]  ctrl_data,
    
    // External button inputs (from host CSR)
    input  wire [7:0]  buttons_p1,   // A,B,Sel,Start,U,D,L,R
    input  wire [7:0]  buttons_p2
);

    // Shift registers
    reg [7:0] shift_p1;
    reg [7:0] shift_p2;
    reg       strobe;
    
    // Output current bit (bit 0 of shift register)
    wire p1_bit = strobe ? buttons_p1[0] : shift_p1[0];
    wire p2_bit = strobe ? buttons_p2[0] : shift_p2[0];
    
    // Data output (bits 1-7 are open bus, return 0 for simplicity)
    assign ctrl_data = addr_bit ? {7'b0, p2_bit} : {7'b0, p1_bit};
    
    always @(posedge clk) begin
        if (rst) begin
            shift_p1 <= 8'hFF;
            shift_p2 <= 8'hFF;
            strobe <= 1'b0;
        end else if (cpu_clk_en) begin
            // Write to $4016 controls strobe
            if (ctrl_cs && ctrl_wr && ~addr_bit) begin
                strobe <= cpu_data_in[0];
                
                // On strobe transition 1->0, load shift registers
                if (strobe && ~cpu_data_in[0]) begin
                    shift_p1 <= buttons_p1;
                    shift_p2 <= buttons_p2;
                end
            end
            
            // Read shifts the register (if not strobing)
            if (ctrl_cs && ctrl_rd && ~strobe) begin
                if (~addr_bit)
                    shift_p1 <= {1'b1, shift_p1[7:1]};  // Shift right, fill with 1
                else
                    shift_p2 <= {1'b1, shift_p2[7:1]};
            end
        end
    end

endmodule
