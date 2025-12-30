// NES APU Stub (Frame Counter Only)
// No audio synthesis - only implements frame counter IRQ
// Supports both 4-step and 5-step modes with cycle-accurate timing

module nes_apu_stub (
    input  wire        clk,
    input  wire        rst,
    input  wire        cpu_clk_en,
    
    input  wire        apu_cs,
    input  wire [4:0]  apu_addr,
    input  wire        apu_wr,
    input  wire [7:0]  apu_wr_data,
    output wire [7:0]  apu_rd_data,
    
    output reg         frame_irq_n
);

    // $4015 reads return 0 (no sound channels), but preserve frame IRQ status
    assign apu_rd_data = (apu_addr == 5'h15) ? {1'b0, ~frame_irq_n, 6'b000000} : 8'h00;
    
    // Frame counter state
    reg [14:0] cycle_count;
    reg [2:0]  step;
    reg        mode_5step;
    reg        irq_inhibit;
    
    // Step timing thresholds (in CPU cycles from frame start)
    // NES uses 7456.5 cycles per step, approximated as 7457
    localparam [14:0] STEP0_CYC = 15'd7457;
    localparam [14:0] STEP1_CYC = 15'd14913;
    localparam [14:0] STEP2_CYC = 15'd22371;
    localparam [14:0] STEP3_CYC = 15'd29828;  // 4-step IRQ point
    localparam [14:0] STEP4_CYC = 15'd37281;  // 5-step only
    
    always @(posedge clk) begin
        if (rst) begin
            cycle_count <= 15'd0;
            step <= 3'd0;
            mode_5step <= 1'b0;
            irq_inhibit <= 1'b0;
            frame_irq_n <= 1'b1;
        end else if (cpu_clk_en) begin
            // $4017 write handling
            if (apu_cs && apu_wr && apu_addr == 5'h17) begin
                mode_5step <= apu_wr_data[7];
                irq_inhibit <= apu_wr_data[6];
                if (apu_wr_data[6]) 
                    frame_irq_n <= 1'b1;
                cycle_count <= 15'd0;
                step <= 3'd0;
            end
            // $4015 read clears frame IRQ
            else if (apu_cs && ~apu_wr && apu_addr == 5'h15) begin
                frame_irq_n <= 1'b1;
            end
            else begin
                cycle_count <= cycle_count + 15'd1;
                
                // Step advancement
                case (step)
                    3'd0: if (cycle_count >= STEP0_CYC) step <= 3'd1;
                    3'd1: if (cycle_count >= STEP1_CYC) step <= 3'd2;
                    3'd2: if (cycle_count >= STEP2_CYC) step <= 3'd3;
                    3'd3: begin
                        if (cycle_count >= STEP3_CYC) begin
                            if (~mode_5step) begin
                                // 4-step mode: IRQ and reset
                                if (~irq_inhibit) 
                                    frame_irq_n <= 1'b0;
                                cycle_count <= 15'd0;
                                step <= 3'd0;
                            end else begin
                                step <= 3'd4;
                            end
                        end
                    end
                    3'd4: begin
                        if (cycle_count >= STEP4_CYC) begin
                            // 5-step mode: no IRQ, just reset
                            cycle_count <= 15'd0;
                            step <= 3'd0;
                        end
                    end
                    default: begin
                        step <= 3'd0;
                    end
                endcase
            end
        end
    end

endmodule
