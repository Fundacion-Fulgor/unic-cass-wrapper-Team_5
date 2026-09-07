//=============================================================================
// Updated: 2026-09-01
// SPI slave, mode 0 (CPOL=0, CPHA=0). Receives 16-bit frames laid out as
// [RW | ADDR(7) | DATA(8)] on the rising edge of i_sclk and shifts the read
// data back out on the falling edge.
//
// The receive shift register and the bit counter are cleared asynchronously
// while the slave is deselected, so every frame starts on a known boundary
// even if the master aborts one part way through.
//
// Two deliberate deviations from the house rules, both forced by the SPI
// protocol: the resets are asynchronous, because i_sclk does not run while
// the interface is idle and a synchronous reset would never take effect; and
// the transmit path is clocked on the falling edge, because in mode 0 the
// slave must present MISO half a bit before the master samples it.
//=============================================================================

module spi_slave_mode0 #(
    parameter FRAME_BITS   = 16,
    parameter ADDR_BITS    =  7,
    parameter DATA_BITS    =  8,
    parameter RW_BIT       = 15,
    parameter ADDR_MSB     = 14,
    parameter ADDR_LSB     =  8,
    parameter DATA_MSB     =  7,
    parameter DATA_LSB     =  0,
    parameter HDR_LAST_BIT =  7
) (
    `ifdef USE_POWER_PINS
    inout                        VPWR,
    inout                        VGND,
    `endif
    output wire                  o_miso,
    output reg  [ADDR_BITS-1:0]  o_addr,
    output reg  [DATA_BITS-1:0]  o_data,
    output reg                   o_write_enable,
    output reg                   o_rw_bit,
    output reg                   o_done,
    output reg  [FRAME_BITS-1:0] o_rx_frame,
    input                        i_rstn,
    input                        i_ss_n,
    input                        i_sclk,
    input                        i_mosi,
    input       [DATA_BITS-1:0]  i_data
);

localparam CNT_W    = $clog2(FRAME_BITS);
localparam TXC_W    = $clog2(DATA_BITS);
localparam LAST_BIT = FRAME_BITS - 1;

reg  [FRAME_BITS-1:0] rx_shift;
reg  [FRAME_BITS-1:0] tx_shift;
reg  [CNT_W-1:0]      bit_cnt;
reg  [ADDR_BITS-1:0]  addr_latched;
reg                   rd_toggle;
reg  [TXC_W-1:0]      tx_cnt;
reg                   tx_active;
reg                   rd_toggle_d;

wire [FRAME_BITS-1:0] next_rx;
wire                  rx_clr_n;

assign next_rx  = {rx_shift[FRAME_BITS-2:0], i_mosi};
assign rx_clr_n = i_rstn & ~i_ss_n;
assign o_miso   = (!i_ss_n) ? tx_shift[FRAME_BITS-1] : 1'b0;

always @(posedge i_sclk or negedge rx_clr_n) begin
    if (!rx_clr_n) begin
        rx_shift <= {FRAME_BITS{1'b0}};
        bit_cnt  <= {CNT_W{1'b0}};
    end
    else begin
        rx_shift <= next_rx;
        if (bit_cnt == LAST_BIT[CNT_W-1:0]) begin
            bit_cnt <= {CNT_W{1'b0}};
        end
        else begin
            bit_cnt <= bit_cnt + 1'b1;
        end
    end
end

always @(posedge i_sclk or negedge i_rstn) begin
    if (!i_rstn) begin
        o_rw_bit       <= 1'b1;
        addr_latched   <= {ADDR_BITS{1'b0}};
        rd_toggle      <= 1'b0;
        o_addr         <= {ADDR_BITS{1'b0}};
        o_data         <= {DATA_BITS{1'b0}};
        o_write_enable <= 1'b0;
        o_done         <= 1'b0;
        o_rx_frame     <= {FRAME_BITS{1'b0}};
    end
    else begin
        o_write_enable <= 1'b0;
        o_done         <= 1'b0;

        if (!i_ss_n) begin
            if (bit_cnt == HDR_LAST_BIT[CNT_W-1:0]) begin
                o_rw_bit     <= next_rx[HDR_LAST_BIT];
                addr_latched <= next_rx[HDR_LAST_BIT-1:0];
                o_addr       <= next_rx[HDR_LAST_BIT-1:0];
                if (next_rx[HDR_LAST_BIT] == 1'b1) begin
                    rd_toggle <= ~rd_toggle;
                end
            end

            if (bit_cnt == LAST_BIT[CNT_W-1:0]) begin
                o_rx_frame <= next_rx;
                o_addr     <= next_rx[ADDR_MSB:ADDR_LSB];
                o_data     <= next_rx[DATA_MSB:DATA_LSB];
                if (next_rx[RW_BIT] == 1'b0) begin
                    o_write_enable <= 1'b1;
                end
                o_done <= 1'b1;
            end
        end
    end
end

always @(negedge i_sclk or negedge i_rstn) begin
    if (!i_rstn) begin
        tx_shift    <= {FRAME_BITS{1'b0}};
        tx_cnt      <= {TXC_W{1'b0}};
        tx_active   <= 1'b0;
        rd_toggle_d <= 1'b0;
    end
    else begin
        if (i_ss_n) begin
            tx_shift    <= {FRAME_BITS{1'b0}};
            tx_cnt      <= {TXC_W{1'b0}};
            tx_active   <= 1'b0;
            rd_toggle_d <= rd_toggle;
        end
        else begin
            if (rd_toggle_d != rd_toggle) begin
                rd_toggle_d <= rd_toggle;
                tx_shift    <= {i_data, {(FRAME_BITS-DATA_BITS){1'b0}}};
                tx_active   <= 1'b1;
                tx_cnt      <= {TXC_W{1'b0}};
            end
            else if (tx_active) begin
                if (tx_cnt < (DATA_BITS-1)) begin
                    tx_shift <= {tx_shift[FRAME_BITS-2:0], 1'b0};
                    tx_cnt   <= tx_cnt + 1'b1;
                end
                else begin
                    tx_active <= 1'b0;
                end
            end
        end
    end
end

endmodule
