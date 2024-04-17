import tkinter as tk

from magsweep.gui import App


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Magnetic Sweep")
    padx = 20
    pady = 100
    root.geometry(f"{root.winfo_screenwidth()-padx}x{root.winfo_screenheight()-pady}+0+0")
    root.resizable(False, False)
    app = App(master=root)
    app.mainloop()
