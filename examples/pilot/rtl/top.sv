module top(
  input  logic clk,
  input  logic rst_n,
  input  logic req,
  output logic ack,
  input  logic fifo_push,
  input  logic fifo_pop,
  output logic fifo_full,
  output logic fifo_empty,
  output logic valid
);

  logic [31:0] status_q;
  logic [31:0] ctrl_q;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      status_q <= 32'h0;
      ctrl_q <= 32'h0;
      ack <= 1'b0;
      valid <= 1'b0;
    end else begin
      ack <= req;
      valid <= !fifo_empty;
    end
  end

  assign fifo_full = 1'b0;
  assign fifo_empty = 1'b1;
endmodule
