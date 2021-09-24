'''
Triphasic Pump Class File
Pump, CSV writer, and pump sensors
By Mark Joyce - 2021
Triphasic
'''
import pigpio
import time
import math
import threading

import board
import busio
i2c = busio.I2C(board.SCL, board.SDA)
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

from datetime import datetime
import logging


##############################################################################
######################################################################
######################################################################
# The Pump Class        
# Closed Loop Stepper Motor Controller Class
# Original by Sato forked by Mark.
# Sato's original code can crash at various settings. Therfore I have provided
# a fix in the up and the down run methods. Needs error testing against actual
# motor operation. Seems to work fine, your welcome. When the fix corrects an error
# it is written to the 'PumpErrorLog.log' file allowing for further investigation.

##############################################################################
class Pump:
    
    def __init__(self, direction_pin, return_sensor, motor_pin, enable_pin, length, pulse_per_revolution,
                 length_per_revolution, tube_diameter, remaining_degrees, gear_ratio):
        self.logging = logging
        self.logging.basicConfig(filename="PumpErrorLog.log",  level=logging.INFO)
        self.logging.getLogger('PIL').setLevel(logging.WARNING)
        #self.logging.debug("This message should go to the log file")
      # Set constructor variables
        self.pi = pigpio.pi()
        self.direction_pin = direction_pin
        self.return_sensor = return_sensor
        self.motor = motor_pin
        self.enable = enable_pin
        self.length = length
        self.pulse_per_revolution = pulse_per_revolution
        self.length_per_revolution = length_per_revolution #3 #in millimeter, was 20
        self.tube_diameter = float(tube_diameter)
        
        self.gear_ratio = gear_ratio
        
        self.return_wave_delay = 4
        
        self.volume_value = 1
        self.rate_value = 30
        self.systolic_percentage_value = 50
        self.peak_percentage_value = 50
        
        # Set GPIO's
        self.pi.set_mode(self.direction_pin, pigpio.OUTPUT)
        self.pi.set_pull_up_down(self.return_sensor, pigpio.PUD_DOWN)
        self.pi.set_mode(self.motor, pigpio.OUTPUT)
        # Motor Direction
        self.direction = 1
        
        # A circle / rotation has. 
        self.max_degrees = 360
        
        #REMAINING DEGREES - Change request by Albert. have left original code vars as remaining_steps
        self.remaining_steps = int(self.pulse_per_revolution / (self.max_degrees / remaining_degrees)) * self.gear_ratio
        #self.remaining_steps = int(self.pulse_per_revolution * remaining_degrees) #13.5 / 2.25
        self.main_divide = 100
        self.length = 20 # was 20
        
        self.running = True
        
        self.condition_change = 0
        self.return_wave_chain = 0
        self.initial_wave_chain = []
        self.initial_wave_chain_1 = []
        self.initial_wave_chain_2 = []
        self.initialise_step = 0
        
        self.up_times = 0
        self.up_run = []
        self.up_step_total = 0
        
        self.down_times = 0
        self.down_run = []
        
        self.step_count = 0
        self.up_divide = 0
        self.new_up_divide = 0
        self.down_divide = 0
        self.new_down_divide = 0
        self.scale_value = 0
        self.pulse_time = 0
        
        #status_bar
        self.step_count_complete = False
        self.stop_start_call = False
        ##running
        self.move_initial_start = False
        self.move_initial_end = False
        self.move_initial_funct_done = False
        self.bck_home_possition = False
        self.start_stop_function_end = False
        
        self.i_made_new_data = False
        
        self.up_frequency_copy = []
        self.down_frequency_copy = []
    
    def __del__(self):
        print("Pump instance died :(")
        
    def enable_stepper(self):
        self.pi.write(self.enable, 0)
        
    def disable_stepper(self):
        self.pi.write(self.enable, 1)
        
    def set_inputs(self,volume_value, systolic_percentage_value, rate_value, peak_percentage_value):
        
        self.volume_value = volume_value
        self.systolic_percentage_value = systolic_percentage_value
        self.rate_value = rate_value
        self.peak_percentage_value = peak_percentage_value
         
    #define functions
    def return_wave_setting(self):
        
        self.pi.wave_clear()
        return_frequency = int(self.pulse_per_revolution)
        return_micros = int(500000 / (return_frequency / self.return_wave_delay))
        return_wave = []
        #                                        ON     OFF  DELAY us
        return_wave.append(pigpio.pulse(1 << self.motor, 0, return_micros))
        return_wave.append(pigpio.pulse(0, 1 << self.motor, return_micros))
        self.pi.wave_add_generic(return_wave)
        return_wave_chain = self.pi.wave_create()

    def initial_wave_setting(self):

        if self.remaining_steps <= 65535: #65535 = 255 * 256
            print('Init Wave set if')
            print('remaining steps = ', self.remaining_steps)
            x_1_1 = self.remaining_steps & 255
            y_1_1 = self.remaining_steps >> 8
            self.initial_wave_chain = [255, 0, self.return_wave_chain, 255, 1, x_1_1, y_1_1]
        
        else:
            print('Init Wave set else')
            self.initialise_step = int(self.remaining_steps / 65535)
            x_1_1 = 65535 & 255
            y_1_1 = 65535 >> 8
            self.initial_wave_chain_1 = [255, 0, self.return_wave_chain, 255, 1, x_1_1, y_1_1]
            x_1_2 = (int(self.remaining_steps % 65535)) & 255
            y_1_2 = (int(self.remaining_steps % 65535)) >> 8
            self.initial_wave_chain_2 = [255, 0, self.return_wave_chain, 255, 1, x_1_2, y_1_2]

    def change_detect(self,  event):
        
        self.condition_change = 1
        

    def up_curve_setting(self):
        
        up_sine_sum = 0
        up_step_count = 0
        self.up_step_total = 0
        up_frequency = []
        up_pulse = []
        self.up_run = []
        peak_percentage_value = self.peak_percentage_value
        systolic_percentage_value = self.up_divide / 2
        
        for b in range(self.new_up_divide):
            up_sine_sum = up_sine_sum + math.sin(0.5 * math.pi * ((b + 1) / (systolic_percentage_value / 2)))
        
        up_pulse_scale = (self.step_count / round(up_sine_sum, 1)) * 100
        up_hill_value = int((systolic_percentage_value * peak_percentage_value) / 100)
        down_hill_value = int(systolic_percentage_value - up_hill_value)
        
        for c in range(self.new_up_divide):
            if c < up_hill_value:
                single_up_frequency = int(round(up_pulse_scale * math.sin(0.5 * math.pi * ((c + 1) / up_hill_value)), -2))
            
            else:
                single_up_frequency = int(round(up_pulse_scale * math.sin((((c + 1) + (systolic_percentage_value - (2 * up_hill_value))) / down_hill_value) * 0.5 * math.pi), -2))
            
            if single_up_frequency == 0:
                single_up_frequency = 100
            
            #up_frequency = up_frequency + [single_up_frequency]
            up_frequency.append(single_up_frequency)
            up_pulse = up_pulse + [int(single_up_frequency / 100)]
            up_step_count = up_step_count + int(single_up_frequency / 100)

        up_remainder = self.step_count - up_step_count
        print("UF len = ",len(up_frequency))
        print("upremainder = ", up_remainder)
        
        if up_remainder < 0:
            up_index = [z for z in range(len(up_pulse)) if up_pulse[z] > 1]
            print("up I len =", len(up_index))
            if abs(up_remainder) > len(up_index):
                up_remainder = len(up_index)
            for y in range(abs(up_remainder)):
                up_frequency[up_index[y]] = up_frequency[up_index[y]] - 100
                up_pulse[up_index[y]] = up_pulse[up_index[y]] - 1
        
        else:
            #                          <--------------------------------------<<< GETAFIX ****
            if len(up_frequency) < up_remainder:
                self.logging.info(">>>--------> Getafix <--------<<<")
                self.logging.info(datetime.now().strftime('%H:%M:%S:%f|%d/%m/%Y'))
                self.logging.info("Tube Diameter = " +  str(self.tube_diameter))
                self.logging.info("Length Per Revolution = " +  str(self.length_per_revolution))
                self.logging.info("Stroke Volume % = " +  str(self.volume_value))
                self.logging.info("Rate Value = " + str(self.rate_value))
                self.logging.info("Systolic % Value = " + str(self.systolic_percentage_value) + "%")
                self.logging.info("Peak % Value = "+ str(self.peak_percentage_value) + "%")
                self.logging.info("If length of Up Frequency List < Up Remainder: TRUE")
                self.logging.info("Then: Make up remainder equal to the length of the Up Frequency List")
                self.logging.info(">>>--------> Getafix <--------<<<")
                up_remainder = len(up_frequency)               
            #                          <--------------------------------------<<< GETAFIX END*
            for xy in range(abs(up_remainder)):
                up_frequency[xy] = up_frequency[xy] + 100
                up_pulse[xy] = up_pulse[xy] + 1
                
        for n in range(self.new_up_divide):
            up_frequency[n] = int(round(up_frequency[n] * self.scale_value, -2))
            if(up_frequency[n] == 0):
                up_frequency[n] = 10
        
        self.up_times = int(self.new_up_divide / self.length)
        up_extra = int(self.new_up_divide % self.length)
        if up_extra != 0:
            self.up_times = self.up_times + 1
        
        for e in range(self.up_times):
            up_chain = []
            up_length = self.length
            if up_extra != 0 and e == self.up_times - 1:
                up_length = up_extra
            #print(up_frequency)
            for f in range(up_length):
                up_pulse_time = int(500000 / up_frequency[e * self.length + f])
                up_wave_form = []
                up_wave = []
                up_wave_form.append(pigpio.pulse(1 << self.motor, 0, up_pulse_time)) #pulse on
                up_wave_form.append(pigpio.pulse(0, 1 << self.motor, up_pulse_time)) #pulse off
                self.pi.wave_add_generic(up_wave_form)
                up_wave = self.pi.wave_create()
                up_step = up_pulse[e * self.length + f]
                x_2 = up_step & 255
                y_2 = up_step >> 8
                up_chain = up_chain + [255, 0, up_wave, 255, 1, x_2, y_2]
                self.up_step_total = self.up_step_total + up_step
            
            self.up_run = self.up_run + [up_chain]
            
        self.up_frequency_copy = up_frequency.copy()

    def down_curve_setting(self):
        
        down_sine_sum = 0
        down_step_count = 0
        down_step_total = 0
        down_frequency = []
        down_pulse = []
        self.down_run = []
        for h in range(self.new_down_divide):
            down_sine_sum = down_sine_sum + math.sin(2 * math.pi * ((h + 1) / self.down_divide))
        
        down_pulse_scale = (self.up_step_total / (math.ceil(down_sine_sum * 1000) / 1000)) * 100
        
        for i in range(self.new_down_divide):
            single_down_frequency = int(round(down_pulse_scale * math.sin(2 * math.pi * ((i + 1) / self.down_divide)), -2))
            if single_down_frequency == 0:
                single_down_frequency = 100
            
            down_frequency = down_frequency + [single_down_frequency]
            down_pulse = down_pulse + [int(round(single_down_frequency / 100))]
            down_step_count = down_step_count + int(round(single_down_frequency / 100))
            
        down_remainder = self.up_step_total - down_step_count
        
        print("diwn Remainder = ", down_remainder)
        print("down frequency = ", len(down_frequency))
        
        if down_remainder < 0:
            down_index = [w for w in range(len(down_pulse)) if down_pulse[w] > 1]
            #print("down Index", down_index)
            print("down I =", len(down_index))
            if abs(down_remainder) > len(down_index):
                down_remainder = len(down_index)
                
                
            for v in range(abs(down_remainder)):
                down_frequency[down_index[v]] = down_frequency[down_index[v]] - 100
                down_pulse[down_index[v]] = down_pulse[down_index[v]] - 1

        else:
            for u in range(abs(down_remainder)):
                down_frequency[u] = down_frequency[u] + 100
                down_pulse[u] = down_pulse[u] + 1
        
        for o in range(self.new_down_divide):
            down_frequency[o] = int(round(down_frequency[o] * self.scale_value, -2))
            if(len(down_frequency) < down_remainder): #<-----------------------------------------------------ADDED NEW!
                down_frequency[o] = 10
                self.logging.info("*****************************************************************")
                self.logging.info("                         Down Freq Div by zero Fix               ")
                self.logging.info(datetime.now().strftime('%H:%M:%S:%f|%d/%m/%Y'))
                self.logging.info("Tube Diameter = " +  str(self.tube_diameter))
                self.logging.info("Length Per Revolution = " +  str(self.length_per_revolution))
                self.logging.info("Stroke Volume % = " +  str(self.volume_value))
                self.logging.info("Rate Value = " + str(self.rate_value))
                self.logging.info("Systolic % Value = " + str(self.systolic_percentage_value) + "%")
                self.logging.info("Peak % Value = "+ str(self.peak_percentage_value) + "%")
                self.logging.info("*****************************************************************")
            down_remainder = len(down_frequency)
        
        self.down_times = int(self.new_down_divide / self.length)
        down_extra = int(self.new_down_divide % self.length)
        if down_extra != 0:
            self.down_times = self.down_times + 1
        
        for k in range(self.down_times):
            down_chain = []
            down_length = self.length
            if down_extra != 0 and k == self.down_times - 1:
                down_length = down_extra
            #print(down_frequency)
            for l in range(down_length):
                down_pulse_time = int(500000 / down_frequency[k * self.length + l])
                down_wave_form = []
                down_wave = []
                down_wave_form.append(pigpio.pulse(1 << self.motor, 0, down_pulse_time)) #pulse on
                down_wave_form.append(pigpio.pulse(0, 1 << self.motor, down_pulse_time)) #pulse off
                self.pi.wave_add_generic(down_wave_form)
                down_wave = self.pi.wave_create()
                down_step = down_pulse[k * self.length + l]
                x_3 = down_step & 255
                y_3 = down_step >> 8
                down_chain = down_chain + [255, 0, down_wave, 255, 1, x_3, y_3]
                down_step_total = down_step_total + down_step
            
            self.down_run = self.down_run + [down_chain]
            self.down_frequency_copy = down_frequency.copy()

    def step_count_setting(self):

        volume_value = self.volume_value
        rate_value = self.rate_value
        systolic_percentage_value = self.systolic_percentage_value
        self.up_divide = int(systolic_percentage_value * 2)
        self.new_up_divide = int(systolic_percentage_value - 1)
        self.down_divide = int((self.main_divide - systolic_percentage_value) * 2)
        self.new_down_divide = int(self.main_divide - systolic_percentage_value - 1)
        self.scale_value = rate_value / 60
        self.pulse_time = round(0.01 / self.scale_value, -5)
        #self.step_count = int(round((math.sqrt(volume_value) * self.pulse_per_revolution * self.tube_diameter) / (10 * self.length_per_revolution), 0) / 1.780)
        #magicNumber = 1125 # gives me 3% of 360 degrees (1540 steps of 51200) 
        self.step_count = int(round((math.sqrt(volume_value) * self.pulse_per_revolution * self.tube_diameter) / (self.length_per_revolution), 1) / 1.78) * self.gear_ratio
  
        #print(step_count)
        self.up_curve_setting()
        self.down_curve_setting()
        #status_bar['text'] = 'The pump is running at ' + str(slider3.get()) + ' percent of systolic, ' + str(slider2.get()) + ' beat per minute, and ' + str(slider1.get()) + ' percent occlusion'
        self.step_count_complete = True
        
    #Event functions
    def start(self):
        self.i_made_new_data = False
        while self.running:
            self.pi.write(self.direction_pin, 0)
            for a in range(self.up_times):
                self.pi.wave_chain(self.up_run[a])
                while self.pi.wave_tx_busy():
                    pass
            
            time.sleep(self.pulse_time)
            self.pi.write(self.direction_pin, 1)
            for g in range(self.down_times):
                self.pi.wave_chain(self.down_run[g])
                while self.pi.wave_tx_busy():
                    pass
            
            if self.condition_change == 1:
                self.condition_change = 0
                for m in range(self.new_up_divide + self.new_down_divide):
                    self.pi.wave_delete(m + 1)
                
                self.step_count_setting()
                self.i_made_new_data = True
            time.sleep(self.pulse_time)

    def start_stop_function(self):
        #status_bar['text'] = 'The pump is running at ' + str(slider3.get()) + ' percent of systolic, ' + str(slider2.get()) + ' beat per minute, and ' + str(slider1.get()) + ' percent occlusion'
        self.stop_start_call = True
        if self.running == False:
            self.running = True
            if self.condition_change == 1:
                self.condition_change = 0
                for m in range(self.new_up_divide + self.new_down_divide):
                    self.pi.wave_delete(m + 1)
                
                self.step_count_setting()
            
            self.start_stop_function_end_disabled = True
            #customise_button['state'] = 'disabled'
            #return_initial['state'] = 'disabled'
           # exit_button['state'] = 'disabled'
            threading.Thread(name = 'Pump_start_thread', target = self.start).start()
        
        else:
            self.running = False
            self.start_stop_function_end_enabled = True
            #status_bar['text'] = 'The movement has been stopped'
            #customise_button['state'] = 'normal'
            #return_initial['state'] = 'normal'
           # exit_button['state'] = 'normal'

    def function_c(self):
        customise_button['bg'] = color2
        status_bar['text'] = 'Select a text file profile'
        global filename
        filename = filedialog.askopenfilename()

    def return_initial_start(self):
        
        self.pi.write(self.direction_pin, self.direction)
        if self.direction == 1:
            
            #status_bar['text'] = 'Back to home position'
            #print(return_wave_chain)
            if self.pi.read(self.return_sensor) == 0:
                self.pi.wave_send_repeat(self.return_wave_chain)
                while self.pi.read(self.return_sensor) == 0:
                    pass
                
                self.pi.wave_tx_stop()
            
        
        else:
            self.move_initial_start = True
            #status_bar['text'] = 'Move to Initial position'
            if self.initialise_step == 0:
                print("im in IF ret ini start")
                self.pi.wave_chain(self.initial_wave_chain)
                while self.pi.wave_tx_busy():
                    pass
                self.move_initial_end = True
            
            else:
                print("Im in Else ret init start")
                self.move_initial_start = True
                for run_time in range(self.initialise_step):
                    self.pi.wave_chain(self.initial_wave_chain_1)
                    while self.pi.wave_tx_busy():
                        pass
                
                self.pi.wave_chain(self.initial_wave_chain_2)
                while self.pi.wave_tx_busy():
                    pass
                self.move_initial_end = True
            
            #start_stop['state'] = 'normal'
        self.move_initial_funct_done = True
        #return_initial['state'] = 'normal'
        self.direction = (self.direction + 1) % 2

    def return_initial_function(self):
        #start_stop['state'] = 'disabled'
        #return_initial['state'] = 'disabled'
        threading.Thread(name= 'Pump_return_init_start', target = self.return_initial_start).start()

    def exit_function(self):
        win.destroy()
        pi.wave_tx_stop()
        pi.wave_clear()
        pi.stop()
               
##############################################################################
##########################################################################
######################################################################
        
# CSV Writer Class
# Writes pump data to CSV file
# TODO -> Folder path variable

##############################################################################
import csv

class CsvWriter:
     
    # Create file with header
    def create_csv_file_and_header(self, fileName):
        with open(fileName, mode='w') as data_file:

            data_writer = csv.writer(data_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            #fieldnames = ['emp_name', 'dept', 'birth_month']
            fieldnames = ['Tube Diameter', 'Length Per Rev', 'Stroke Volume', 'Heart Rate', 'Systolic Percentage', 'Peak Percentage', 'Index', 'PSI', 'Flow', 'Throttle Valve Setting']
            data_writer.writerow(fieldnames)
    
    # Write data to file    
    def add_data_to_csv(self, fileName, Tube_Diameter, Length_Per_Rev, Stroke_Volume, Heart_Rate, Systolic_Percentage, Peak_Percentage, Index, PSI, Flow, Throttle_Valve_Setting):
        with open(fileName, mode='a') as data_file:
            data_writer = csv.writer(data_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            data_writer.writerow([Tube_Diameter, Length_Per_Rev, Stroke_Volume, Heart_Rate, Systolic_Percentage, Peak_Percentage, Index, PSI, Flow, Throttle_Valve_Setting])
 
 
##############################################################################
#########################################################################
######################################################################
        
# Pump Sensor Class
# Pressure Sensor - 5 PSI max - If changed to say 10 PSI change the Max PSI value to 10
# Flow Sensor - Analog 0-5v
# TODO -> Throttle Valve <-- Done!

##############################################################################

class PumpSensor:
    def __init__(self, PSI_MAX):
        self.ads = ADS.ADS1115(i2c)
        self.psi_channel = AnalogIn(self.ads, ADS.P0)
        self.flow_channel = AnalogIn(self.ads, ADS.P1)
        self.psi_xs = []
        self.psi_ys = []
        self.flow_xs = []
        self.flow_ys = []
        # Pressure sensor variables - Magic Numbers
        self.voltage_low_limit = 0.5 # Lowest valid voltage value @ 0 PSI
        self.voltage_high_limit = 4.5 # Highest valid voltage value @ 5 PSI
        self.pressure_range = PSI_MAX # Max PSI reading range. <---<< MAX PSI
        self.voltage_reading = 0.0
        self.pressure = 0.0
        
    def get_sensor_values(self):
        
        # Sample pressure
        self.psi_xs.clear() # Clear Arrays
        self.psi_ys.clear()
        self.flow_xs.clear()
        self.flow_ys.clear()
        for t in range(0, 200):
            
            # Read pressure form sensor
            self.voltage_reading = self.psi_channel.voltage
            self.pressure = self.pressure_range * (self.voltage_reading - self.voltage_low_limit) / (self.voltage_high_limit - self.voltage_low_limit)
            if(self.pressure < 0): # Remove negative noise valuse at rest. Dependent on outside air pressure, ie can be positive.
                self.pressure = 0.0
            # Add x and y pressure values to lists
            self.psi_xs.append(t)#(dt.datetime.now().strftime('%H:%M:%S.%f'))
            self.psi_ys.append(self.pressure)
            
            #Read flow from sensor <- CHANGE THE FORMULA
            self.voltage_reading = self.flow_channel.voltage
            self.flow = self.voltage_reading #self.pressure_range * (self.voltage_reading - self.voltage_low_limit) / (self.voltage_high_limit - self.voltage_low_limit)
            if(self.flow < 0):
                self.flow = 0.0
            # Append Flow Values to x and y lists
            self.flow_xs.append(t)#(dt.datetime.now().strftime('%H:%M:%S.%f'))
            self.flow_ys.append(self.flow)
            
            # Wait n (sub)seconds before sampling again
            time.sleep(0.01)
            
        return self.psi_xs, self.psi_ys, self.flow_xs, self.flow_ys
       
##############################################################################
#########################################################################
######################################################################
        
# Occluder Class
# Servo Control
# Set GPIO 
# Set Minimum and Maximum pulse width of servo (In its datasheet)
# Set by angle or duty

##############################################################################  
class Occluder:
    '''Constructor'''
    def __init__(self, servo_gpio, min_pulse_width, max_pulse_width):
        self.MIN_WIDTH = min_pulse_width
        self.MAX_WIDTH = max_pulse_width
        self.servo_gpio = servo_gpio
        self.SERVO_PERIOD = 20000 # Micro seconds (@50Hz)
        self.pi = pigpio.pi()
        self.pi.set_mode(self.servo_gpio, pigpio.OUTPUT)
        self.pi.set_PWM_frequency(self.servo_gpio, 50) # 50hz or 20ms or 20000us
    
    '''Destructor'''
    def __del__(self):
        self.pi.set_PWM_frequency(self.servo_gpio, 0)
        self.pi.stop()
        print("Occluder Destroyed")
        
    '''Class FUNCTIONS'''
    # Return pulse width from percent
    # Accepts values of 3% to 11.5% @ min PW of 600 and Max PW of 2300
    # (Standard for max width = 2000 and min = 1000 would be 5 to 10%)
    def get_width_from_percent(self, percent):
        pulse_width = (percent * self.SERVO_PERIOD) / 100
        return pulse_width
    
    # Return pulse width from angle
    # Accepts 0 to 180 (degrees)
    def get_width_from_angle(self, angle):
        pulse_width = self.MIN_WIDTH + (angle *((self.MAX_WIDTH - self.MIN_WIDTH) / 180))
        return pulse_width
    
    '''USER FUNCTIONS'''
    # Set servo to angle between 0 and 180 degrees
    def set_angle(self, angle):
        pulse_width = self.get_width_from_angle(angle)
        self.pi.set_servo_pulsewidth(self.servo_gpio, pulse_width) #set servo angle
    
    # Set servo duty, between 3% and 11.5% (0 and 180 degrees) for max of 2300 and min 600 pulse width values.
    # Standard of 1000 - 2000 min and max width would be 5% to 10%
    # Incorrect values will most likely damage motor
    def set_duty(self, duty):
        pulse_width = self.get_width_from_percent(duty)
        self.pi.set_servo_pulsewidth(self.servo_gpio, pulse_width) #set servo duty
   
## End Occluder Class ##  
#######################################################################

