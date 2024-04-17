import time

class Kth6221:
    def __init__(self, rm, addr):
        """
        Class that allows for interfacing with Keithley 6221 DC/AC current source

        Parameters
        ----------
        rm: VISA resource manager
        addr: address of the instrument in your GPIB network
        """
        self.rm = rm
        self.addr = addr
        self.instr = self.rm.open_resource(self.addr)
        self.set_wave_freq()
        self.start_up()

    def start_up(self):
        self.set_output_low()
        self.set_curr_comp()
        self.set_wave_func()
        self.set_wave_ampl()
        self.set_wave_freq()
        

    def set_output_low(self, value=1):
        """
        Sets output low mode. If value == 1 -> output low is tied to
          Earth ground, if the value is 0 the output low is set to the internal
          floating ground
        """
        self.instr.write(f":OUTP:LTE {value}\r")

    def get_curr_comp(self):
        """
        Queries the instrument for the current compliance
        """
        return self.instr.query(":SOUR:CURR:COMP?")

    def set_curr_comp(self, value=5):
        """
        Sets the current compliance of the instrument to the provided value
        """
        self.instr.write(f":SOUR:CURR:COMP {value}\r")

    def get_wave_func(self):
        """
        Queries the instrument for current wave function
        """
        return self.instr.query(":SOUR:WAVE:FUNC?")

    def set_wave_func(self, value="SIN"):
        """
        Sets current wave function to provided value
        Acceptable values: SIN (sinusoid), SQU (square), RAMP (ramp), ARB{X}
        (arbitrary, where X is between 0 and 4)
        """
        self.instr.write(f":SOUR:WAVE:FUNC {value}\r")

    def get_wave_ampl(self):
        """
        Queries instrument for current wave function amplitude
        """
        return self.instr.query(":SOUR:WAVE:AMPL?")

    def set_wave_ampl(self, value=1e-6):
        """
        Sets current wave function amplitude
        """
        self.instr.write(f":SOUR:WAVE:AMPL {value}\r")

    def get_wave_freq(self):
        """
        Queries instrument for current wave function frequency
        """
        return self.instr.query(":SOUR:WAVE:FREQ?")

    def set_wave_freq(self, value=13):
        """
        Sets current wave function frequency to provided value (in Hertz)
        """
        self.instr.write(f":SOUR:WAVE:FREQ {value}\r")

    def start_output(self, tslp=2):
        """
        Enables current output
        tslp: number of seconds between arming and initiating output
        """
        self.instr.write(":SOUR:WAVE:ARM\r")
        time.sleep(tslp)
        self.instr.write(":SOUR:WAVE:INIT\r")
        
    def stop_output(self):
        """
        Disables current output
        """
        self.instr.write(":SOUR:WAVE:ABOR\r")

class SR850:
    def __init__(self, rm, addr):
        """
        Class that allows for interfacing with SR850 lock-in amplifier

        Parameters
        ----------
        rm: VISA resource manager
        addr: address of the instrument in your GPIB network
        """
        self.rm = rm
        self.addr = addr
        self.instr = self.rm.open_resource(self.addr)
        self.auto_gain()

    def data_point(self):
        """
        Queries the instrument to obtain a data point. Returns the data
          in a dictionary
        X: x-axis projection of signal
        Y: y-axis projection of signal
        R: radius (magnitude) of signal
        T: theta (phase angle)

        Note that X = R*COS(T), Y = R*SIN(T), and X^2 + Y^2 = R^2
        """
        return {"X": float(self.instr.query("OUTP? 1")),
                "Y": float(self.instr.query("OUTP? 2")),
                "R": float(self.instr.query("OUTP? 3")),
                "T": float(self.instr.query("OUTP? 4"))}

    def auto_gain(self):
        """
        Runs auto-gain function on instrument
        """
        self.instr.write("AGAN\r")

    def auto_phase(self):
        """
        Runs auto-phase function on instrument
        """
        self.instr.write("APHS\r")

class LS475:
    def __init__(self, rm, addr):
        """
        Class that allows for interfacing with Lakeshore 475 Gaussmeter

        Parameters
        ----------
        rm: VISA resource manager
        addr: address of the instrument in your GPIB network
        """
        self.rm = rm
        self.addr = addr
        self.instr = self.rm.open_resource(self.addr)

    def get_field_reading(self):
        """
        Queries the instrument for the current magnetic field reading (in Gauss)
        """
        return float(self.instr.query("RDGFIELD?"))

    def get_temp_reading(self):
        """
        Queries the instrument for the current temperature reading (in Celsius)
        """
        return float(self.instr.query("RDGTEMP?"))

class LS642:
    def __init__(self, rm, addr):
        """
        Class that allows for interfacing with Lakeshore 642 magnet
          power supply

        Parameters
        ----------
        rm: VISA resource manager
        addr: address of the instrument in your GPIB network
        """
        self.rm = rm
        self.addr = addr
        self.instr = self.rm.open_resource(self.addr)

    def get_current(self):
        """
        Queries instrument for current (amps)
        """
        return self.instr.query("RDGI?")

    def get_setpoint(self):
        """
        Queries instrument for current setpoint (amps)
        """
        return self.instr.query("SETI?")

    def get_voltage(self):
        """
        Queries instrument for voltage (volts)
        """
        return self.instr.query("RDGV?")

    def set_current(self, value):
        """
        Sets instrument current output (amps)
        """
        self.instr.write(f"SETI {value}\r")

    def stop(self):
        self.instr.write("STOP\r")

class B1500A:
    def __init__(self, rm, addr):
        """
        Class that allows for interfacing with Agilent (Keysight) B1500A
          Semiconductor Parameter Analyzer (SPA)

        Parameters
        ----------
        rm: VISA resource manager
        addr: address of the instrument in your GPIB network
        """

        self.rm = rm
        self.addr = addr
        self.instr = self.rm.open_resource(self.addr)

    def set_voltage(self, value, smu=3):
        """
        Sets voltage of SMU to a given value
        
        Parameters
        ----------
        value: voltage level to set SMU to
        smu: number of SMU whose voltage you are setting (default to 3 for our setup's backgate probe)
        """
        
        self.instr.write(f"DV {smu},0,{value}")

    def disconnect_smu(self, smu=3):
        """
        Disconnects provided SMU to ensure voltage is shutoff

        Parameters
        ----------
        smu: number of SMU to disconnect (default to 3 for our setup's backgate probe)
        """

        self.instr.write(f"CL {smu}")

    def connect_smu(self, smu=3):
        """
        Re-connects provided SMU (must be done after disconnecting prior to setting voltage)

        Parameters
        ----------
        smu: number of SMU to connect (default to 3 for our setup's backgate probe)
        """

        self.instr.write(f"CN {smu}")
        
