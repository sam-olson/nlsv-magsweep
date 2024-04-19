# Lakeshore Probe Station Control Software
A Python GUI for remotely controlling magnetic probe station equipment via GPIB. 

The main use case for this software is for acquiring current and voltage measurements while sweeping a parallel-plane magnetic field, which is a standard measurement for analysis of non-local spin valves. 

![gui](https://github.com/sam-olson/nlsv-magsweep/blob/main/assets/GUI_interface.JPG)


## Select Features
- User-friendly GUI with asynchronous functionality
- Live updating plots during data collection
- Instrument connection status indicators
- Automatic data export upon sweep completion

## Default Instruments Used
The following instruments are currently supported out of the box: 
- Keithley 6221 DC and AC Current Source
- Stanford Research Systems SR850 Lock-In Amplifier
- Agilent B1500A Semiconductor Parameter Analyzer
- Lakeshore 475 DSP Gaussmeter
- Lakeshore 642 Electromagnet Power Supply

![instruments](https://github.com/sam-olson/nlsv-magsweep/blob/main/assets/instruments.png)
*a) Agilent B1500A, b) Lakeshore magnetic test equipment, c) Stanford Research Systems SR850, d) Keithley 6221, e) Lakeshore magnetic probe station*

## Software Setup
### Installation
This software requires that [Python3](https://www.python.org/) is installed on your machine. The software also requires some third-party packages that must be installed prior to usage. The packages are listed in the `requirements.txt` file. To install these packages, navigate to the directory where you downloaded this repository and run the following command (on a Unix-based system):
```bash
python3 -m pip install -r requirements.txt
```

Or on a Windows system:
```bash
py -m pip install -r requirements.txt
```

### Editing GPIB Instruments
It is relatively easy to add a new instrument for use in the GUI. Simply add a new object representing the instrument in `instruments.py` with the appropriate SCPI commands represented as object methods. This object can then be referenced and called from the GUI.

The GPIB addresses of the instruments and the path to your VISA backend should be set in `config.json` prior to launching the GUI. 

## Hardware Setup
All instruments should be connected via GPIB to the host computer and switched on before launching the GUI.

## GUI Fields
- **Save Folder**: The folder to which all data will be saved (with a timestamp). This folder can be selected with the adjacent button.
- **Device row**: Device array row number of the device under test.
- **Device col**: Device array column number of the device under test.
- **Injector**: Used to specify which injector electrode is being used in multi-injector device tests. 
- **Det. Angle**: Angle of detector electrode. 
- **Det. Distance**: Distance of detector electrode from injector electrode.
- **Notes**: A text box in which the user can write notes about the current device under test.
- **Frequency**: Sets the carrier wave frequency of the injected AC current. 
- **Current (uA)**: Sets the current amplitude in microamps.
- **Backgate Voltage**: Sets the backgate voltage supplied to the probe station stage (supplied by the semiconductor parameter analyzer).
- **Sweep Lower Limit (A)**: The lower current limit supplied to the magnet for generating the magnetic field. On this probe station, the magnetic field in Gauss is proportional to ~100x the current supplied in amps.
- **Sweep Upper Limit (A)**: The upper current limit supplied to the magnet for generating the magnetic field.
- **Sweep Step (A)**: Amount to change the current by for each data point.
- **Sweep both ways?**: If checked, the software will sweep the magnetic field from negative -> positive and back from positive -> negative. If unchecked, the software will only sweep from negative -> positive.
- **Delay (sec)**: The amount of time, in seconds, to delay between each datapoint to allow the magnetic field to equilibrate.
- **Runs per**: The number of runs to repeat with these parameters.

## Measurement of Non-Local Spin Valves (NLSVs) - Theoretical Background
NLSVs are devices that can be used to determine the spintronic properties of a material. Ferromagnetic electrodes are used to inject a spin-polarized current into a material. This spin polarized current then traverses the material and is detected by a set of reference electrodes as a voltage. This voltage can then be converted to a resistance using Ohm's law, which is then termed the non-local resistance. 

![nlsv](https://github.com/sam-olson/nlsv-magsweep/blob/main/assets/NLSV_schematic.png)
*Schematic of a graphene-channel NLSV*

An external magnetic field parallel to the electrodes is swept from high negative field to high positive field, causing the electrode material to switch its magnetization direction, and so switch the direction of the injected spin-polarized electrons. The injector and detector electrodes are made to have different widths and so different magnetic coercivities. This results in the injector and detector electrodes briefly being anti-parallel in their magnetic alignment to one another. This causes the non-local resistance to change, and the magnitude of this change is termed the non-local spin signal. The larger the spin signal, the higher the amount of spin-polarized current reaching the detector electrodes. For practical devices, it is desired that such spin-polarized currents can traverse relatively large distances without depolarizing, a metric known as the material's "spin diffusion length".

The benefits of spintronic devices in logic or memory storage applications is that they tend to be faster-switching and less power-hungry than their electronic counterparts. My research focuses specifically on NLSVs that have graphene as a channel material due to its inherently long spin diffusion length, although NLSVs with other channel materials exist.  
