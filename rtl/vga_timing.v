// VGA Timing Generator for 640x480 @ 60Hz
// Pixel clock: 25.175 MHz (we use 25 MHz from 50 MHz / 2)
//
// Horizontal timing (in pixels):
//   Visible:     640
//   Front porch: 16
//   Sync pulse:  96
//   Back porch:  48
//   Total:       800
//
// Vertical timing (in lines):
//   Visible:     480
//   Front porch: 10
//   Sync pulse:  2
//   Back porch:  33
//   Total:       525

module vga_timing (
    input         clk,          // Pixel clock (25 MHz)
    input         reset,
    
    output reg    hsync,        // Horizontal sync (active low)
    output reg    vsync,        // Vertical sync (active low)
    output        hblank,       // Horizontal blanking
    output        vblank,       // Vertical blanking
    output        active,       // Active video region
    
    output [9:0]  pixel_x,      // Current pixel X (0-639 in active region)
    output [9:0]  pixel_y       // Current pixel Y (0-479 in active region)
);

    // Horizontal timing parameters
    localparam H_VISIBLE    = 640;
    localparam H_FRONT      = 16;
    localparam H_SYNC       = 96;
    localparam H_BACK       = 48;
    localparam H_TOTAL      = 800;
    
    // Vertical timing parameters
    localparam V_VISIBLE    = 480;
    localparam V_FRONT      = 10;
    localparam V_SYNC       = 2;
    localparam V_BACK       = 33;
    localparam V_TOTAL      = 525;
    
    // Counters
    reg [9:0] h_count;
    reg [9:0] v_count;
    
    // Horizontal counter
    always @(posedge clk) begin
        if (reset) begin
            h_count <= 0;
        end else if (h_count == H_TOTAL - 1) begin
            h_count <= 0;
        end else begin
            h_count <= h_count + 1'b1;
        end
    end
    
    // Vertical counter
    always @(posedge clk) begin
        if (reset) begin
            v_count <= 0;
        end else if (h_count == H_TOTAL - 1) begin
            if (v_count == V_TOTAL - 1) begin
                v_count <= 0;
            end else begin
                v_count <= v_count + 1'b1;
            end
        end
    end
    
    // Sync signals (active low)
    always @(posedge clk) begin
        if (reset) begin
            hsync <= 1'b1;
            vsync <= 1'b1;
        end else begin
            // HSYNC: active during h_count 656-751 (after visible + front porch)
            hsync <= ~((h_count >= H_VISIBLE + H_FRONT) && 
                       (h_count < H_VISIBLE + H_FRONT + H_SYNC));
            
            // VSYNC: active during v_count 490-491 (after visible + front porch)
            vsync <= ~((v_count >= V_VISIBLE + V_FRONT) && 
                       (v_count < V_VISIBLE + V_FRONT + V_SYNC));
        end
    end
    
    // Blanking signals
    assign hblank = (h_count >= H_VISIBLE);
    assign vblank = (v_count >= V_VISIBLE);
    
    // Active video region
    assign active = (h_count < H_VISIBLE) && (v_count < V_VISIBLE);
    
    // Pixel coordinates (valid during active region)
    assign pixel_x = h_count;
    assign pixel_y = v_count;

endmodule
