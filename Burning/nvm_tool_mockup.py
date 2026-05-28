import tkinter as tk
from tkinter import ttk

# Create a canvas window
root = tk.Tk()
root.title("NVM Burner & Kernel Installer - Canvas Layout")
root.geometry("800x600")

# Main frame
main_frame = ttk.Frame(root, padding="10")
main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

# Mockup elements as labeled rectangles
elements = [
    ("Mount Status", 0, 0, 2, 1, "gray"),
    ("Select File", 1, 0, 1, 1, "lightblue"),
    ("Install Kernel", 1, 1, 1, 1, "lightgreen"),
    ("Burn Image", 1, 2, 1, 1, "lightyellow"),
    ("Back", 2, 0, 1, 1, "lightpink"),
    ("Unmount & Exit", 2, 1, 2, 1, "lightcoral"),
    ("File Listbox", 3, 0, 3, 1, "lightgray"),
    ("Auto-reboot Check", 4, 0, 3, 1, "white"),
    ("Text Area", 5, 0, 3, 1, "lightcyan")
]

for label, row, col, rowspan, colspan, color in elements:
    frame = ttk.Frame(main_frame, relief="solid", borderwidth=1, padding="5", style=f"Custom.TFrame")
    frame.grid(row=row, column=col, rowspan=rowspan, columnspan=colspan, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
    label_widget = tk.Label(frame, text=label, bg=color, width=20, height=2)
    label_widget.pack(expand=True)

# Configure grid weights
for i in range(6):
    main_frame.rowconfigure(i, weight=1)
for i in range(3):
    main_frame.columnconfigure(i, weight=1)

# Custom style for frames
style = ttk.Style()
style.configure("Custom.TFrame", background="black")

root.mainloop()