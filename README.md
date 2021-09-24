# Triphasic :heart:
### Triphasic Heart Pump Work - For Albert Chong.  
This is an application that uses Python, Raspberry Pi, Stepper Motors, Sensors etc to create a specialised heart pump. Class Based.  
Triphasic.py contains a Pump (closed loop stepper motor control) class, a Occluder (servo) class, and a sensor (PSI and Flow) class and basic CSV writer.  
The pump class is most likely to specialised for any reuse but features the use of sin waves for acceleration control.  
The Occluder class can be used for any pulse width servo.  
The sensor class could be used for PSI applications. Requires ADS1115 and 5 to 10 psi sensor - 0v to 5v output.  
Unfortunatly the flow sensor is a expensive ultra sonic machine used for calibration and testing. It just outputs a voltage 0 to 5 volts.  
The GUI is Tkinter based and the app is menu driven.  
  
  
MINIMUM SETUP! (Raspberry Pi (4 recomended) OS -> Rapbian) 
               (ADS1115 ADC on I2C BUS, will throw error without)
1.   
Open a command line on the Raspberry Pi and paste or write in:  
"pip3 install Adafruit-Blinka"  
2.  
When that completes, type in:  
"sudo pip3 install adafruit-circuitpython-ads1x15"  
3.  
PIGPIO lib was already installed on Rasp  
if not  
"pip3 install pigpio"  
4.  
Install matplotlib   
"pip install matplotlib"   
5.   
Then download this repository.  
Create a folder to download into.  
ie.  
"mkdir githubDownload"  
cd into it  
ie.  
"cd ./githubDownload/"  

Then enter  
"git clone https://github.com/MarkJoyce0111/Triphasic"  
6.  
Setup peripherals  
type in  
"sudo raspi-config"  
Select Interface Options (3)  
Then enable I2C   
7.    
Run Code  
"python3 TriphasicData_1.py"  
