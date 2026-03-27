//`default_nettype none

module scoreboard (
    `ifdef USE_POWER_PINS
    inout VPWR,    // Common digital supply
    inout VGND,    // Common digital ground
    `endif
    input wire clk,                   // Clock signal
    input wire reset,                 // Reset signal
    input wire team1_inc,             // Team 1 increment button
    input wire team2_inc,             // Team 2 increment button
    input wire team1_dec,             // Team 1 increment button
    input wire team2_dec,             // Team 2 increment button
    output wire [6:0] seg_out,         // Seven-segment outputs (A-G, DP)
    output wire [3:0] seg_control      // Control for Team 1 digits (4 digits)
);

    reg [7:0] score_team1;           // Store Team 1 score (4 digits)
    reg [7:0] score_team2;           // Store Team 2 score (4 digits)
    reg [1:0] current_digit;          // Current digit for multiplexing (0-6)

    parameter DIV_10MHZ_TO_500HZ = 5000;     // Divide 10 MHz by 10,000 to get 1000 Hz. . give half value
    reg [14:0] counter_500Hz;    // 15-bit counter for 500 Hz     

    reg team1_inc_prev, team2_inc_prev;
    reg team1_dec_prev, team2_dec_prev;
    reg [7:0] team1_tens;
    reg [7:0] team1_ones;
    reg [7:0] team2_tens;
    reg [7:0] team2_ones;    
    
    reg [6:0] seg_out_reg;
    reg[3:0] seg_control_reg;

    assign seg_out = seg_out_reg;
    assign seg_control =seg_control_reg;


    
    // Second stage: Divide 10 MHz clock to 500 Hz
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            counter_500Hz <= 15'b0;           
            current_digit <= 2'b00;
            team1_inc_prev <= 1'b0;
            team2_inc_prev <= 1'b0;  
            team1_dec_prev <= 1'b0;
            team2_dec_prev <= 1'b0;        
            score_team1 <= 8'b0;
            score_team2 <= 8'b0;
            seg_out_reg <= 7'b1111111;   // Turn off all segments
            seg_control_reg <= 4'b1111;   // Turn off control signals
                      
        end else begin
        
            team1_inc_prev <= team1_inc;
            team2_inc_prev <= team2_inc;    
            team1_dec_prev <= team1_dec;
            team2_dec_prev <= team2_dec;      
        
	    if (team1_inc && !team1_inc_prev) begin
            	    // Increment the score of team 1 when inc1 button is pressed (on rising edge)
		    if (score_team1 + 8'd1 <= 8'd99)
		        score_team1 <= score_team1 + 8'd1;
		    else
		        score_team1 <= 8'd99; // Cap at 999
            end        
  
	   if (team2_inc && !team2_inc_prev) begin
		    // Increment the score of team 2 when inc2 button is pressed (on rising edge)
		    if (score_team2 + 8'd1 <= 8'd99)
		        score_team2 <= score_team2 + 8'd1;
		    else
		        score_team2 <= 8'd99; // Cap at 999
           end  
           
	    if (team1_dec && !team1_dec_prev && score_team1 > 0) begin
            	    // Increment the score of team 1 when inc1 button is pressed (on rising edge)
		    if (score_team1 - 8'd1 > 8'd0)
		        score_team1 <= score_team1 - 8'd1;
		    else
		        score_team1 <= 8'd0; // Cap at 0
            end  

	   if (team2_dec && !team2_dec_prev && score_team2 > 0) begin
		    // Increment the score of team 2 when inc2 button is pressed (on rising edge)
		    if (score_team2 - 8'd1 > 8'd0)
		        score_team2 <= score_team2 - 8'd1;
		    else
		        score_team2 <= 8'd0; // Cap at 0
           end 
  
 	   if (counter_500Hz == (DIV_10MHZ_TO_500HZ - 1)) begin		//Enabling the control pins of the 4 seven segment. Multiplex at a lower frequency based on a counter value
            	counter_500Hz <= 15'b0;
           
            	if (current_digit == 2'b11) begin
            		current_digit <= 2'b00;  // Wrap around to 000 after reaching 101
            	end else begin
            		current_digit <= current_digit + 2'b01;			
            	end                                   
          end else begin
               counter_500Hz <= counter_500Hz + 15'b1;
          end 
         
            
	  team1_tens<=score_team1 / 10;
	  team1_ones<=score_team1 % 10;
	  team2_tens<=score_team2 / 10;
	  team2_ones<=score_team2 % 10;

        case (current_digit)
                2'b00: begin
                    // Team 1 Digit 1
                    
			case(team1_ones)
			    8'd0: seg_out_reg <= 7'b0000001; // "0"	01
			    8'd1: seg_out_reg <= 7'b1001111; // "1"	4F
			    8'd2: seg_out_reg <= 7'b0010010; // "2"	12
			    8'd3: seg_out_reg <= 7'b0000110; // "3"
			    8'd4: seg_out_reg <= 7'b1001100; // "4"
			    8'd5: seg_out_reg <= 7'b0100100; // "5"
			    8'd6: seg_out_reg <= 7'b0100000; // "6"
			    8'd7: seg_out_reg <= 7'b0001111; // "7"
			    8'd8: seg_out_reg <= 7'b0000000; // "8"
			    8'd9: seg_out_reg <= 7'b0000100; // "9"
			    default: seg_out_reg <= 7'b1111111; // Blank
			endcase                    
                    
                    //seg_out_reg <= seven_seg_decoder(team1_ones);
                    seg_control_reg <= 4'b1110; // Activate digit 1 for Team 1
                   // team2_control <= 4'b1111;
                end
                2'b01: begin
                    // Team 1 Digit 2
			case(team1_tens)
			    8'd0: seg_out_reg <= 7'b0000001; // "0"	01
			    8'd1: seg_out_reg <= 7'b1001111; // "1"	4F
			    8'd2: seg_out_reg <= 7'b0010010; // "2"	12
			    8'd3: seg_out_reg <= 7'b0000110; // "3"
			    8'd4: seg_out_reg <= 7'b1001100; // "4"
			    8'd5: seg_out_reg <= 7'b0100100; // "5"
			    8'd6: seg_out_reg <= 7'b0100000; // "6"
			    8'd7: seg_out_reg <= 7'b0001111; // "7"
			    8'd8: seg_out_reg <= 7'b0000000; // "8"
			    8'd9: seg_out_reg <= 7'b0000100; // "9"
			    default: seg_out_reg <= 7'b1111111; // Blank
			endcase                     
                    
                   // seg_out_reg <= seven_seg_decoder(team1_tens);
                    seg_control_reg <= 4'b1101; // Activate digit 2 for Team 1
                    //team2_control <= 4'b1111;
                end
                2'b10: begin
                    // Team 1 Digit 3                    
			case(team2_ones)
			    8'd0: seg_out_reg <= 7'b0000001; // "0"	01
			    8'd1: seg_out_reg <= 7'b1001111; // "1"	4F
			    8'd2: seg_out_reg <= 7'b0010010; // "2"	12
			    8'd3: seg_out_reg <= 7'b0000110; // "3"
			    8'd4: seg_out_reg <= 7'b1001100; // "4"
			    8'd5: seg_out_reg <= 7'b0100100; // "5"
			    8'd6: seg_out_reg <= 7'b0100000; // "6"
			    8'd7: seg_out_reg <= 7'b0001111; // "7"
			    8'd8: seg_out_reg <= 7'b0000000; // "8"
			    8'd9: seg_out_reg <= 7'b0000100; // "9"
			    default: seg_out_reg <= 7'b1111111; // Blank
			endcase                                         
                    
                    //seg_out_reg <= seven_seg_decoder(team2_ones);
                    seg_control_reg <= 4'b1011; // Activate digit 3 for Team 1
                   // team2_control <= 4'b1111;
                end
                2'b11: begin
			case(team2_tens)
			    8'd0: seg_out_reg <= 7'b0000001; // "0"	01
			    8'd1: seg_out_reg <= 7'b1001111; // "1"	4F
			    8'd2: seg_out_reg <= 7'b0010010; // "2"	12
			    8'd3: seg_out_reg <= 7'b0000110; // "3"
			    8'd4: seg_out_reg <= 7'b1001100; // "4"
			    8'd5: seg_out_reg <= 7'b0100100; // "5"
			    8'd6: seg_out_reg <= 7'b0100000; // "6"
			    8'd7: seg_out_reg <= 7'b0001111; // "7"
			    8'd8: seg_out_reg <= 7'b0000000; // "8"
			    8'd9: seg_out_reg <= 7'b0000100; // "9"
			    default: seg_out_reg <= 7'b1111111; // Blank
			endcase


                    // Team 1 Digit 3
                   // seg_out_reg<= seven_seg_decoder(team2_tens);
                    seg_control_reg <= 4'b0111; // Activate digit 4 for Team 1
                   // team2_control <= 4'b1111;
                end 
                default: begin
                    seg_out_reg<= 7'b1111111;   // Turn off all segments
                    seg_control_reg <= 4'b1111;   // Turn off control signals
                end             
       endcase

        
      end
    end
endmodule       
       
              
    
