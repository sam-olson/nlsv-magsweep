import asyncio
import datetime
import json
import os
from queue import Queue
import random
import sys
import threading
import time

import tkinter as tk
from tkinter import filedialog as fd
from tkinter import messagebox

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import numpy as np
import pandas as pd
import pyvisa as visa

from .config import COLORS, CURRENT_LIMIT, FREQ_LIMIT
from .instruments import *
from .utils import parse_entry

def auto_update_entry(entry, value):
    """
    Programatically inserts given value into tkinter entry box

    Parameters
    ----------
    entry: tkinter Entry widget
    value: value to put in Entry widget
    """

    entry.delete(0, tk.END)
    entry.insert(0, value)

class App(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.master = master
        self.grid(column=0, row=0)

        self.row_n = 0

        self.folder = ""
        self.current = 0
        self.index = 0
        self.base_file_name = ""

        self.data_forward = {"DATETIME": [],
                             "PSUP SP (A)": [],
                             "PSUP I (A)": [],
                             "PSUP V (V)": [],
                             "MAGFIELD (G)": [],
                             "TEMP (C)": [],
                             "LIA X (V)": [],
                             "LIA Y (V)": [],
                             "LIA R (V)": [],
                             "LIA THETA (deg)": [],
                             "KTH OUTPUT (A)": [],
                             "KTH FREQ (HZ)": [],
                             "BGV (V)": [],
                             "R_NL (ohm)": []}

        self.data_reverse = {"DATETIME": [],
                             "PSUP SP (A)": [],
                             "PSUP I (A)": [],
                             "PSUP V (V)": [],
                             "MAGFIELD (G)": [],
                             "TEMP (C)": [],
                             "LIA X (V)": [],
                             "LIA Y (V)": [],
                             "LIA R (V)": [],
                             "LIA THETA (deg)": [],
                             "KTH OUTPUT (A)": [],
                             "KTH FREQ (HZ)": [],
                             "BGV (V)": [],
                             "R_NL (ohm)": []}

        with open("config.json", "r") as f:
            self.config = json.load(f)

        # instrument addresses
        self.kth_addr = self.config["equipment"]["KEITHLEY 6221 CURR_SOURCE"]    # Keithley 6221 current source
        self.lia_addr = self.config["equipment"]["SR850 LIA"]                    # SR850 lock-in amplifier
        self.mag_psup_addr = self.config["equipment"]["LAKESHORE 642 MAG_PSUP"]  # Lakeshore 642 Magnet power supply
        self.gmeter_addr = self.config["equipment"]["LAKESHORE 475 GAUSSMETER"]  # Lakeshore 475 gaussmeter
        self.spa_addr = self.config["equipment"]["AGILENT B1500A SPA"]           # Agilent B1500A SPA

        # instrument objects
        self.kth = None
        self.lia = None
        self.mag_psup = None
        self.gmeter = None
        self.spa = None

        # values to test
        self.freqs = []
        self.currents = []
        self.bgvs = []
        self.test_matrix = []

        self.colors_used = []

        # GUI dimensions
        self.window_w = 1200

        # GPIB configuration
        self.backend = self.config["backend"]
        self.rm = visa.ResourceManager(self.backend)

        self.label_font = ("Helvetica", 10, "bold")

        self._build_frames()
        self._place_user_input_frame()
        self._place_sweep_frame()
        self._place_rdg_frame()
        # self._test()
        
        self._update_connections()

        # adding handling for when user closes the window
        self.master.protocol("WM_DELETE_WINDOW", self.closing_cleanup)

        # event loop variable for sweep event
        self.sweep_loop = None
        self.stop_thread = False

    def _build_frames(self):
        """
        Method for building out sub-frames
        """

        self.user_input_frame = tk.LabelFrame(self, width=self.window_w)
        self.user_input_frame.grid(column=0,
                                   row=self.row_n,
                                   columnspan=6,
                                   rowspan=8,
                                   sticky="wens")
        self.user_input_frame.columnconfigure(0, weight=1)
        
        self.sweep_frame = tk.LabelFrame(self, width=self.window_w)
        self.sweep_frame.grid(column=0,
                              row=8,
                              columnspan=6,
                              rowspan=3,
                              sticky="wens")
        self.sweep_frame.columnconfigure(0, weight=1)

        self.rdg_frame = tk.LabelFrame(self, width=self.window_w)
        self.rdg_frame.grid(column=0,
                            row=12,
                            columnspan=6,
                            rowspan=4,
                            sticky="wens")
        self.rdg_frame.columnconfigure(0, weight=1)

    def _place_user_input_frame(self):
        """
        Method for placing user input frame
        """

        # title label
        self.title_label = tk.Label(self.user_input_frame, text="Lakeshore Magnetic Sweep", font=("Helvetica", 14, "bold"))
        self.title_label.grid(column=0, row=self.row_n, columnspan=6, sticky="wens")
        
        self.row_n += 1

        # Keithley 6221
        self.kth_label = tk.Label(self.user_input_frame, text="Keithley 6221 Source", font=self.label_font, background="red", borderwidth=2, relief="groove")
        self.kth_label.grid(column=0, row=self.row_n, columnspan=3, sticky="wens")

        # LIA
        self.lia_label = tk.Label(self.user_input_frame, text="SR850 L.I.A.", font=self.label_font, background="red", borderwidth=2, relief="groove")
        self.lia_label.grid(column=3, row=self.row_n, columnspan=3, sticky="wens")

        self.row_n += 1

        # Magnet power supply
        self.mag_psup_label = tk.Label(self.user_input_frame, text="Lakeshore 642 Power Supply", font=self.label_font, background="red", borderwidth=2, relief="groove")
        self.mag_psup_label.grid(column=0, row=self.row_n, columnspan=2, sticky="wens")

        # Gaussmeter
        self.gmeter_label = tk.Label(self.user_input_frame, text="Lakeshore 475 Gaussmeter", font=self.label_font, background="red", borderwidth=2, relief="groove")
        self.gmeter_label.grid(column=2, row=self.row_n, columnspan=2, sticky="wens")

        # SPA
        self.spa_label = tk.Label(self.user_input_frame, text="Agilent B1500A SPA", font=self.label_font, background="red", borderwidth=2, relief="groove")
        self.spa_label.grid(column=4, row=self.row_n, columnspan=2, sticky="wens")

        self.row_n += 1

        # reconnect instruments button
        self.recon_instr_button = tk.Button(self.user_input_frame, text="Connect Instruments", command=self._update_connections, font=self.label_font)
        self.recon_instr_button.grid(column=0, row=self.row_n, columnspan=6, sticky="wens")
        
        self.row_n += 1

        # status label
        self.status = tk.Label(self.user_input_frame, text="-", background="green", borderwidth=2, relief="groove")
        self.status.grid(column=0, row=self.row_n, columnspan=6, sticky="wens")
        
        self.row_n += 1

        # selecting a folder
        self.folder_label = tk.Label(self.user_input_frame, text="Save folder:", font=self.label_font)
        self.folder_label.grid(column=0, row=self.row_n, columnspan=1, sticky="e")
        self.folder_str = tk.StringVar(self.user_input_frame)
        self.folder_str.set("")
        self.folder_entry = tk.Entry(self.user_input_frame, textvariable=self.folder_str)
        self.folder_entry.grid(column=1, row=self.row_n, columnspan=3, sticky="wens")

        self.choose_folder_button = tk.Button(self.user_input_frame, text="Select folder", command=self._choose_folder, font=self.label_font)
        self.choose_folder_button.grid(column=4, row=self.row_n, columnspan=2, sticky="wens")
        self.row_n += 1

        # device params label
        self.device_params_label = tk.Label(self.user_input_frame, text="Device Parameters", font=self.label_font)
        self.device_params_label.grid(column=0, row=self.row_n, columnspan=6, sticky="wens")

        self.row_n += 1

        # setting device row
        self.device_row_label = tk.Label(self.user_input_frame, text="Device row:", font=self.label_font)
        self.device_row_label.grid(column=0, row=self.row_n, columnspan=1, sticky="w")
        self.device_row_entry = tk.Entry(self.user_input_frame)
        self.device_row_entry.grid(column=1, row=self.row_n, columnspan=1, sticky="wens")

        # setting device column
        self.device_col_label = tk.Label(self.user_input_frame, text="Device col:", font=self.label_font)
        self.device_col_label.grid(column=2, row=self.row_n, columnspan=1, sticky="w")
        self.device_col_entry = tk.Entry(self.user_input_frame)
        self.device_col_entry.grid(column=3, row=self.row_n, columnspan=1, sticky="wens")
        
        self.row_n += 1

        # electrode configuration
        self.injector_label = tk.Label(self.user_input_frame, text="Injector:", font=self.label_font)
        self.injector_label.grid(column=0, row=self.row_n, columnspan=1, sticky="w")
        self.injector_entry = tk.Entry(self.user_input_frame)
        self.injector_entry.grid(column=1, row=self.row_n, columnspan=1, sticky="wens")
        self.detector_angle_label = tk.Label(self.user_input_frame, text="Det. Angle:", font=self.label_font)
        self.detector_angle_label.grid(column=2, row=self.row_n, columnspan=1, sticky="w")
        self.detector_angle_entry = tk.Entry(self.user_input_frame)
        self.detector_angle_entry.grid(column=3, row=self.row_n, columnspan=1, sticky="wens")
        self.detector_dist_label = tk.Label(self.user_input_frame, text="Det. Distance:", font=self.label_font)
        self.detector_dist_label.grid(column=4, row=self.row_n, columnspan=1, sticky="w")
        self.detector_dist_entry = tk.Entry(self.user_input_frame)
        self.detector_dist_entry.grid(column=5, row=self.row_n, columnspan=1, sticky="wens")

        self.row_n += 1

        # notes
        self.notes_label = tk.Label(self.user_input_frame, text="Notes:", font=self.label_font)
        self.notes_label.grid(column=0, row=self.row_n, columnspan=3, sticky="w")
        self.notes_tb = tk.Text(self.user_input_frame, height=5, width=52, bg="light yellow")
        self.notes_tb.grid(column=3, row=self.row_n, columnspan=3, sticky="ew")
        
        self.row_n += 1

    def _place_sweep_frame(self):
        """
        Method for placing sweep parameter frame
        """

        # sweep params label
        self.sweep_params_label = tk.Label(self.sweep_frame, text="Sweep Parameters", font=self.label_font)
        self.sweep_params_label.grid(column=0, row=self.row_n, columnspan=6, sticky="wens")

        self.row_n += 1

        # carrier frequency
        self.freq_var = tk.StringVar()
        self.freq_label = tk.Label(self.sweep_frame, text="Frequency (Hz):", font=self.label_font)
        self.freq_label.grid(column=0, row=self.row_n, columnspan=1, sticky="w")
        self.freq_entry = tk.Entry(self.sweep_frame, textvariable=self.freq_var, validate="focusout", validatecommand=self._check_sweep_params)
        self.freq_entry.grid(column=1, row=self.row_n, columnspan=1, sticky="wens")
        auto_update_entry(self.freq_entry, "13")

        # injection current
        self.current_label = tk.Label(self.sweep_frame, text="Current (uA):", font=self.label_font)
        self.current_label.grid(column=2, row=self.row_n, columnspan=1, sticky="w")
        self.current_entry = tk.Entry(self.sweep_frame, validate="focusout", validatecommand=self._check_sweep_params)
        self.current_entry.grid(column=3, row=self.row_n, columnspan=1, sticky="wens")
        auto_update_entry(self.current_entry, "10")

        # backgate voltage
        self.bgv_label = tk.Label(self.sweep_frame, text="Backgate Voltage (V):", font=self.label_font)
        self.bgv_label.grid(column=4, row=self.row_n, columnspan=1, sticky="w")
        self.bgv_entry = tk.Entry(self.sweep_frame, validate="focusout", validatecommand=self._check_sweep_params)
        self.bgv_entry.grid(column=5, row=self.row_n, columnspan=1, sticky="wens")
        auto_update_entry(self.bgv_entry, "0")
        
        self.row_n += 1

        # sweep lower limit
        self.swp_low_lim_var = tk.StringVar()
        self.swp_low_lim_label = tk.Label(self.sweep_frame, text="Sweep Lower Limit (A):", font=self.label_font)
        self.swp_low_lim_label.grid(column=0, row=self.row_n, columnspan=1, sticky="w")
        self.swp_low_lim_entry = tk.Entry(self.sweep_frame, textvariable=self.swp_low_lim_var, validate="focusout", validatecommand=self._update_num_points)
        self.swp_low_lim_entry.grid(column=1, row=self.row_n, columnspan=1, sticky="wens")
        auto_update_entry(self.swp_low_lim_entry, "-9.5")

        # sweep upper limit
        self.swp_upp_lim_var = tk.StringVar()
        self.swp_upp_lim_label = tk.Label(self.sweep_frame, text="Sweep Upper Limit (A):", font=self.label_font)
        self.swp_upp_lim_label.grid(column=2, row=self.row_n, columnspan=1, sticky="w")
        self.swp_upp_lim_entry = tk.Entry(self.sweep_frame, textvariable=self.swp_upp_lim_var, validate="focusout", validatecommand=self._update_num_points)
        self.swp_upp_lim_entry.grid(column=3, row=self.row_n, columnspan=1, sticky="wens")
        auto_update_entry(self.swp_upp_lim_entry, "9.5")

        # sweep step
        self.swp_step_var = tk.StringVar()
        self.swp_step_label = tk.Label(self.sweep_frame, text="Sweep Step (A):", font=self.label_font)
        self.swp_step_label.grid(column=4, row=self.row_n, columnspan=1, sticky="w")
        self.swp_step_entry = tk.Entry(self.sweep_frame, textvariable=self.swp_step_var, validate="focusout", validatecommand=self._update_num_points)
        self.swp_step_entry.grid(column=5, row=self.row_n, columnspan=1, sticky="wens")
        auto_update_entry(self.swp_step_entry, "0.1")
        self.row_n += 1

        # sweep symmetry checkbox
        self.swp_sym_var = tk.IntVar(self.sweep_frame, value=1)
        self.swp_sym_cb = tk.Checkbutton(self.sweep_frame, variable=self.swp_sym_var, text="Sweep both ways?", font=self.label_font)
        self.swp_sym_cb.grid(column=0, row=self.row_n, columnspan=2, sticky="w")

        # delay
        self.delay_label = tk.Label(self.sweep_frame, text="Delay (sec):", font=self.label_font)
        self.delay_label.grid(column=2, row=self.row_n, columnspan=1, sticky="w")
        self.delay_entry = tk.Entry(self.sweep_frame)
        self.delay_entry.grid(column=3, row=self.row_n, columnspan=1, sticky="wens")
        auto_update_entry(self.delay_entry, "0.5")

        # number of runs per setting
        self.num_var = tk.StringVar()
        self.num_label = tk.Label(self.sweep_frame, text="Runs per:", font=self.label_font)
        self.num_label.grid(column=4, row=self.row_n, columnspan=1, sticky="w")
        self.num_entry = tk.Entry(self.sweep_frame, textvariable=self.num_var, validate="focusout", validatecommand=self._check_sweep_params)
        self.num_entry.grid(column=5, row=self.row_n, columnspan=1, sticky="wens")
        auto_update_entry(self.num_entry, "1")

        self.row_n += 1

        # datapoint readout
        self.points_label = tk.Label(self.sweep_frame, text=f"Datapoints/run: {self._calc_datapoints()}", font=self.label_font)
        self.points_label.grid(column=0, row=self.row_n, columnspan=2, sticky="wens")

        self.num_runs_label = tk.Label(self.sweep_frame, text=f"Number of runs: {len(self.test_matrix)}", font=self.label_font)
        self.num_runs_label.grid(column=2, row=self.row_n, columnspan=2, sticky="wens")
        self.row_n += 1

        # start sweep button
        self.start_swp_button = tk.Button(self.sweep_frame, text="Begin Sweep", command=self._begin_sweep, font=("Helvetica", 14, "bold"))
        self.start_swp_button.grid(column=0, row=self.row_n, columnspan=6, sticky="wens")
        self.row_n += 1

        # stop sweep button
        self.stop_swp_button = tk.Button(self.sweep_frame, text="Stop Sweep", command=self._stop_sweep, font=("Helvetica", 14, "bold"))
        self.stop_swp_button.grid(column=0, row=self.row_n, columnspan=6, sticky="wens")
        self.row_n += 1

    def _place_rdg_frame(self):
        """
        Places live reading frame
        """

        # setting up the live plotting
        # forward scan
        self.f_fig = plt.figure(figsize=(7,2), dpi=100)
        self.f_ax1 = self.f_fig.add_subplot(1,1,1)
        self.f_ax1.set_xlabel("Mag. Field (G)")
        self.f_ax1.set_ylabel("R_NL (Ohm)")
        # self.f_line, = self.f_ax1.plot(self.data_forward["MAGFIELD (G)"], self.data_forward["R_NL (ohm)"], marker="o")
        self.f_plotcanv = FigureCanvasTkAgg(self.f_fig, self.rdg_frame)
        self.f_plotcanv.get_tk_widget().grid(column=0, row=self.row_n)

        self.row_n += 1
        
        # reverse scan
        self.r_fig = plt.figure(figsize=(7,2), dpi=100)
        self.r_ax1 = self.r_fig.add_subplot(1,1,1)
        self.r_ax1.set_xlabel("Mag. Field (G)")
        self.r_ax1.set_ylabel("R_NL (Ohm)")
        # self.r_line, = self.r_ax1.plot(self.data_reverse["MAGFIELD (G)"], self.data_reverse["R_NL (ohm)"], marker="o")
        self.r_plotcanv = FigureCanvasTkAgg(self.r_fig, self.rdg_frame)
        self.r_plotcanv.get_tk_widget().grid(column=0, row=self.row_n)

        self.row_n += 1

    def _choose_folder(self):
        """
        Handles choose folder button event
        """
        
        self.folder = fd.askdirectory()
        if self.folder:
            self.folder_str.set(self.folder)
            self.status["text"] = f"Selected folder '{self.folder}'"
            self.status["background"] = "green"
        else:
            self.folder = ""

    def _calc_datapoints(self):
        """
        Calculates the number of datapoints in the measurement
        """
        
        try:
            lower = float(self.swp_low_lim_entry.get())
            upper = float(self.swp_upp_lim_entry.get())
            step = float(self.swp_step_var.get())
        except ValueError:
            return 0

        if upper > 9.5:
            auto_update_entry(self.swp_upp_lim_entry, "9.5")

        if lower < -9.5:
            auto_update_entry(self.swp_low_lim_entry, "-9.5")

        if (upper > lower):
            num_pts = int((upper-lower)/step)
            if self.swp_sym_var.get():
                num_pts *= 2
            return num_pts
        else:
            return 0

    def _update_num_points(self):
        """
        Callback function for updating number of points label
        """
        
        self.points_label["text"] = f"Datapoints: {self._calc_datapoints()}"
        return True

    def _update_connections(self):
        """
        Handles button that updates intstrument connections
        """
        
        resources = self.rm.list_resources()
        
        if self.kth_addr in resources:
            self.kth_label["background"] = "green"
            self.kth = Kth6221(self.rm, self.kth_addr)

            # set output low to earth ground
            self.kth.set_output_low()

            # set output amplitude
            self.kth.set_wave_ampl(10e-6)

            # make sure output is off
            self.kth.stop_output()

            # self.current_value["text"] = f"{round(float(self.kth.get_wave_ampl())/(1e-6), 3)}"
        else:
            self.kth_label["background"] = "red"
            self.kth = None

        if self.lia_addr in resources:
            self.lia_label["background"] = "green"
            self.lia = SR850(self.rm, self.lia_addr)
        else:
            self.lia_label["background"] = "red"
            self.lia = None

        if self.mag_psup_addr in resources:
            self.mag_psup_label["background"] = "green"
            self.mag_psup = LS642(self.rm, self.mag_psup_addr)
        else:
            self.mag_psup_label["background"] = "red"
            self.mag_psup = None

        if self.gmeter_addr in resources:
            self.gmeter_label["background"] = "green"
            self.gmeter = LS475(self.rm, self.gmeter_addr)
        else:
            self.gmeter_label["background"] = "red"
            self.gmeter = None

        if self.spa_addr in resources:
            self.spa_label["background"] = "green"
            self.spa = B1500A(self.rm, self.spa_addr)

            # make sure voltage to SMU3 is off
            self.spa.connect_smu()
            self.spa.set_voltage(0)
            
        else:
            self.spa_label["background"] = "red"
            self.spa = None

    def _reset_data(self):
        self.data_forward = {"DATETIME": [],
                             "PSUP SP (A)": [],
                             "PSUP I (A)": [],
                             "PSUP V (V)": [],
                             "MAGFIELD (G)": [],
                             "TEMP (C)": [],
                             "LIA X (V)": [],
                             "LIA Y (V)": [],
                             "LIA R (V)": [],
                             "LIA THETA (deg)": [],
                             "KTH OUTPUT (A)": [],
                             "KTH FREQ (HZ)": [],
                             "BGV (V)": [],
                             "R_NL (ohm)": []}
                             

        self.data_reverse = {"DATETIME": [],
                             "PSUP SP (A)": [],
                             "PSUP I (A)": [],
                             "PSUP V (V)": [],
                             "MAGFIELD (G)": [],
                             "TEMP (C)": [],
                             "LIA X (V)": [],
                             "LIA Y (V)": [],
                             "LIA R (V)": [],
                             "LIA THETA (deg)": [],
                             "KTH OUTPUT (A)": [],
                             "KTH FREQ (HZ)": [],
                             "BGV (V)": [],
                             "R_NL (ohm)": []}

    def _begin_sweep(self):
        """
        Creates separate thread and runs the sweep callback function
        """

        """
        threading.Thread(target=lambda loop: loop.run_until_complete(self._run_sweep()),
                         args=(asyncio.new_event_loop(),)).start()
        """
        self.sweep_loop = asyncio.new_event_loop()
        self.stop_thread = False
        threading.Thread(target=lambda loop: loop.run_until_complete(self._run_sweep()),
                         args=(self.sweep_loop,)).start()

    def _test(self, frame=None):
        self.master.after(1000, self._test, self.master)
        self._update_connections()

        if self.lia:
            lia_rdg = self.lia.data_point()
            self.lia_x_rdg["text"] = f"X: {round(lia_rdg['X']/(1e-6), 3)} uV"
            self.lia_y_rdg["text"] = f"Y: {round(lia_rdg['Y']/(1e-6), 3)} uV"
            self.lia_r_rdg["text"] = f"R: {round(lia_rdg['R']/(1e-6), 3)} uV"
            self.lia_theta_rdg["text"] = f"Theta: {round(lia_rdg['T'], 1)} deg"
        else:
            self.lia_x_rdg["text"] = "X: -"
            self.lia_y_rdg["text"] = "Y: -"
            self.lia_r_rdg["text"] = "R: -"
            self.lia_theta_rdg["text"] = "Theta: -"

        if self.gmeter:
            self.gmeter_field_rdg["text"] = f"Field: {round(self.gmeter.get_field_reading(), 3)} G"
            self.gmeter_temp_rdg["text"] = f"Temp: {round(self.gmeter.get_temp_reading(), 1)} C"
        else:
            self.gmeter_field_rdg["text"] = "Field: -"
            self.gmeter_temp_rdg["text"] = "Temp: -"

        if self.mag_psup:
            self.mag_psup_setpt["text"] = f"Setpoint: {round(float(self.mag_psup.get_setpoint()), 3)} A"
            self.mag_psup_curr_rdg["text"] = f"Output Current: {round(float(self.mag_psup.get_current()), 3)} A"
            self.mag_psup_volt_rdg["text"] = f"Output Voltage: {round(float(self.mag_psup.get_voltage()), 3)} V"
        else:
            self.mag_psup_curr_rdg["text"] = "-"

    def _await_test(self):
        threading.Thread(target=lambda loop: loop.run_until_complete(self._test_2()))

    async def _run_sweep(self):
        """
        Callback function that runs in separate thread to maintain updating features
        """

        self._update_connections()

        if self._calc_datapoints() == 0:
            self.status["text"] = "Make sure that the sweep lower limit is lower than the sweep upper limit!"
            self.status["background"] = "red"
            return

        if self.folder == "":
            self.status["text"] = "Please select a folder to save the data to!"
            self.status["background"] = "red"
            return

        if None in [self.kth, self.lia, self.mag_psup, self.gmeter]:
            self.status["text"] = "Please make sure all instruments are connected!"
            self.status["background"] = "red"
            return
        
        # clearing the plots
        self.f_ax1.cla()
        self.r_ax1.cla()
        self.colors_used = []

        for datapoint in self.test_matrix:
            run_freq = datapoint["frequency"]
            run_curr = datapoint["current"]
            run_bgv = datapoint["bgv"]
            
            self.status["text"] = f"Running sweep: Frequency={run_freq} Hz, Current={run_curr} uA, BGV={run_bgv} V"
            self.status["background"] = "cyan"

            row = self.device_row_entry.get()
            col = self.device_col_entry.get()

            base_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{row}_{col}"

            # getting injection current amplitude
            inj_current = float(run_curr)*1.0e-6
            if abs(inj_current) <= CURRENT_LIMIT:
                self.kth.set_wave_ampl(inj_current)
            else:
                self.status["text"] = f"Keep the injection current below the limit of {CURRENT_LIMIT} A!"
                self.status["background"] = "red"
                return

            # getting injection current frequency
            inj_freq = float(run_freq)
            if (inj_freq <= FREQ_LIMIT) and (inj_freq > 0):
                self.kth.set_wave_freq(inj_freq)
            else:
                self.status["text"] = f"Keep the injection frequency below the limit of {FREQ_LIMIT} Hz!"
                self.status["background"] = "red"
                return

            # setting BGV
            if (run_bgv <= 80) and (run_bgv >= -80):
                self.spa.set_voltage(run_bgv)
            else:
                self.status["text"] = f"Keep the backgate voltage between -80 and 80 V!"
                self.status["background"] = "red"
                return

            # getting sweep profile
            swp_start = float(self.swp_low_lim_entry.get())
            swp_end = float(self.swp_upp_lim_entry.get())
            swp_delta = float(self.swp_step_entry.get())

            swp_forward = list(np.arange(swp_start, swp_end+swp_delta, swp_delta))
            swp_reverse = []

            if self.swp_sym_var.get():
                swp_reverse = swp_forward[::-1]

            swp_forward = [round(i, 3) for i in swp_forward]
            swp_reverse = [round(i, 3) for i in swp_reverse]

            notes = self.notes_tb.get("1.0", "end-1c")

            delay = float(self.delay_entry.get())     

            # starting current output
            self.kth.start_output()

            # plot color
            plot_color = random.choice(list(COLORS.keys()))

            # setting up new line to draw
            self.f_line, = self.f_ax1.plot(self.data_forward["MAGFIELD (G)"], self.data_forward["R_NL (ohm)"], color=plot_color, marker="o", markersize=3,
                                           label=f"Frequency={run_freq} Hz, Current={run_curr} uA, BGV={run_bgv} V")
            self.r_line, = self.r_ax1.plot(self.data_reverse["MAGFIELD (G)"], self.data_reverse["R_NL (ohm)"], color=plot_color, marker="o", markersize=3,
                                           label=f"Frequency={run_freq} Hz, Current={run_curr} uA, BGV={run_bgv} V")

            for m,i in enumerate(swp_forward):
                if self.stop_thread:
                    self._cleanup_sweep()
                    return
                    
                self.mag_psup.set_current(i)
                # delay for longer on first measurement to allow magnet to ramp
                if m == 0:
                    time.sleep(10)

                # appending data
                try:
                    self.data_forward["DATETIME"].append(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    self.data_forward["PSUP SP (A)"].append(round(float(self.mag_psup.get_setpoint()), 3))
                    # self.data_forward["PSUP SP (A)"].append("-")
                    self.data_forward["PSUP I (A)"].append(round(float(self.mag_psup.get_current()), 3))
                    self.data_forward["PSUP V (V)"].append(round(float(self.mag_psup.get_voltage()), 3))
                    self.data_forward["MAGFIELD (G)"].append(round(self.gmeter.get_field_reading(), 3))
                    self.data_forward["TEMP (C)"].append(round(self.gmeter.get_temp_reading(), 1))
                    lia_rdg = self.lia.data_point()
                    self.data_forward["LIA X (V)"].append(lia_rdg["X"])
                    self.data_forward["LIA Y (V)"].append(lia_rdg["Y"])
                    self.data_forward["LIA R (V)"].append(lia_rdg["R"])
                    self.data_forward["LIA THETA (deg)"].append(lia_rdg["T"])
                    curr = float(self.kth.get_wave_ampl())
                    self.data_forward["KTH OUTPUT (A)"].append(curr)
                    self.data_forward["KTH FREQ (HZ)"].append(inj_freq)
                    self.data_forward["BGV (V)"].append(run_bgv)
                    self.data_forward["R_NL (ohm)"].append(round(lia_rdg["X"]/curr, 3))
                    
                    time.sleep(delay)
                except Exception as e:
                    print(e)
                    print("Timeout error...")
                    time.sleep(5)
                    
                self.f_ax1.relim()
                self.f_ax1.autoscale_view()
                self.f_line.set_data(self.data_forward["MAGFIELD (G)"], self.data_forward["R_NL (ohm)"])
                self.f_plotcanv.draw()
                self.f_plotcanv.flush_events()

            # resetting magnet by sweeping to high positive current
            self.mag_psup.set_current(9.5)
            time.sleep(10)
            

            for n,j in enumerate(swp_reverse):
                if self.stop_thread:
                    self._cleanup_sweep()
                    return
                
                self.mag_psup.set_current(j)
                # delay for longer on first measurement to allow magnet to ramp
                if n == 0:
                    time.sleep(10)
                
                # appending data
                try:
                    self.data_reverse["DATETIME"].append(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    self.data_reverse["PSUP SP (A)"].append(round(float(self.mag_psup.get_setpoint()), 3))
                    # self.data_reverse["PSUP SP (A)"].append("-")
                    self.data_reverse["PSUP I (A)"].append(round(float(self.mag_psup.get_current()), 3))
                    self.data_reverse["PSUP V (V)"].append(round(float(self.mag_psup.get_voltage()), 3))
                    self.data_reverse["MAGFIELD (G)"].append(round(self.gmeter.get_field_reading(), 3))
                    self.data_reverse["TEMP (C)"].append(round(self.gmeter.get_temp_reading(), 1))
                    lia_rdg = self.lia.data_point()
                    self.data_reverse["LIA X (V)"].append(lia_rdg["X"])
                    self.data_reverse["LIA Y (V)"].append(lia_rdg["Y"])
                    self.data_reverse["LIA R (V)"].append(lia_rdg["R"])
                    self.data_reverse["LIA THETA (deg)"].append(lia_rdg["T"])
                    curr = float(self.kth.get_wave_ampl())
                    self.data_reverse["KTH OUTPUT (A)"].append(curr)
                    self.data_reverse["KTH FREQ (HZ)"].append(inj_freq)
                    self.data_reverse["BGV (V)"].append(run_bgv)
                    self.data_reverse["R_NL (ohm)"].append(round(lia_rdg["X"]/curr, 3))
                    
                    time.sleep(delay)
                except Exception as e:
                    print(e)
                    print("Timeout error...")
                    time.sleep(5)

                self.r_ax1.relim()
                self.r_ax1.autoscale_view()
                self.r_line.set_data(self.data_reverse["MAGFIELD (G)"], self.data_reverse["R_NL (ohm)"])
                self.r_plotcanv.draw()
                self.r_plotcanv.flush_events()

            # resetting magnet by sweeping to high negative current
            self.mag_psup.set_current(-9.5)
            time.sleep(10)

            
            
            pd.DataFrame(data=self.data_forward).to_csv(os.path.join(self.folder, f"{base_name}_forward.csv"), index=False)
            pd.DataFrame(data=self.data_reverse).to_csv(os.path.join(self.folder, f"{base_name}_reverse.csv"), index=False)

            if notes:
                with open(os.path.join(self.folder, f"{base_name}_notes.txt"), "w") as f:
                    f.write(notes)

            # saving electrode configuration
            e_data = {"injector": self.injector_entry.get(),
                    "detector dist": self.detector_dist_entry.get(),
                    "detector angle": self.detector_angle_entry.get()}

            with open(os.path.join(self.folder, f"{base_name}_electrodes.json"), "w") as f:
                json.dump(e_data, f, indent=4)
                

            self.mag_psup.set_current(0)
            self.kth.stop_output()
            self.spa.set_voltage(0)
            self.spa.disconnect_smu()
            self.spa.connect_smu()
            
            self.status["text"] = "Sweep complete"
            self.status["background"] = "green"
            self._reset_data()


    def _stop_sweep(self):
        """
        Handles interrupt of sweep function
        """
        if self.sweep_loop is not None:
            self.stop_thread = True
            self.sweep_loop = None

    def _cleanup_sweep(self):
        """
        Cleans up after interrupt
        """
        self.mag_psup.set_current(0)
        self.kth.stop_output()
        self.spa.set_voltage(0)
        self.spa.disconnect_smu()
        self.spa.connect_smu()
        self.status["text"] = "Sweep interrupted"
        self.status["background"] = "red"
        self._reset_data()

    def _check_sweep_params(self):
        self.freqs = parse_entry(self.freq_entry.get())
        self.test_matrix = []

        if self.freqs is None:
            self.status["text"] = "Invalid input for frequency!"
            self.status["background"] = "red"
            return True
        else:
            self.status["text"] = "-"
            self.status["background"] = "green"

        self.currents = parse_entry(self.current_entry.get())

        if self.currents is None:
            self.status["text"] = "Invalid input for current!"
            self.status["background"] = "red"
            return True
        else:
            self.status["text"] = "-"
            self.status["background"] = "green"

        self.bgvs = parse_entry(self.bgv_entry.get())

        if self.bgvs is None:
            self.status["text"] = "Invalid input for backgate voltage!"
            self.status["background"] = "red"
            return True
        else:
            self.status["text"] = "-"
            self.status["background"] = "green"

        num_runs = int(self.num_entry.get())

        for i in self.freqs:
            for j in self.currents:
                for k in self.bgvs:
                    for n in range(num_runs):
                        self.test_matrix.append({"frequency": i, "current": j, "bgv": k})

        self.num_runs_label["text"] = f"Number of runs: {len(self.test_matrix)}"
        return True

    def closing_cleanup(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.mag_psup:
                self.mag_psup.set_current(0)
            if self.kth:
                self.kth.stop_output()
            if self.spa:
                self.spa.set_voltage(0)
                self.spa.disconnect_smu()
            self.rm.close()
            self.master.destroy()


        
        
