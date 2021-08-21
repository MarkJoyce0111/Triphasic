from tkinter import filedialog
import tkinter as tk                # python 3
from tkinter import font as tkfont  # python 3
from tkinter import ttk
import threading
import multiprocessing

import time
import copy

import os
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import ImageTk,Image

import board
import busio
i2c = busio.I2C(board.SCL, board.SDA)
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

from TriphasicPump import Pump
from TriphasicPump import CsvWriter
from TriphasicPump import PumpSensor
from TriphasicPump import Occluder

from datetime import datetime

os.system('sudo pigpiod') # Start GPIO Lib/Class

      
class TriphasicApp(tk.Tk, Pump):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        #self.geometry('800x480')
        self.attributes('-fullscreen', True)

        self.title_font = tkfont.Font(family='Helvetica', size=12, weight="bold", slant="italic")
        self.status_bar_font = tkfont.Font(family='Helvetica', size=8, weight="bold", slant="italic")
        self.main_Menu_font = tkfont.Font(family='Helvetica', size= 15, weight="bold")
        self.allfont = tkfont.Font(family = "Times New Roman", size = 8, weight = "bold")
        self.spinbox_font = tkfont.Font(family = "Times New Roman", size = 25, weight = "bold")
        
        #Test Run Vars
        self.test_settings = {}
        
        #pump vars DEFAULTS -- TO BE LOADED FROM FILE!  <-------##
        self.__tube_diameter = 0
        self.__pulse_per_revolution = 0
        self.__length_per_revolution = 0
        self.__systolic_percentage_value = 0
        self.__stroke_volume_value = 0
        self.__rate_value = 0
        self.__peak_percentage_value = 0
        self.__lock_on_start = False
        self.__remaining_degrees = 1
        self.__occlusion = 0
        

        # the container is where we'll stack a bunch of frames
        # on top of each other, then the one we want visible
        # will be raised above the others
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        self.check_info_file('config.json') 

        self.frames = {}
        for F in (SplashScreen, MainMenu, CalPumpChamber, PumpOperation, RunTests, AutomateTests):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            # put all of the pages in the same location;
            # the one on the top of the stacking order
            # will be the one that is visible.
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("SplashScreen")
        

    def show_frame(self, page_name):
        '''Show a frame for the given page name'''
        frame = self.frames[page_name]
        frame.tkraise()
    
    # Config File, JSON.
    def check_info_file(self,path):
        
        defaultDict = {"tube_diameter": 25, "pulse_per_revolution": 5000,"length_per_revolution": 3,
                       "systolic_percentage_value": 50, "stroke_volume_value": 6,
                       "rate_value": 60, "peak_percentage_value": 50, "lock_on_start": False,
                       "remaining_degrees": 1, "occlusion": 0} 
        
        if os.path.isfile(path):    
            f = open(path, "r")
            data = f.read()
            f.close()
            converted = json.loads(data)  # We convert the JSON object to a Dictionary   
        else:
            #print ("File does not exist")
            default_json = json.dumps(defaultDict, indent=4) #Convert Dict to Json
            converted = json.loads(default_json) # We convert the JSON object to a Dictionary

            f = open(path,"w")
            f.write(default_json)
            f.close()

        self.set_tube_diameter(converted['tube_diameter'])
        self.set_pulse_per_revolution(converted['pulse_per_revolution'])
        self.set_length_per_revolution(converted['length_per_revolution'])
        self.set_systolic_percentage_value(converted['systolic_percentage_value'])
        self.set_stroke_volume_value(converted['stroke_volume_value'])
        self.set_rate_value(converted['rate_value'])
        self.set_peak_percentage_value(converted['peak_percentage_value'])
        
        self.set_lock_on_start(converted['lock_on_start'])
        self.set_remaining_degrees(converted['remaining_degrees'])
        
        try:
            self.set_occlusion(converted['occlusion'])
        except:
            converted['occlusion'] = 0
            self.set_occlusion(converted['occlusion'])
            self.save_info_file(converted['tube_diameter'], converted['pulse_per_revolution'],
                           converted['length_per_revolution'],
                           converted['systolic_percentage_value'],
                           converted['stroke_volume_value'],
                           converted['rate_value'], converted['peak_percentage_value'],
                           converted['lock_on_start'], converted['remaining_degrees'],
                           converted['occlusion'])
            
        
    # Save config File            
    def save_info_file(self, tube_diameter, pulse_per_revolution, length_per_revolution, systolic_percentage_value, stroke_volume_value, rate_value, peak_percentage_value, lock_on_start_value,remaining_degrees, occlusion):
        
        defaultDict = {"tube_diameter": tube_diameter, "pulse_per_revolution": pulse_per_revolution,
                       "length_per_revolution": length_per_revolution, "systolic_percentage_value": systolic_percentage_value,
                       "stroke_volume_value": stroke_volume_value, "rate_value": rate_value, "peak_percentage_value": peak_percentage_value,
                       "lock_on_start": lock_on_start_value, "remaining_degrees": remaining_degrees, "occlusion": occlusion}
        default_json = json.dumps(defaultDict, indent=4) # Dictionary to JSON
        f = open('config.json',"w")
        f.write(default_json)
        f.close()
          
        
######################GETTERS########################
        
    def get_tube_diameter(self):
        return self.__tube_diameter
    
    def get_pulse_per_revolution(self):
        return self.__pulse_per_revolution
    
    def get_length_per_revolution(self):
        return self.__length_per_revolution
    
    def get_systolic_percentage_value(self):
        return self.__systolic_percentage_value
    
    def get_stroke_volume_value(self):
        return self.__stroke_volume_value
    
    def get_rate_value(self):
        return self.__rate_value
    
    def get_peak_percentage_value(self):
        return self.__peak_percentage_value
    
    def get_lock_on_start(self):
        return self.__lock_on_start
    
    def get_remaining_degrees(self):
        return self.__remaining_degrees
    
    def get_occlusion(self):
        return self.__occlusion

######################SETTERS########################
    
    def set_tube_diameter(self, tube_diameter):
        self.__tube_diameter = tube_diameter
        
    def set_pulse_per_revolution(self, pulse_per_revolution):
        self.__pulse_per_revolution = pulse_per_revolution
    
    def set_length_per_revolution(self, length_per_revolution):
        self.__length_per_revolution = length_per_revolution
        
    def set_systolic_percentage_value(self, systolic_percentage_value):
        self.__systolic_percentage_value = systolic_percentage_value
    
    def set_stroke_volume_value(self, stroke_volume_value):
        self.__stroke_volume_value = stroke_volume_value
    
    def set_rate_value(self, rate_value):
        self.__rate_value = rate_value
        
    def set_peak_percentage_value(self, peak_percentage_value):
        self.__peak_percentage_value = peak_percentage_value
        
    def set_lock_on_start(self, lock_on_start):
        self.__lock_on_start = lock_on_start
        
    def set_remaining_degrees(self, remaining_degrees):
        self.__remaining_degrees = remaining_degrees
        
    def set_occlusion(self, occlusion):
        self.__occlusion = occlusion
        
        
class SplashScreen(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(cursor='none')
        
        def someFunct(x,y):
            image = Image.open("heart.png")
            image = image.resize((x,y), Image.ANTIALIAS)
            photo = ImageTk.PhotoImage(image)
            photo_label.configure(image=photo)
            photo_label.image = photo
        
        def out_of_here():
            self.after(1000,someFunct,260,220)
            self.after(2000,someFunct,250,210)
            self.after(3000,someFunct,260,220)
            self.after(4000,someFunct,250,210)
            controller.after(5000, controller.show_frame, 'MainMenu')
            
            
        label  = tk.Label(self, text="TRIPHASIC CARDIAC PUMP", font=controller.spinbox_font)
        label2 = tk.Label(self, text = "Physiological Perfusion", font=controller.title_font)
        label3 = tk.Label(self, text = "Triphasic", font=controller.title_font)
        label4 = tk.Label(self, text = "Albert Chong", font=controller.allfont)
        label5 = tk.Label(self, text = " ", font=controller.allfont)
        
        photo_label = tk.Label(self)
        #photo_label.grid(row = 1, column = 12, columnspan = 3, rowspan = 3)
        
        image = Image.open("heart.png")
        image = image.resize((250,210), Image.ANTIALIAS)
        photo = ImageTk.PhotoImage(image)
        photo_label.configure(image=photo)
        photo_label.image = photo
        
        label.pack(pady = 30, padx = 10)
        #photo_label.place(relx=0.5, rely=0.35, anchor= 'center')
        photo_label.pack()
        label5.pack(side = 'bottom',ipady = 30)
        label4.pack(side = 'bottom')
        label3.pack(side = 'bottom')
        label2.pack(side = 'bottom')
        out_of_here()
             
        
class MainMenu(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(bg='skyblue',cursor='none')
        self.button_font = tkfont.Font(family='Helvetica', size=13, weight="bold", slant="italic")
        self.button_width = 50
        self.button_height = 2
        
        label = tk.Label(self, text="Main Menu", font = controller.main_Menu_font, fg = 'ivory2', bg = 'black')
        label.pack(side="top", fill="x", pady=0)
        
        button1 = tk.Button(self, text="Calibrate Pump Chamber",height=self.button_height, width=self.button_width, font=self.button_font, bg='blue', fg='white',
                            command=lambda: controller.show_frame("CalPumpChamber"))
        
        button2 = tk.Button(self, text="Pump Operation",height=self.button_height, width=self.button_width, font=self.button_font, bg='blue', fg='white',
                            command=lambda: controller.show_frame("PumpOperation"))
        
        button3 = tk.Button(self, text="Run Tests",height=self.button_height, width=self.button_width, font=self.button_font, bg='blue', fg='white',
                            command=lambda: controller.show_frame("RunTests"))
        
        button4 = tk.Button(self, text="Exit Application",height=self.button_height, width=self.button_width, font=self.button_font, bg = 'green', fg='white',
                            command=lambda: controller.destroy())
        
        button1.pack(pady = 20)
        button2.pack(pady = 20)
        button3.pack(pady = 20)
        button4.pack(pady = 11)
      
        
# Calabration Menu / Frame Class        
class CalPumpChamber(tk.Frame):
     
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.config(cursor='none')
        
            
        # Value check for Stepper Conttroller valid pulse per rev
        def valuecheck(value):
            newvalue = min(self.valuelist, key=lambda x:abs(x-float(value)))
            pulse_per_revolution_slider.set(newvalue)
            
            
        # Save Config Values    
        def saveStuff():
            #Get Data
            controller.set_tube_diameter(tube_diameter_slider.get())
            controller.set_pulse_per_revolution(pulse_per_revolution_slider.get())
            controller.set_length_per_revolution(length_per_revolution_slider.get())
            controller.set_stroke_volume_value(stroke_volume_value_slider.get())
            controller.set_systolic_percentage_value(systolic_percentage_slider.get())
            controller.set_rate_value(heart_rate_slider.get())
            controller.set_peak_percentage_value(peak_percentage_slider.get())
            controller.set_lock_on_start(var1.get())
            controller.set_remaining_degrees(remaining_degrees_slider.get())
            controller.set_occlusion(occlusion_slider.get())
            #Save Data
            controller.save_info_file(controller.get_tube_diameter(),
                                      controller.get_pulse_per_revolution(),
                                      controller.get_length_per_revolution(),
                                      controller.get_systolic_percentage_value(),
                                      controller.get_stroke_volume_value(),
                                      controller.get_rate_value(),
                                      controller.get_peak_percentage_value(),
                                      controller.get_lock_on_start(),
                                      controller.get_remaining_degrees(),
                                      controller.get_occlusion())
                                      

            controller.destroy() #<-- END WITH
        
        #Get Defaults
        var1 = tk.BooleanVar(value = controller.get_lock_on_start())
        self.tube_diameter_value = controller.get_tube_diameter()
        self.pulse_per_revolution = controller.get_pulse_per_revolution()
        self.length_per_revolution_value = controller.get_length_per_revolution()
        self.stroke_volume_value = controller.get_stroke_volume_value()
        self.heart_rate_value = controller.get_rate_value()
        self.systolic_percentage = controller.get_systolic_percentage_value()
        self.peak_percentage_value = controller.get_peak_percentage_value()
        self.remaining_degrees_value = controller.get_remaining_degrees()
        self.occlusion_value = controller.get_occlusion()
        # Create/Set Tk String Vars
        self.tube_diameter = tk.StringVar()
        self.tube_diameter.set(self.tube_diameter_value)
        self.length_per_revolution = tk.StringVar()
        self.length_per_revolution.set(self.length_per_revolution_value)
        self.stroke_volume = tk.StringVar()
        self.stroke_volume.set(self.stroke_volume_value)
        self.heart_rate = tk.StringVar()
        self.heart_rate.set(self.heart_rate_value)
        self.pulse_percentage = tk.StringVar()
        self.pulse_percentage.set(self.systolic_percentage)
        self.peak_percentage = tk.StringVar()
        self.peak_percentage.set(self.peak_percentage_value)
        self.remaining_degrees = tk.StringVar()
        self.remaining_degrees.set(self.remaining_degrees_value)
        self.occlusion = tk.StringVar()
        self.occlusion.set(self.occlusion_value)
        
        self.spinner_font = tkfont.Font(family='Helvetica', size=25, weight='bold')
        self.label_font = tkfont.Font(family = "Times New Roman", size = 13, weight = "bold")
        
        #Stepper Controller Settings, Valid values
        self.valuelist = [400,800,1000,1600,2000,3200,4000,5000,6400,8000,10000,12800,20000,25600,40000,51200]
        
        label = tk.Label(self, text="Calabrate Pump Chamber", font=controller.title_font, height = 2,justify = 'center')
        label.grid(row = 0, column = 0, columnspan = 1, sticky = 'nesw')

        #tube_diameter -----------------------------
        tube_diameter_label = tk.Label(self, text = 'Tube Diameter', font = self.label_font, bg = 'light green')
        tube_diameter_label.grid(row = 2, column = 0, columnspan = 1, sticky = 'nesw')
        
        tube_diameter_spinbox = tk.Spinbox(self,  from_ = 2, to = 50, width = 1, bg = 'light green',
                                           textvariable = self.tube_diameter, justify = 'right',
                                           font=self.spinner_font)
        tube_diameter_spinbox['state'] = 'readonly'
        tube_diameter_spinbox.grid(row = 3, column = 0, rowspan = 1, sticky = 'nesw')
            
        tube_diameter_slider = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 2, to = 50,
                                        showvalue = 0, bg = 'light green', length = 10, variable = self.tube_diameter,
                                        sliderlength = 60, width = 60)
        tube_diameter_slider.grid(row = 5, column = 0, rowspan = 1, columnspan = 1, sticky = 'nesw')
        tube_diameter_slider.set(self.tube_diameter_value)
        
        #pulse_per_revolution  ----------------------
        pulse_per_revolution_label = tk.Label(self, text = 'Pulse Per Revolution', font = self.label_font, bg = 'steel blue')
        pulse_per_revolution_label.grid(row = 2, column = 1, columnspan = 1, sticky = 'nesw')

        pulse_per_revolution_spinbox = tk.Spinbox(self,  values = self.valuelist, width = 1, bg = 'steel blue',
                                                  textvariable = self.pulse_per_revolution, justify = 'right',
                                                  font=self.spinner_font)
        pulse_per_revolution_spinbox['state'] = 'readonly'
        pulse_per_revolution_spinbox.grid(row = 3, column = 1, rowspan = 1, sticky = 'nesw')
            
        pulse_per_revolution_slider = tk.Scale(self, orient=tk.HORIZONTAL, from_=0, to=max(self.valuelist),
                                               showvalue = 0, command=valuecheck, bg = 'steel blue', length = 200,
                                               variable = self.pulse_per_revolution, sliderlength = 60, width = 60)
        pulse_per_revolution_slider.grid(row = 5, column = 1, rowspan = 1, columnspan = 1, sticky = 'nesw')
        pulse_per_revolution_slider.set(self.pulse_per_revolution)
        
        #length_per_revolution ----------------
        length_per_revolution_label = tk.Label(self, text = 'Length Per Rev (mm)', font = self.label_font, bg = 'tomato')
        length_per_revolution_label.grid(row = 2, column = 2, columnspan = 1, sticky = 'nesw')
        
        length_per_revolution_spinbox = tk.Spinbox(self,  from_ = 1, to = 20, width = 5, bg = 'tomato',
                                                   textvariable = self.length_per_revolution, justify = 'right',
                                                   font=self.spinner_font)
        length_per_revolution_spinbox['state'] = 'readonly'
        length_per_revolution_spinbox.grid(row = 3, column = 2, rowspan = 1, sticky = 'nesw')
            
        length_per_revolution_slider = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 1, to = 20,
                                                showvalue = 0, bg = 'tomato', length = 200,
                                                variable = self.length_per_revolution, sliderlength = 60, width = 60)
        length_per_revolution_slider.grid(row = 5, column = 2, rowspan = 1, columnspan = 1, sticky = 'nesw')
        length_per_revolution_slider.set(self.length_per_revolution_value)
        
        #Stroke Volume ------------------------
        stroke_volume_value_label = tk.Label(self, text = 'Stroke Volume', font = self.label_font, bg = 'orange')
        stroke_volume_value_label.grid(row = 9, column = 0, columnspan = 1, sticky = 'nesw')
        
        stroke_volume_value_spinbox = tk.Spinbox(self,  from_ = 1, to = 100, width = 5, bg = 'orange',
                                                    textvariable = self.stroke_volume, justify = 'right',
                                                    font=self.spinner_font)
        stroke_volume_value_spinbox['state'] = 'readonly'
        stroke_volume_value_spinbox.grid(row = 10, column = 0, rowspan = 1, sticky = 'nesw')
            
        stroke_volume_value_slider = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 1, to = 100, showvalue = 0, bg = 'orange',
                                                 length = 150, variable = self.stroke_volume, sliderlength = 60, width = 60)
        stroke_volume_value_slider.grid(row = 13, column = 0, rowspan = 1, columnspan = 1, sticky = 'nesw')
        stroke_volume_value_slider.set(self.stroke_volume_value)     
        
        #heart_rate_value
        heart_rate_label = tk.Label(self, text = 'Heart Rate', font = self.label_font, bg = 'pink')
        heart_rate_label.grid(row = 9, column = 1, columnspan = 1, sticky = 'nesw')
        
        heart_rate_spinbox = tk.Spinbox(self,  from_ = 30, to = 120, width = 5, bg = 'pink',
                                                    textvariable = self.heart_rate, justify = 'right',
                                                    font=self.spinner_font)
        heart_rate_spinbox['state'] = 'readonly'
        heart_rate_spinbox.grid(row = 10, column = 1, rowspan = 1, sticky = 'nesw')
            
        heart_rate_slider = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 30, to = 120, showvalue = 0, bg = 'pink',
                                                 length = 150, variable = self.heart_rate, sliderlength = 60, width = 60)
        heart_rate_slider.grid(row = 13, column = 1, rowspan = 1, columnspan = 1, sticky = 'nesw')
        heart_rate_slider.set(self.heart_rate_value)
        
        #systolic_percentage --------------------------
        systolic_percentage_label = tk.Label(self, text = 'Systolic Percentage', font = self.label_font, bg = 'skyblue1')
        systolic_percentage_label.grid(row = 9, column = 2, columnspan = 1, sticky = 'nesw')
        
        systolic_percentage_spinbox = tk.Spinbox(self,  from_ = 20, to = 80, increment = 10, width = 5, bg = 'skyblue1',
                                                    textvariable = self.pulse_percentage, justify = 'right',
                                                    font=self.spinner_font)
        systolic_percentage_spinbox['state'] = 'readonly'
        systolic_percentage_spinbox.grid(row = 10, column = 2, rowspan = 1, sticky = 'nesw')
            
        systolic_percentage_slider = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 20, to = 80,resolution = 10,showvalue = 0, bg = 'skyblue1',
                                                 length = 150, variable = self.pulse_percentage, sliderlength = 60, width = 60)
        systolic_percentage_slider.grid(row = 13, column = 2, rowspan = 1, columnspan = 1, sticky = 'nesw')
        systolic_percentage_slider.set(self.systolic_percentage)
        
        #peak_percentage --------------------------
        peak_percentage_label = tk.Label(self, text = 'Peak Percentage', font = self.label_font, bg = 'yellow')
        peak_percentage_label.grid(row = 9, column = 3, columnspan = 1, sticky = 'nesw')
        
        peak_percentage_spinbox = tk.Spinbox(self,  from_ = 20, to = 80, increment = 10, width = 5, bg = 'yellow',
                                                    textvariable = self.peak_percentage, justify = 'right',
                                                    font=self.spinner_font)
        peak_percentage_spinbox['state'] = 'readonly'
        peak_percentage_spinbox.grid(row = 10, column = 3, rowspan = 1, sticky = 'nesw')
            
        peak_percentage_slider = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 20, to = 80, resolution = 10, showvalue = 0, bg = 'yellow',
                                                 length = 150, variable = self.peak_percentage, sliderlength = 60, width = 60)
        peak_percentage_slider.grid(row = 13, column = 3, rowspan = 1, columnspan = 1, sticky = 'nesw')
        peak_percentage_slider.set(self.peak_percentage_value)
                                                        
        remaining_degrees_label = tk.Label(self, text = 'Initial Posi from Home°', font = self.label_font, bg = 'bisque2')
        remaining_degrees_label.grid(row = 2, column = 3, columnspan = 1, sticky = 'nesw')
        remaining_degrees_spinbox = tk.Spinbox(self,  from_ = 1, to = 45, increment = 1, width = 5, bg = 'bisque2',
                                                    textvariable = self.remaining_degrees, justify = 'right',
                                                    font=self.spinner_font)
        remaining_degrees_spinbox.grid(row = 3, column = 3, rowspan = 1, sticky = 'nesw')
        remaining_degrees_slider = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 1, to = 45, resolution = 1, showvalue = 0, bg = 'bisque2',
                                                 length = 150, variable = self.remaining_degrees, sliderlength = 60, width = 60)
        remaining_degrees_slider.grid(row = 5, column = 3, rowspan = 1, columnspan = 1, sticky = 'nesw')
        remaining_degrees_slider.set(self.remaining_degrees_value)
              
        occlusion_label = tk.Label(self, text = 'Occlusion °', font = self.label_font, bg = 'MediumOrchid2')
        occlusion_label.grid(row = 15, column = 0, columnspan = 1, sticky = 'nesw')
        occlusion_spinbox = tk.Spinbox(self, from_ = 0, to = 180, increment = 1, width = 5, bg = 'MediumOrchid2',
                                                    textvariable = self.occlusion, justify = 'right',
                                                    font=self.spinner_font)
        occlusion_spinbox.grid(row = 16, column = 0, rowspan = 1, sticky = 'nesw')
        occlusion_slider = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 0, to = 180, resolution = 1, showvalue = 0, bg = 'MediumOrchid2',
                                                 length = 150, variable = self.occlusion, sliderlength = 60, width = 60)
        occlusion_slider.grid(row = 17, column = 0, rowspan = 1, columnspan = 1, sticky = 'nesw')
        occlusion_slider.set(self.occlusion_value)
        
        #Exit Buttons ----------------------
        no_save_button = tk.Button(self, text="Exit without saving", font = self.label_font, command=lambda: controller.show_frame("MainMenu"),bg = 'red')
        no_save_button.grid(row = 17, column = 3, columnspan = 1, sticky = 'nesw')
        
        save_button = tk.Button(self, text= "Save - Restart required", font = self.label_font, command=saveStuff, bg = 'limegreen')
        save_button.grid(row = 17, column = 2, columnspan = 1, sticky = 'nesw')
        
        lock_on_start = tk.Checkbutton(self, text="Lock controls @ start", variable = var1, onvalue=True, offvalue=False)
        lock_on_start.grid(row=15, column= 1, columnspan = 1, sticky='nesw')
         
        
# Pump Operation Class / Page
class PumpOperation(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.config(cursor='none')
        self.servo_gpio = 12 # PIN 32 = GPIO 12
              
        color1 = 'white'
        color2 = 'gray'
        self.__patient = ""
        self.first_run = True
        
        # Pressure sensor variables
        voltage_low_limit = 0.5 # Lowest valid voltage value @ 0 PSI
        voltage_high_limit = 4.5 # Highest valid voltage value @ 5 PSI
        pressure_range = 10 # 10 PSI Max reading range.
        voltage_reading = 0.0
        pressure = 0.0
        
        # Create figure for plotting
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.psi_xs = []
        self.psi_ys = []
        self.flow_xs = []
        self.flow_ys = []
        
        # Getters and Setters
        #####################
        def get_patient():
            return self.__patient
        
        
        def set_patient(self, patient):
            self.__patient = patient
        ######################    
        
        #Remove/Delete Plot File
        def remove_foo():
            try:
                os.remove("foo.png")
            except:
                #print("no file yet")
                pass
            
            while os.path.isfile("foo.png") == True:
                pass
         
         
        #Required to create new arrays and PWM waves or will crash - non-existant Wave ID.     
        def initialise_pump_settings():
            self.pump.return_wave_setting() 
            self.pump.initial_wave_setting()
            self.pump.step_count_setting()
        
        
        #Enable sliders and spinboxes 
        def enable_controls():
            stroke_vol_spinbox['state'] = 'readonly'
            heart_rate_spinbox['state'] = 'readonly'
            systolic_percentage_spinbox['state'] = 'readonly'
            systole_a_p_spinbox['state'] = 'readonly'
            occluder_spinbox['state'] = 'readonly'
                
            stroke_vol_slider['state'] = 'normal'
            heart_rate_slider['state'] = 'normal'
            systolic_percent_slider['state'] = 'normal'
            systole_a_p_slider['state'] = 'normal'
            occluder_slider['state'] = 'normal'
            
            stroke_vol_slider.bind("<ButtonRelease-1>", change_detect)
            heart_rate_slider.bind("<ButtonRelease-1>", change_detect)
            systolic_percent_slider.bind("<ButtonRelease-1>", change_detect)
            systole_a_p_slider.bind("<ButtonRelease-1>", change_detect)
            occluder_slider.bind("<ButtonRelease-1>", change_detect)
            
            
        #Disable sliders and spinboxes     
        def disable_controls():
            stroke_vol_spinbox['state'] = 'disabled'
            heart_rate_spinbox['state'] = 'disabled'
            systolic_percentage_spinbox['state'] = 'disabled'
            systole_a_p_spinbox['state'] = 'disabled'
            occluder_spinbox['state'] = 'disabled'
            
            stroke_vol_slider['state'] = 'disabled'
            heart_rate_slider['state'] = 'disabled'
            systolic_percent_slider['state'] = 'disabled'
            systole_a_p_slider['state'] = 'disabled'
            occluder_slider['state'] = 'disabled'
            stroke_vol_slider.unbind("<ButtonRelease-1>")
            heart_rate_slider.unbind("<ButtonRelease-1>")
            systolic_percent_slider.unbind("<ButtonRelease-1>")
            systole_a_p_slider.unbind("<ButtonRelease-1>")
            occluder_slider.unbind("<ButtonRelease-1>")
            
            
        #Input Change - uses EVENT
        def change_detect(event):
            self.throttle_valve.set_angle(occluder_slider.get())
            if self.pump.running == True: 
                set_up_pump_variables()
                self.pump.i_made_new_data = False
                self.pump.condition_change = 1
            else:  
                disable_controls()
                set_up_pump_variables()
                initialise_pump_settings()
                enable_controls()
                self.pump.condition_change = 1
            threading.Thread(name='States_thread', target=states).start()
         
        
        #Input Change - NO EVENT 
        def change_detect_no_event():
            self.throttle_valve.set_angle(occluder_slider.get())
            running = self.pump.running
            if running == True:      
                set_up_pump_variables()
                self.pump.i_made_new_data = False
                self.pump.condition_change = 1
            else:
                set_up_pump_variables()
                initialise_pump_settings()
                self.pump.condition_change = 1
                
            threading.Thread(name='States_thread', target=states).start()
            
            
        # THREAD - Handle Update Screen    
        def states():
            while True:
                
                if self.pump.running == True:
                    #print('The pump is running at ' + str(self.pump.systolic_percentage_value) + ' percent of systolic, ' + str(self.pump.rate_value) + ' beat per minute, and ' + str(self.pump.volume_value) + ' percent occlusion')
                    status_bar['text'] = 'The pump is running at ' + str(self.pump.systolic_percentage_value) + ' percent of systolic, ' + str(self.pump.rate_value) + ' beat per minute, and ' + str(self.pump.volume_value) + ' percent occlusion'
                    self.pump.step_count_complete == False
                    self.pump.stop_start_call == False
                    break  
                    
                time.sleep(0.2)
                
        # THREAD - check for motor stop condition   
        def start_stop_states():
            while True:

                if  self.pump.running == False:
                    #print('The movement has been stopped')
                    status_bar['text'] = 'The movement has been stopped'
                    self.pump.stop_start_call == False
                    break
                
                time.sleep(0.2)
                
               
        #Start and stop the pump. Change button colours and disable/enable controls -sliders and spinboxes                    
        def start_stop_function():
            
            if self.pump.running == True:
                start_stop_button.configure(bg='green')
                customise_button['state'] = 'normal'
                return_initial['state'] = 'normal'
                exit_button['state'] = 'normal'
                
                if controller.get_lock_on_start() == True:
                    disable_controls()
                else:
                    enable_controls()
            else:
                
                start_stop_button.configure(bg='red')
                enable_controls()
                customise_button['state'] = 'disabled'
                return_initial['state'] = 'disabled'
                exit_button['state'] = 'disabled'
                                  
            if self.pump.running == False:
                status_bar['text'] = 'The pump is running at ' + str(self.pump.systolic_percentage_value) + ' percent of systolic, ' + str(self.pump.rate_value) + ' beat per minute, and ' + str(self.pump.volume_value) + ' percent occlusion'
         
            threading.Thread(name='start_stop_states',target=start_stop_states).start()
            threading.Thread(name='States_thread', target=states).start()
            threading.Thread(name='Pump_start_stop_function', target=self.pump.start_stop_function).start()
            threading.Thread(name='draw_psi_plot', target=draw_psi_plot).start()    
                      
            
        # Open Patient File and setup pump settings and plot it.
        def function_c():
            
            filetypes = (
                ('json files', '*.json'),
                ('All files', '*.*')
                )
            
            filename = filedialog.askopenfilename(filetypes=filetypes)
            f = open(filename, "r")
            data = f.read()
            
            converted = json.loads(data)  # We convert the JSON object to a Dictionary
            set_patient(self,converted['patient_name'])
            self.stroke_volume.set(converted['stroke_volume_value'])
            self.heart_rate.set(converted['rate_value'])
            self.pulse_percentage.set(converted['systolic_percentage_value'])
            self.peak_percentage.set(converted['peak_percentage_value'])
            
            set_up_pump_variables()
            initialise_pump_settings()
            enable_controls()
        
        
        def move_initial_funct_done_check():
            while True:
                if self.pump.move_initial_end == True:
                    start_stop_button['bg']='green'
                    start_stop_button['state'] = 'normal'
                    break
        
        # Return Initial Function    
        def return_initial_function():   
            #self.pump.set_i_made_new_data(False)
            
            self.pump.move_initial_end = False
            
            if self.pump.direction == 1 and self.first_run == True:
                self.first_run = False
                status_bar['text'] = 'Welcome to the System'
                self.pump.return_initial_function()
                
            elif self.pump.direction == 1:
                status_bar['text'] = 'Back to home position'
                self.pump.return_initial_function()
            else:
                self.pump.return_initial_function()
                status_bar['text'] = 'Move to Initial position'
                threading.Thread(name='Move_init_posi', target=move_initial_funct_done_check).start()
                
        # EXIT Program   
        def exit_function():    
            self.pump.pi.wave_tx_stop()
            self.pump.pi.wave_clear()
            self.pump.pi.stop()
            self.destroy()
            
         
       # Set up pump variables from slider values. 
        def set_up_pump_variables():
            self.pump.volume_value = stroke_vol_slider.get()  #
            self.pump.rate_value = heart_rate_slider.get()
            self.pump.systolic_percentage_value = systolic_percent_slider.get()
            self.pump.peak_percentage_value = systole_a_p_slider.get()
            
            
        # Exit to Main Menu
        def exit_to_main():
            remove_foo()
            try:
                os.remove("foo2.png")
            except:
                print("no foo2.png file")
            finally:
                controller.show_frame("MainMenu")
            
        # Gets Sensor Values, Resizes plot image, then displays it.   
        def draw_psi_plot():
            while(self.pump.running == True):
                first = multiprocessing.Process(target=aquire_sensor_values, args=()) # get sensor values
                first.start()
                first.join()
                
                image = Image.open("foo2.png")
                image = image.resize((260,220), Image.ANTIALIAS)
                photo = ImageTk.PhotoImage(image)
                plot_psi_label.configure(image=photo)
                plot_psi_label.image = photo
                
                image = Image.open("foo1.png")
                image = image.resize((260,220), Image.ANTIALIAS)
                photo = ImageTk.PhotoImage(image)
                plot_flow_label.configure(image=photo)
                plot_flow_label.image = photo
                
        #Read Sensor Values            
        def aquire_sensor_values():
            # Get PSI and FLow sensor values
            self.psi_xs, self.psi_ys, self.flow_xs, self.flow_ys = self.sensors.get_sensor_values()           
            # Graph PSI and Flow Values
            graph_psi_values()
        
        #Plot the results into images and save into a image file.      
        def graph_psi_values():
            #            
            # Draw plot PSI
            plt.axis([0, 200, 0, 6])
            plt.xticks(rotation=45, ha='right')
            #plt.subplots_adjust(bottom=0.30)
            plt.title(str(self.maxPSI) + ' PSI pressure sensor', fontsize=18)
            plt.ylabel('PSI', fontsize=13)
            plt.plot(self.psi_xs, self.psi_ys)
            plt.tick_params(labelsize=11,labelcolor="red")
            self.ax.plot(self.psi_xs, self.psi_ys)
            
            # Draw the graph PNG
            plt.savefig('foo2.png')
            plt.clf()
            self.psi_ys.clear()
            self.psi_xs.clear()
            ##############################################################
            # Draw plot FLOW
            plt.axis([0, 200, 0, 5])
            plt.xticks(rotation=45, ha='right')
            #plt.subplots_adjust(bottom=0.30)
            plt.title('Flow Rate (volts)', fontsize=18)
            plt.ylabel('Flow', fontsize=13)
            plt.plot(self.flow_xs, self.flow_ys)
            plt.tick_params(labelsize=11,labelcolor="red")
            self.ax.plot(self.flow_xs, self.flow_ys)
            
            # Draw the graph PNG
            plt.savefig('foo1.png')
            plt.clf()
            self.flow_ys.clear()
            self.flow_xs.clear()
            
        def occluder_to_position():
            self.throttle_valve.set_angle(self.controller.get_occlusion())
            
        
            
#################################################################################################################################################
#################################################################################################################################################
                                     
    # --MAIN--
    
        #Sensors Instance
        self.maxPSI = 10
        self.sensors = PumpSensor(self.maxPSI)
        #Servo Instance
        self.throttle_valve = Occluder(self.servo_gpio, 600, 2300)
        #Pump instance
        self.pump = Pump(17,27,5,20,controller.get_pulse_per_revolution(),controller.get_length_per_revolution(),
                         controller.get_tube_diameter(), controller.get_remaining_degrees())
        
        #Set pump vars
        self.pump.volume_value = controller.get_stroke_volume_value()
        self.pump.rate_value = controller.get_rate_value()
        self.pump.systolic_percentage_value = controller.get_systolic_percentage_value()
        self.pump.peak_percentage_value = controller.get_peak_percentage_value()
        self.occluder_angle_value = controller.get_occlusion()
        
        #Defaut / Startup Plot Image - Blank
        self.fillerImage ="white.jpeg"
        
        #Fonts
        self.spinner_font = tkfont.Font(family='Helvetica', size=18, weight='bold')
        self.label_font = tkfont.Font(family = "Times New Roman", size = 13, weight = "bold")
        
        #TK Stuff
        #Status bar setting
        status_bar = tk.Label(self, text = 'Welcome to the system', font = controller.status_bar_font,
                              bg = 'white', relief = 'groove')
        
        status_bar.grid(row = 0, column = 0, rowspan = 1, columnspan = 18, sticky = 'nesw')
        
        stroke_vol_slider = tk.Scale(self, from_ = 98, to = 1, showvalue = 0, bg = 'orange', length = 200,
                                     sliderlength = 60, width = 20)
        
        heart_rate_slider = tk.Scale(self, from_ = 120, to = 30, showvalue = 0, bg = 'pink', length = 200,
                                     sliderlength = 60, width = 20)
        
        systolic_percent_slider = tk.Scale(self, from_ = 80, to = 20, showvalue = 0, resolution = 10,
                                           bg = 'skyblue1', length = 200, sliderlength = 60, width = 20)
        
        start_stop_button = tk.Button(self, text = 'Start/\nStop', font = controller.allfont,fg = 'ivory2',
                               bg = 'black', height = 2, state ='disabled')
        
        customise_button = tk.Button(self, text = 'Customise', font = controller.allfont, bg = color1, height = 2)
        
        return_initial = tk.Button(self, text = 'Return/\nInitialise', font = controller.allfont,
                                   bg = color1, height = 1)
        
        exit_button = tk.Button(self, text = 'Exit', font = controller.allfont, bg = color1, height = 2)
                   
        #Tk string vars
        self.stroke_volume = tk.StringVar()
        self.stroke_volume.set(self.pump.volume_value)
        self.heart_rate = tk.StringVar()
        self.heart_rate.set(self.pump.rate_value)
        self.pulse_percentage = tk.StringVar()
        self.pulse_percentage.set(self.pump.systolic_percentage_value)
        self.peak_percentage = tk.StringVar()
        self.peak_percentage.set(self.pump.peak_percentage_value)
        self.occluder_angle = tk.StringVar()
        self.occluder_angle.set(self.occluder_angle_value)
        print("occluder_angle: ",self.occluder_angle_value)

        #Tk set string vars
        stroke_vol_slider['variable'] = self.stroke_volume
        heart_rate_slider['variable'] = self.heart_rate
        systolic_percent_slider['variable'] = self.pulse_percentage
        
        # Setup utton Commands
        start_stop_button['command'] = start_stop_function
        customise_button['command'] = function_c
        return_initial['command'] = return_initial_function
        exit_button['command'] = exit_to_main
        
        #Adjustment setting
        stroke_vol_label = tk.Label(self, text = 'Stroke volume', font = controller.allfont, bg = 'orange')
        stroke_vol_spinbox = tk.Spinbox(self, command = change_detect_no_event, from_ = 1, to = 98, width = 2, bg = 'orange',
                                        textvariable = self.stroke_volume, justify = 'right', font = self.spinner_font)
        stroke_vol_spinbox['state'] = 'disabled'
        stroke_vol_slider.bind("<ButtonRelease-1>", change_detect)
        
        heart_rate_label = tk.Label(self, text = 'Heart rate', font = controller.allfont, bg = 'pink')
        heart_rate_spinbox = tk.Spinbox(self, command = change_detect_no_event, from_ = 30, to = 120, width = 2,
                                        bg = 'pink', textvariable = self.heart_rate, justify = 'right',
                                        font = self.spinner_font)
        heart_rate_spinbox['state'] = 'disabled'
        heart_rate_slider.bind("<ButtonRelease-1>", change_detect)
        
        systolic_percentage_label = tk.Label(self, text = 'Systolic percentage', font = controller.allfont, bg = 'skyblue1')
        systolic_percentage_spinbox = tk.Spinbox(self, command = change_detect_no_event, from_ = 20, to = 80,
                                                 width = 2, increment = 10, bg = 'skyblue1', textvariable = self.pulse_percentage,
                                                 justify = 'right',font = self.spinner_font)
        systolic_percentage_spinbox['state'] = 'disabled'
        systolic_percent_slider.bind("<ButtonRelease-1>", change_detect)
        
        systole_a_p_label = tk.Label(self, text = 'Systole AP', font = controller.allfont, bg = 'yellow')
        systole_a_p_spinbox = tk.Spinbox(self, command = change_detect_no_event,from_ = 20, to = 80, width = 2, increment = 10,
                                         bg = 'yellow', textvariable = self.peak_percentage, justify = 'right',
                                         font = self.spinner_font)
        systole_a_p_spinbox['state'] = 'disabled'
        systole_a_p_slider = tk.Scale(self, from_ = 80, to = 20, showvalue = 0, resolution = 10,
                                      bg = 'yellow', variable = self.peak_percentage, length = 200, sliderlength = 60, width = 20)
        systole_a_p_slider.bind("<ButtonRelease-1>", change_detect)
        
        occluder_label = tk.Label(self, text = 'Occlusion', font = controller.allfont, bg = 'MediumOrchid2')
        occluder_spinbox = tk.Spinbox(self, command = change_detect_no_event,from_ = 0, to = 180, width = 2, increment = 1,
                                         bg = 'MediumOrchid2', textvariable = self.occluder_angle, justify = 'right',
                                         font = self.spinner_font)
        occluder_spinbox['state'] = 'disabled'
        occluder_slider = tk.Scale(self, from_ = 180, to = 0, showvalue = 0, resolution = 1,
                                      bg = 'MediumOrchid2', variable = self.occluder_angle, length = 200, sliderlength = 60, width = 20)
        occluder_slider.bind("<ButtonRelease-1>", change_detect)

        #Button setting
        plot_flow_label = tk.Label(self)
        plot_psi_label = tk.Label(self)
        
        image = Image.open(self.fillerImage)
        image = image.resize((260,220), Image.ANTIALIAS)
        photo = ImageTk.PhotoImage(image)
        plot_psi_label.configure(image=photo)
        plot_psi_label.image = photo
        
        plot_flow_label.configure(image=photo)
        plot_flow_label.image = photo
        
        #GRIDS
        stroke_vol_label.grid(row = 1, column = 0, columnspan = 3, sticky = 'nesw')
        stroke_vol_spinbox.grid(row = 2, column = 0, rowspan = 5, sticky = 'nesw')
        stroke_vol_slider.grid(row = 2, column = 1, rowspan = 5, columnspan = 2, sticky = 'nesw')
        stroke_vol_spinbox["state"] = "disabled"
        systolic_percentage_spinbox['state'] = 'disabled'
        
        heart_rate_label.grid(row = 1, column = 3, columnspan = 3, sticky = 'nesw')
        heart_rate_spinbox.grid(row = 2, column = 3, rowspan = 5, sticky = 'nesw')
        heart_rate_slider.grid(row = 2, column = 4, rowspan = 5, columnspan = 2, sticky = 'nesw')
        
        systolic_percentage_label.grid(row = 1, column = 6, columnspan = 3, sticky = 'nesw')
        systolic_percentage_spinbox.grid(row = 2, column = 6, rowspan = 5, sticky = 'nesw')
        systolic_percent_slider.grid(row = 2, column = 7, rowspan = 5, columnspan = 2, sticky = 'nesw')
        
        systole_a_p_label.grid(row = 1, column = 9, columnspan = 3, sticky = 'nesw')
        systole_a_p_spinbox.grid(row = 2, column = 9, rowspan = 5, sticky = 'nesw')
        systole_a_p_slider.grid(row = 2, column = 10, rowspan = 5, columnspan = 2, sticky = 'nesw')
        
        occluder_label.grid(row = 1, column = 12, columnspan = 3, sticky = 'nesw')
        occluder_spinbox.grid(row = 2, column = 12, rowspan = 5, sticky = 'nesw')
        occluder_slider.grid(row = 2, column = 13, rowspan = 5, columnspan = 2, sticky = 'nesw')
        
        plot_flow_label.grid(row = 1, column = 15, columnspan = 3, rowspan = 3, sticky = 'n')
        plot_psi_label.grid(row = 4, column = 15, columnspan = 3, rowspan = 3, sticky = 'n')
        
        start_stop_button.grid(row = 7, column = 0, columnspan = 3, sticky = 'nesw')
        customise_button.grid(row = 7, column = 3, columnspan = 3, sticky = 'nesw')
        return_initial.grid(row = 7, column = 6, columnspan = 3, sticky = 'nesw')
        exit_button.grid(row = 7, column = 9, columnspan = 3, sticky = 'nesw')

        for x_axis in range(15):
            for y_axis in range(7):
                tk.Grid.rowconfigure(self, y_axis, weight = 1)
            
            tk.Grid.columnconfigure(self, x_axis, weight = 1)
            
###############################################################################################
###############################################################################################
        
        #GO! >>---->
        
        #self.throttle_valve.set_angle(controller.
        set_up_pump_variables()
        self.pump.return_wave_setting()
        self.pump.initial_wave_setting()
        self.pump.step_count_setting()
        
        threading.Thread(name='Return_init_funct', target = return_initial_function).start()
        self.pump.running = False 
        #threading.Thread(target = occluder_to_position).start()
        
        if controller.get_lock_on_start() == True:
            disable_controls()
        else:
            enable_controls()
            
        r = multiprocessing.Process(target=occluder_to_position, args=())
        r.start()
      
        

##############################################################################################
        #####################################################################

class RunTests(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        #Get Defaults
        self.tube_diameter_value = controller.get_tube_diameter()
        self.length_per_revolution_value = controller.get_length_per_revolution()
        
        #MIN
        self.stroke_volume_value_MIN = controller.get_stroke_volume_value()
        self.heart_rate_value_MIN = controller.get_rate_value()
        self.systolic_percentage_MIN = controller.get_systolic_percentage_value()
        self.peak_percentage_value_MIN = controller.get_peak_percentage_value()
        self.remaining_degrees_value_MIN = controller.get_remaining_degrees()
        
        #MAX
        self.stroke_volume_value_max = controller.get_stroke_volume_value()
        self.heart_rate_value_max = controller.get_rate_value()
        self.systolic_percentage_max = controller.get_systolic_percentage_value()
        self.peak_percentage_value_max = controller.get_peak_percentage_value()
        self.remaining_degrees_value_max = controller.get_remaining_degrees()
        self.occlusion_value = controller.get_occlusion()
        print(self.occlusion_value)
        
        self.tube_diameter = tk.StringVar()
        self.tube_diameter.set(self.tube_diameter_value)
        self.length_per_revolution = tk.StringVar()
        self.length_per_revolution.set(self.length_per_revolution_value)
        self.occlusion = tk.StringVar()
        self.occlusion.set(self.occlusion_value)
        
        #MIN
        self.stroke_volume_MIN = tk.StringVar()
        self.stroke_volume_MIN.set(self.stroke_volume_value_MIN)
        self.heart_rate_MIN = tk.StringVar()
        self.heart_rate_MIN.set(self.heart_rate_value_MIN)
        self.pulse_percentage_MIN = tk.StringVar()
        self.pulse_percentage_MIN.set(self.systolic_percentage_MIN)
        self.peak_percentage_MIN = tk.StringVar()
        self.peak_percentage_MIN.set(self.peak_percentage_value_MIN)
        #MAX
        self.stroke_volume_max = tk.StringVar()
        self.stroke_volume_max.set(self.stroke_volume_value_MIN)
        self.heart_rate_max = tk.StringVar()
        self.heart_rate_max.set(self.heart_rate_value_MIN)
        self.pulse_percentage_max = tk.StringVar()
        self.pulse_percentage_max.set(self.systolic_percentage_MIN)
        self.peak_percentage_max= tk.StringVar()
        self.peak_percentage_max.set(self.peak_percentage_value_MIN)
        
        
        #Fonts
        self.spinner_font = tkfont.Font(family='Helvetica', size=20, weight='bold')
        self.label_font = tkfont.Font(family = "Times New Roman", size = 13, weight = "bold")
        
        # Run Tests
        def run_tests():
            test_dict = {}
            test_dict['tube_diameter'] = tube_diameter_slider.get()
            test_dict['length_per_rev'] = length_per_revolution_slider.get()
            test_dict['stroke_volume_MIN'] = stroke_volume_slider_MIN.get()
            test_dict['heart_rate_MIN'] = heart_rate_slider_MIN.get()
            test_dict['systolic_percentage_MIN'] = systolic_percentage_slider_MIN.get()
            test_dict['peak_percentage_MIN'] = peak_percentage_slider_MIN.get()
            test_dict['stroke_volume_MAX'] = stroke_volume_slider_MAX.get()
            test_dict['heart_rate_MAX'] = heart_rate_slider_MAX.get()
            test_dict['systolic_percentage_MAX'] = systolic_percentage_slider_MAX.get()
            test_dict['peak_percentage_MAX'] = peak_percentage_slider_MAX.get()
            test_dict['occlusion'] = occlusion_slider.get()
            
            #Input error check - 'from and 'to' values.
            if test_dict['stroke_volume_MIN'] > test_dict['stroke_volume_MAX']:
                title_label['text'] = "Stroke Volume Min must be Less Than Stroke Volume Max"
                title_label['fg'] = 'red'
            elif test_dict['heart_rate_MIN'] > test_dict['heart_rate_MAX']:
                title_label['text'] = "Heart Rate Min must be Less Than Heart Rate Max"
                title_label['fg'] = 'red'
            elif test_dict['systolic_percentage_MIN'] > test_dict['systolic_percentage_MAX']:
                title_label['text'] = "Systolic % Min must be Less Than Systolic % Max"
                title_label['fg'] = 'red'
            elif test_dict['peak_percentage_MIN'] > test_dict['peak_percentage_MAX']:
                title_label['text'] = "Peak % Min must be Less Than Peak % Max"
                title_label['fg'] = 'red'
            else:
                #Automate Tests
                controller.test_settings = test_dict.copy()
                controller.show_frame("AutomateTests")  
        
        #GUI
        title_label = tk.Label(self, text="Run Tests Page", font=self.controller.title_font)
        title_label.grid(row = 0, column = 0, columnspan = 4, sticky = 'nesw')

        #tube_diameter -----------------------------
        tube_diameter_label = tk.Label(self, text = 'Tube Diameter', font = self.label_font, bg = 'light green')
        tube_diameter_label.grid(row = 1, column = 0, columnspan = 1, sticky = 'nesw')
        
        tube_diameter_spinbox = tk.Spinbox(self,  from_ = 2, to = 50, width = 1, bg = 'light green',
                                           textvariable = self.tube_diameter, justify = 'right',
                                           font=self.spinner_font)
        tube_diameter_spinbox['state'] = 'readonly'
        tube_diameter_spinbox.grid(row = 2, column = 0, rowspan = 1, sticky = 'nesw')
            
        tube_diameter_slider = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 2, to = 50,
                                        showvalue = 0, bg = 'light green', length = 10, variable = self.tube_diameter,
                                        sliderlength = 60, width = 60)
        tube_diameter_slider.grid(row = 3, column = 0, rowspan = 1, columnspan = 1, sticky = 'nesw')
        tube_diameter_slider.set(self.tube_diameter_value)
        
        #length_per_revolution ----------------
        length_per_revolution_label = tk.Label(self, text = 'Length Per Rev (mm)', font = self.label_font, bg = 'tomato')
        length_per_revolution_label.grid(row = 1, column = 1, columnspan = 1, sticky = 'nesw')
        
        length_per_revolution_spinbox = tk.Spinbox(self,  from_ = 1, to = 20, width = 5, bg = 'tomato',
                                                   textvariable = self.length_per_revolution, justify = 'right',
                                                   font=self.spinner_font)
        length_per_revolution_spinbox['state'] = 'readonly'
        length_per_revolution_spinbox.grid(row = 2, column = 1, rowspan = 1, sticky = 'nesw')
            
        length_per_revolution_slider = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 1, to = 20,
                                                showvalue = 0, bg = 'tomato', length = 200,
                                                variable = self.length_per_revolution, sliderlength = 60, width = 60)
        length_per_revolution_slider.grid(row = 3, column = 1, rowspan = 1, columnspan = 1, sticky = 'nesw')
        length_per_revolution_slider.set(self.length_per_revolution_value)
        
        occlusion_label = tk.Label(self, text = 'Occlusion °', font = self.label_font, bg = 'MediumOrchid2')
        occlusion_label.grid(row = 1, column = 2, columnspan = 1, sticky = 'nesw')
        occlusion_spinbox = tk.Spinbox(self, from_ = 0, to = 180, width = 5, bg = 'MediumOrchid2',
                                                    textvariable = self.occlusion, justify = 'right',
                                                    font=self.spinner_font)
        occlusion_spinbox.grid(row = 2, column = 2, rowspan = 1, sticky = 'nesw')
        occlusion_slider = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 0, to = 180, showvalue = 0, bg = 'MediumOrchid2',
                                                 length = 150, variable = self.occlusion, sliderlength = 60, width = 60)
        occlusion_slider.grid(row = 3, column = 2, rowspan = 1, columnspan = 1, sticky = 'nesw')
        occlusion_slider.set(self.occlusion_value)
        
        
        minimum_value_label = tk.Label(self, text="Minimum test values - From", font=self.controller.title_font)
        minimum_value_label.grid(row = 4, column = 0, columnspan = 1, sticky = 'nesw')
        
        #MIN
        #Stroke Volume ------------------------
        stroke_volume_label_MIN = tk.Label(self, text = 'Stroke Volume', font = self.label_font, bg = 'orange')
        stroke_volume_label_MIN.grid(row = 9, column = 0, columnspan = 1, sticky = 'nesw')
        
        stroke_volume_spinbox_MIN = tk.Spinbox(self,  from_ = 1, to = 100, width = 5, bg = 'orange',
                                                    textvariable = self.stroke_volume_MIN, justify = 'right',
                                                    font=self.spinner_font)
        stroke_volume_spinbox_MIN['state'] = 'readonly'
        stroke_volume_spinbox_MIN.grid(row = 10, column = 0, rowspan = 1, sticky = 'nesw')
            
        stroke_volume_slider_MIN = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 1, to = 100, showvalue = 0, bg = 'orange',
                                                 length = 150, variable = self.stroke_volume_MIN, sliderlength = 60, width = 60)
        stroke_volume_slider_MIN.grid(row = 13, column = 0, rowspan = 1, columnspan = 1, sticky = 'nesw')
        stroke_volume_slider_MIN.set(self.stroke_volume_value_MIN)     
        
        #heart_rate_value
        heart_rate_label_MIN = tk.Label(self, text = 'Heart Rate', font = self.label_font, bg = 'pink')
        heart_rate_label_MIN.grid(row = 9, column = 1, columnspan = 1, sticky = 'nesw')
        
        heart_rate_spinbox_MIN = tk.Spinbox(self,  from_ = 30, to = 120, width = 5, bg = 'pink',
                                                    textvariable = self.heart_rate_MIN, justify = 'right',
                                                    font=self.spinner_font)
        heart_rate_spinbox_MIN['state'] = 'readonly'
        heart_rate_spinbox_MIN.grid(row = 10, column = 1, rowspan = 1, sticky = 'nesw')
            
        heart_rate_slider_MIN = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 30, to = 120, showvalue = 0, bg = 'pink',
                                                 length = 150, variable = self.heart_rate_MIN, sliderlength = 60, width = 60)
        heart_rate_slider_MIN.grid(row = 13, column = 1, rowspan = 1, columnspan = 1, sticky = 'nesw')
        heart_rate_slider_MIN.set(self.heart_rate_value_MIN)
        
        #systolic_percentage --------------------------
        systolic_percentage_label_MIN = tk.Label(self, text = 'Systolic Percentage', font = self.label_font, bg = 'skyblue1')
        systolic_percentage_label_MIN.grid(row = 9, column = 2, columnspan = 1, sticky = 'nesw')
        
        systolic_percentage_spinbox_MIN = tk.Spinbox(self,  from_ = 20, to = 80, increment = 10, width = 5, bg = 'skyblue1',
                                                    textvariable = self.pulse_percentage_MIN, justify = 'right',
                                                    font=self.spinner_font)
        systolic_percentage_spinbox_MIN['state'] = 'readonly'
        systolic_percentage_spinbox_MIN.grid(row = 10, column = 2, rowspan = 1, sticky = 'nesw')
            
        systolic_percentage_slider_MIN = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 20, to = 80,resolution = 10,showvalue = 0, bg = 'skyblue1',
                                                 length = 150, variable = self.pulse_percentage_MIN, sliderlength = 60, width = 60)
        systolic_percentage_slider_MIN.grid(row = 13, column = 2, rowspan = 1, columnspan = 1, sticky = 'nesw')
        systolic_percentage_slider_MIN.set(self.systolic_percentage_MIN)
        
        #peak_percentage --------------------------
        peak_percentage_label_MIN = tk.Label(self, text = 'Peak Percentage', font = self.label_font, bg = 'yellow')
        peak_percentage_label_MIN.grid(row = 9, column = 3, columnspan = 1, sticky = 'nesw')
        
        peak_percentage_spinbox_MIN = tk.Spinbox(self,  from_ = 20, to = 80, increment = 10, width = 5, bg = 'yellow',
                                                    textvariable = self.peak_percentage_MIN, justify = 'right',
                                                    font=self.spinner_font)
        peak_percentage_spinbox_MIN['state'] = 'readonly'
        peak_percentage_spinbox_MIN.grid(row = 10, column = 3, rowspan = 1, sticky = 'nesw')
            
        peak_percentage_slider_MIN = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 20, to = 80, resolution = 10, showvalue = 0, bg = 'yellow',
                                                 length = 150, variable = self.peak_percentage_MIN, sliderlength = 60, width = 60)
        peak_percentage_slider_MIN.grid(row = 13, column = 3, rowspan = 1, columnspan = 1, sticky = 'nesw')
        peak_percentage_slider_MIN.set(self.peak_percentage_value_MIN)
        
        
        maximum_value_label = tk.Label(self, text="Maximum test values - To", font=self.controller.title_font)
        maximum_value_label.grid(row = 14, column = 0, columnspan = 1, sticky = 'nesw')
        
        #MAX
        #Stroke Volume ------------------------
        stroke_volume_label_MAX = tk.Label(self, text = 'Stroke Volume', font = self.label_font, bg = 'orange')
        stroke_volume_label_MAX.grid(row = 15, column = 0, columnspan = 1, sticky = 'nesw')
        
        stroke_volume_spinbox_MAX = tk.Spinbox(self,  from_ = 1, to = 100, width = 5, bg = 'orange',
                                                    textvariable = self.stroke_volume_max, justify = 'right',
                                                    font=self.spinner_font)
        stroke_volume_spinbox_MAX['state'] = 'readonly'
        stroke_volume_spinbox_MAX.grid(row = 18, column = 0, rowspan = 1, sticky = 'nesw')
            
        stroke_volume_slider_MAX = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 1, to = 100, showvalue = 0, bg = 'orange',
                                                 length = 150, variable = self.stroke_volume_max, sliderlength = 60, width = 60)
        stroke_volume_slider_MAX.grid(row = 19, column = 0, rowspan = 1, columnspan = 1, sticky = 'nesw')
        stroke_volume_slider_MAX.set(self.stroke_volume_value_MIN)     
        
        #heart_rate_value
        heart_rate_label_MAX = tk.Label(self, text = 'Heart Rate', font = self.label_font, bg = 'pink')
        heart_rate_label_MAX.grid(row = 15, column = 1, columnspan = 1, sticky = 'nesw')
        
        heart_rate_spinbox_MAX = tk.Spinbox(self,  from_ = 30, to = 120, width = 5, bg = 'pink',
                                                    textvariable = self.heart_rate_max, justify = 'right',
                                                    font=self.spinner_font)
        heart_rate_spinbox_MAX['state'] = 'readonly'
        heart_rate_spinbox_MAX.grid(row = 18, column = 1, rowspan = 1, sticky = 'nesw')
            
        heart_rate_slider_MAX = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 30, to = 120, showvalue = 0, bg = 'pink',
                                                 length = 150, variable = self.heart_rate_max, sliderlength = 60, width = 60)
        heart_rate_slider_MAX.grid(row = 19, column = 1, rowspan = 1, columnspan = 1, sticky = 'nesw')
        heart_rate_slider_MAX.set(self.heart_rate_value_MIN)
        
        #systolic_percentage --------------------------
        systolic_percentage_label_MAX = tk.Label(self, text = 'Systolic Percentage', font = self.label_font, bg = 'skyblue1')
        systolic_percentage_label_MAX.grid(row = 15, column = 2, columnspan = 1, sticky = 'nesw')
        
        systolic_percentage_spinbox_MAX = tk.Spinbox(self,  from_ = 20, to = 80, increment = 10, width = 5, bg = 'skyblue1',
                                                    textvariable = self.pulse_percentage_max, justify = 'right',
                                                    font=self.spinner_font)
        systolic_percentage_spinbox_MAX['state'] = 'readonly'
        systolic_percentage_spinbox_MAX.grid(row = 18, column = 2, rowspan = 1, sticky = 'nesw')
            
        systolic_percentage_slider_MAX = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 20, to = 80,resolution = 10,showvalue = 0, bg = 'skyblue1',
                                                 length = 150, variable = self.pulse_percentage_max, sliderlength = 60, width = 60)
        systolic_percentage_slider_MAX.grid(row = 19, column = 2, rowspan = 1, columnspan = 1, sticky = 'nesw')
        systolic_percentage_slider_MAX.set(self.systolic_percentage_MIN)
        
        #peak_percentage --------------------------
        peak_percentage_label_MAX = tk.Label(self, text = 'Peak Percentage', font = self.label_font, bg = 'yellow')
        peak_percentage_label_MAX.grid(row = 15, column = 3, columnspan = 1, sticky = 'nesw')
        
        peak_percentage_spinbox_MAX = tk.Spinbox(self,  from_ = 20, to = 80, increment = 10, width = 5, bg = 'yellow',
                                                    textvariable = self.peak_percentage_max, justify = 'right',
                                                    font=self.spinner_font)
        peak_percentage_spinbox_MAX['state'] = 'readonly'
        peak_percentage_spinbox_MAX.grid(row = 18, column = 3, rowspan = 1, sticky = 'nesw')
            
        peak_percentage_slider_MAX = tk.Scale(self, orient=tk.HORIZONTAL, from_ = 20, to = 80, resolution = 10, showvalue = 0, bg = 'yellow',
                                                 length = 150, variable = self.peak_percentage_max, sliderlength = 60, width = 60)
        peak_percentage_slider_MAX.grid(row = 19, column = 3, rowspan = 1, columnspan = 1, sticky = 'nesw')
        peak_percentage_slider_MAX.set(self.peak_percentage_value_MIN)
        
        exit_button = tk.Button(self, text="Exit",
                           command=lambda: controller.show_frame("MainMenu"),
                           bg= 'green')
        exit_button.grid(row = 3, column = 3, columnspan = 1, sticky = 'nesw')
        
        run_tests_button = tk.Button(self, text="Run Tests",
                           command=run_tests,bg= 'red')
        run_tests_button.grid(row = 2, column = 3, columnspan = 1, sticky = 'nesw')
        
        
class AutomateTests(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.label_font = tkfont.Font(family = "Times New Roman", size = 18, weight = "bold")
        self.title_font = tkfont.Font(family='Droid Sans', size=25, weight="bold")
        self.data_font = tkfont.Font(family='Droid Sans', size=14, weight="bold")
        
        self.stroke_volume = 0
        self.heart_rate = 0
        self.systolic_percentage = 0
        self.peak_percentage = 0

        self.psi_xs = []
        self.psi_ys = []
        self.flow_xs = []
        self.flow_ys = []
        
        self.test_number = 1
        
        self.dataFilename = ''
        self.first_run = False
        self.test_pump_exists = False
        
        #Exit Frame
        #Kill pump if exits
        #Update GUI for reopening of Frame
        def exit_it():
            #If pump exists: stop it then kill it.         
            if self.test_pump_exists:
                self.test_pump_exists = False
                #self.test_pump.start_stop_function()
                self.test_pump.pi.wave_tx_stop()
                self.test_pump.pi.wave_clear()
                self.test_pump.pi.stop()         
                del self.test_pump
                
            exit_button['state'] = 'normal'
            remaining_time_label['text'] = 'Remaining Time: '
            remaining_tests_label['text'] = 'Remaining Tests: '
            test_number_label['text'] = 'Test: '
            feed_back_label['text'] = 'Pending'
            feed_back_label['fg'] = 'red'
            current_stroke_volume_label['text'] = '0'
            current_heart_rate_label['text'] = '0'
            current_systolic_percentage_label['text'] = '0'
            current_peak_percentage_label['text'] = '0'        
            controller.show_frame("RunTests")
            #controller.show_frame("MainMenu")
            #controller.destroy()
            
        #Update GUI
        #Call Process - THREAD
        def threadit():
            self.test_number = 1
            process_button['state'] = 'disabled'
            exit_button['state'] = 'disabled'
            abort_button['state'] = 'normal'
            threading.Thread(target=process1).start()
            
        #Update GUI
        #Call get sensor data Multiprocess
        def get_sensor_data():
            test_number_label['text'] = "Test: " + str(self.test_number)
            self.remaining_tests = int(self.total_tests) - 1
            remaining_tests_label['text'] = "Remaining Tests: " + str(self.remaining_tests)
            self.total_time = (((self.total_tests * 3) / 60) / 60 ) / 24
            
            if self.total_time < 1:
                self.total_time = self.total_time * 24 #days to hours
                if self.total_time < 1:
                    self.total_time = self.total_time * 60 #hours to minutes
                    
                    if self.total_time < 1:
                        self.total_time = self.total_time * 60 #minutes to seconds
                        #print("total seconds = ", self.total_time)
                        remaining_time_label['text'] = "Remaining seconds: " + str(int(self.total_time))
                    
                    else:
                        #print("total minutes = ", self.total_time)
                        remaining_time_label['text'] = "Remaining Minutes: " + str(round(self.total_time,2))
                else:
                    #print("total hours = ", self.total_time)
                    remaining_time_label['text'] = "Remaining Hours: " + str(round(self.total_time,2))
            else:
                #print("total days = ", self.total_time)
                remaining_time_label['text'] = "Remaining Days: " + str(round(self.total_time,2))
                       
            first = multiprocessing.Process(target=collect_data, args=())
            first.start()
            first.join()
            self.test_number += 1
            #self.remaining_tests -= 1
            self.total_tests -= 1
            
            
        #Get Sensor Data
        #Write data into CSV
        def collect_data():
            self.psi_xs, self.psi_ys, self.flow_xs, self.flow_ys = self.sensors.get_sensor_values()
            self.throttle_valve_setting = controller.get_occlusion()
            #print(self.psi_ys)
  #add_data_to_csv(self, fileName, Tube_Diameter, Length_Per_Rev, Stroke_Volume, Heart_Rate, Systolic_Percentage, Peak_Percentage, Index, PSI, Flow, )
            for result in range(len(self.psi_xs)):
                
                self.csv_writer.add_data_to_csv(self.dataFilename,
                                                self.controller.test_settings['tube_diameter'],
                                                self.controller.test_settings['length_per_rev'],
                                                self.test_pump.volume_value,
                                                self.test_pump.rate_value,
                                                self.test_pump.systolic_percentage_value,
                                                self.test_pump.peak_percentage_value,
                                                self.psi_xs[result],
                                                self.psi_ys[result],
                                                self.flow_ys[result],
                                                self.throttle_valve_setting)
            
        
        def process1():   
            self.test_pump_exists = True
            self.servo_gpio = 12 # PIN 32 = GPIO 12
            
            #Create Pump instance
            self.test_pump = Pump(17,27,5,20,controller.get_pulse_per_revolution(),self.controller.test_settings['length_per_rev'],
                             self.controller.test_settings['tube_diameter'], controller.get_remaining_degrees())
            #Create Servo Instance
            self.throttle_valve = Occluder(self.servo_gpio,600,2300)
            self.throttle_valve.set_angle(self.controller.test_settings['occlusion'])
            
            #CSV Writer Instance
            self.csv_writer = CsvWriter()
            #Create Unique File Name and CSV file with headers
            self.dataFilename = 'testdata' + datetime.now().strftime('%H%M%S%f%d%m%Y') + '.csv'
            self.csv_writer.create_csv_file_and_header(self.dataFilename)
            
            #Create Sensor Instances
            self.maxPSI = 10
            self.sensors = PumpSensor(self.maxPSI)
            
            #GO! >>---->
            #Get values from controller class
            self.stroke_volume_min = self.controller.test_settings['stroke_volume_MIN']
            self.heart_rate_min = self.controller.test_settings['heart_rate_MIN']
            self.systolic_percentage_min  = self.controller.test_settings['systolic_percentage_MIN']
            self.peak_percentage_min  = self.controller.test_settings['peak_percentage_MIN']
            self.stroke_volume_max = self.controller.test_settings['stroke_volume_MAX']
            self.heart_rate_max = self.controller.test_settings['heart_rate_MAX']
            self.systolic_percentage_max  = self.controller.test_settings['systolic_percentage_MAX']
            self.peak_percentage_max  = self.controller.test_settings['peak_percentage_MAX']
            
            #Total tests vars
            self.strokeVolNums = (self.controller.test_settings['stroke_volume_MAX'] - self.controller.test_settings['stroke_volume_MIN']) + 1
            self.hearRateNums = (self.controller.test_settings['heart_rate_MAX'] - self.controller.test_settings['heart_rate_MIN']) + 1
            self.sytoleNums = ((self.controller.test_settings['systolic_percentage_MAX'] - self.controller.test_settings['systolic_percentage_MIN']) / 10) + 1 
            self.peakNums = ((self.controller.test_settings['peak_percentage_MAX'] - self.controller.test_settings['peak_percentage_MIN']) / 10) + 1
            self.total_tests = self.strokeVolNums * self.hearRateNums * self.sytoleNums * self.peakNums
            
            #Set up pump                
            self.test_pump.volume_value = self.stroke_volume_min
            self.test_pump.rate_value = self.heart_rate_min 
            self.test_pump.systolic_percentage_value = self.systolic_percentage_min
            self.test_pump.peak_percentage_value = self.peak_percentage_min 
            #Pump - Initial Start
            self.test_pump.return_wave_setting()
            self.test_pump.initial_wave_setting()
            self.test_pump.step_count_setting()
            self.test_pump.return_initial_function() # Zero pump drive
            time.sleep(1)
            self.test_pump.return_initial_function()
            time.sleep(1)
            self.test_pump .running = False
            #Start Pump - Thread!
            threading.Thread(name='Pump_start_stop_function', target=self.test_pump.start_stop_function).start()
            #Loop through test values
            for i in range(self.stroke_volume_min, self.stroke_volume_max + 1):
                feed_back_label['text'] = "Running Tests"                
                current_stroke_volume_label['text'] = str(i)
                current_stroke_volume_label.config(text = str(i))
                self.test_pump.volume_value = i
                #time.sleep(0.5)
                  
                for j in range(self.heart_rate_min , self.heart_rate_max + 1):
                    current_heart_rate_label['text'] = str(j)
                    current_heart_rate_label.config(text = str(j))
                    self.test_pump.rate_value = j
                    #time.sleep(0.5)
                    
                    for k in range(self.systolic_percentage_min, self.systolic_percentage_max + 10, 10):
                        current_systolic_percentage_label['text'] = str(k)
                        current_systolic_percentage_label.config(text = str(k))
                        self.test_pump.systolic_percentage_value = k
                        #time.sleep(0.5)
                        
                        for m in range(self.peak_percentage_min, self.peak_percentage_max + 10, 10):
                            current_peak_percentage_label['text'] = str(m)
                            current_peak_percentage_label.config(text = str(m))
                            self.test_pump.peak_percentage_value = m
                            #Tell pump to change settings
                            self.test_pump.condition_change = 1
                            #Wait for pump to finish new settings computations.
                            self.test_pump.i_made_new_data = False
                            while self.test_pump.i_made_new_data == False: #Wait for pump to finish computations
                                time.sleep(0.01) #Save porcessing power
                            #Then get sensor data
                            threading.Thread(target=get_sensor_data).start()  #Get sensor data  
                            time.sleep(3) #ZzzzzZ
                       
            #Tests Complete: Stop Pump, Reset GUI.               
            threading.Thread(name='Pump_start_stop_function', target=self.test_pump.start_stop_function).start()
            feed_back_label['text'] = "Tests Complete"
            feed_back_label['fg'] = 'green'
            remaining_time_label['text'] = "Remaining seconds: 0"
            remaining_tests_label['text'] = "Remaining Tests: 0"
            process_button['state'] = 'normal'
            exit_button['state'] = 'normal'
            abort_button['state'] = 'disabled'
        
        # Abort Tests - Will cause exit
        def abort():
            self.test_pump.pi.wave_tx_stop()
            self.test_pump.pi.wave_clear()
            self.test_pump.pi.stop()
            self.destroy()
            controller.destroy()
        
        #Lay out variables
        self.title_row = 0
        self.variable_name_row = 1
        self.variable_value_row = 2
        self.sep1_row = 3
        self.status_title = 4
        self.sep2_row = 5
        self.info_bar_row = 6
        self.test_number_row = 6
        self.remaining_test_row = 7
        self.remaining_time_row = 8
        self.process_button_row = 9
        self.exit_button_row = 10
        self.abort_button_row = 11
        
        #GUI
        label = tk.Label(self, text="Testing", font=self.title_font, fg = 'green')
        label.grid(row = self.title_row, column = 0, columnspan = 8, sticky = 'ew')
        
        stroke_volume_label = tk.Label(self, text = '  Stroke Volume  ', font = self.label_font, bg = 'orange')
        stroke_volume_label.grid(row = self.variable_name_row, column = 0, columnspan = 2, sticky = 'ew')
        
        current_stroke_volume_label = tk.Label(self, text = 0, font = self.label_font, bg = 'orange')
        current_stroke_volume_label.grid(row = self.variable_value_row, column = 0, columnspan = 2, sticky = 'ew')
        
        heart_rate_label = tk.Label(self, text = '       Heart Rate      ', font = self.label_font, bg = 'pink')
        heart_rate_label.grid(row = self.variable_name_row, column = 2, columnspan = 2, sticky = 'ew')
        
        current_heart_rate_label = tk.Label(self, text = 0, font = self.label_font, bg = 'pink')
        current_heart_rate_label.grid(row = self.variable_value_row, column = 2, columnspan = 2, sticky = 'ew')
        
        systolic_percentage_label = tk.Label(self, text = ' Systolic Percentage ', font = self.label_font, bg = 'skyblue1')
        systolic_percentage_label.grid(row = self.variable_name_row, column = 4, columnspan = 2, sticky = 'ew')
        
        current_systolic_percentage_label = tk.Label(self, text = 0, font = self.label_font, bg = 'skyblue1')
        current_systolic_percentage_label.grid(row = self.variable_value_row, column = 4, columnspan = 2, sticky = 'ew')
        
        peak_percentage_label = tk.Label(self, text = ' Peak Percentage ', font = self.label_font, bg = 'yellow')
        peak_percentage_label.grid(row = self.variable_name_row, column = 6, columnspan = 2, sticky = 'ew')
        
        current_peak_percentage_label = tk.Label(self, text = 0, font = self.label_font, bg = 'yellow')
        current_peak_percentage_label.grid(row = self.variable_value_row, column = 6, columnspan = 2, sticky = 'ew')
        
        feed_back_label = tk.Label(self, text="Pending", font=self.data_font, fg = 'red')
        feed_back_label.grid(row = self.info_bar_row, column = 0, columnspan = 4, sticky = 'w')
        
        remaining_tests_label = tk.Label(self, text="Remaining Tests: ", font=self.data_font, fg = 'green')
        remaining_tests_label.grid(row = self.remaining_test_row, column = 3, columnspan = 4, sticky = 'w')
        
        remaining_time_label = tk.Label(self, text="Remaining Time: ", font=self.data_font, fg = 'green')
        remaining_time_label.grid(row = self.remaining_time_row, column = 3, columnspan = 4, sticky = 'w')
        
        process_button = tk.Button(self, text="Process",
                           command=threadit)
        process_button.grid(row = self.process_button_row, column = 0, columnspan = 2, sticky = 'nesw')
        
        exit_button = tk.Button(self, text="Exit",
                           command=exit_it)
        exit_button.grid(row = self.exit_button_row, column = 0, columnspan = 2, sticky = 'nesw')
        exit_button['state'] = 'normal'
        
        test_number_label = tk.Label(self, text="Test: ", font=self.data_font, fg = 'green')
        test_number_label.grid(row = self.test_number_row, column = 3, columnspan = 1, sticky = 'w')
        
        abort_button = tk.Button(self, text="Abort", bg = 'red',command=abort)
        abort_button.grid(row = self.abort_button_row, column = 0, columnspan = 2, sticky = 'ew')
        abort_button['state'] = 'disabled'
        
        #label2 = tk.Label(self, text="", font=self.data_font, fg = 'green')
        #label2.grid(row =self.sep1_row, column = 0, columnspan = 8, sticky = 'ew')
        
        sep1 = ttk.Separator(self).grid(row=13, column=0, columnspan=8,sticky=('ew'))
        status_label = tk.Label(self, text="Status", font=self.data_font, fg = 'green')
        status_label.grid(row = self.status_title, column = 0, columnspan = 4, sticky = 'w')
        sep2 = ttk.Separator(self).grid(row=self.sep2_row, column=0, columnspan=8,sticky=('ew'))
        sep3 = ttk.Separator(self,orient='vertical').grid(row=5, column=2, rowspan=10,sticky=('ns'))
        

if __name__ == "__main__":
    app = TriphasicApp()
    app.mainloop()
