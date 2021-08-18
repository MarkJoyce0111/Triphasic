# Triphasic
Triphasic Heart Pump Work - For Albert Chong.
This is an application that uses Python, Raspberry Pi, Stepper Motors, Sensors etc to create a specialised heart pump. Class Based.
Triphasic.py contains a Pump (closed loop stepper motor control) class, a Occluder (servo) class, and a sensor (PSI and Flow) class.
The pump class is most likely to specialised for any reuse but features the use of sin waves for acceleration control.
The Occluder class can be used for any pulse width servo.
The sensor class could be used for PSI applications. Requires ADS1115 and 5 to 10 psi sensor - 0v to 5v output. 
Unfortunatly the flow sensor is a expensive ultra sonic machine used for calibration and testing. It just outputs a voltage 0 to 5 volts.
The GUI is Tkinter based and the app is menu driven.
