#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import sys
import threading
import queue
import time
from datetime import datetime

# Import your existing functions - adjust the import path as needed
# Assuming your script is saved as 'nvm_burner.py'
try:
    from ops_tool import (
        mount_remote_share, unmount_share, check_disk_exists,
        list_directory_contents, extract_tgz_file, find_kernel_rpms,
        install_kernel_rpms, run_kernel_commit_interactive,
        burn_image_to_ssd, install_kernel_from_tgz
    )
except ImportError:
    print("Please ensure your original script is saved as 'nvm_burner.py' in the same directory")
    sys.exit(1)

class NVMBurnerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NVM Burner & Kernel Installer")
        self.root.geometry("1000x700")
        self.root.configure(bg='#2b2b2b')
        
        # Configuration
        self.remote_path = "//ladjsvop.jer.intel.com/burn"
        self.mount_dir = "/tmp/remote_burn_mount"
        self.disk_name = "/dev/nvme0n1"
        self.username = "laduser"
        self.password = "$giga"
        
        # State variables
        self.current_screen = "main"
        self.selected_folder = ""
        self.folder_contents = []
        self.selected_item = None
        self.available_kernels = []
        self.selected_kernel = None
        self.is_mounted = False
        self.installation_complete = False
        
        # Threading for long operations
        self.operation_queue = queue.Queue()
        self.root.after(100, self.check_queue)
        
        # Create main container
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configure styles
        self.setup_styles()
        
        # Initialize with main screen
        self.show_main_screen()
        
        # Mount share on startup
        self.mount_share_startup()
    
    def setup_styles(self):
        """Configure custom styles for the GUI"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('Title.TLabel', font=('Arial', 24, 'bold'), background='#2b2b2b', foreground='#ffffff')
        style.configure('Subtitle.TLabel', font=('Arial', 12), background='#2b2b2b', foreground='#cccccc')
        style.configure('Header.TLabel', font=('Arial', 16, 'bold'), background='#2b2b2b', foreground='#4a9eff')
        style.configure('Kernel.TButton', font=('Arial', 12, 'bold'))
        style.configure('NVM.TButton', font=('Arial', 12, 'bold'))
        style.configure('SSD.TButton', font=('Arial', 12, 'bold'))
        style.configure('Action.TButton', font=('Arial', 11, 'bold'))
    
    def clear_frame(self):
        """Clear the main frame"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
    
    def show_main_screen(self):
        """Display the main screen with folder selection buttons"""
        self.clear_frame()
        self.current_screen = "main"
        
        # Title
        title_label = ttk.Label(self.main_frame, text="NVM Burner & Kernel Installer", style='Title.TLabel')
        title_label.pack(pady=(20, 10))
        
        subtitle_label = ttk.Label(self.main_frame, text="Professional tool for flashing images and installing custom kernels", style='Subtitle.TLabel')
        subtitle_label.pack(pady=(0, 30))
        
        # Main content frame
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(expand=True, fill="both")
        
        # Create grid layout
        left_frame = ttk.LabelFrame(content_frame, text="System Operations", padding="20")
        left_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        right_frame = ttk.LabelFrame(content_frame, text="Future Development", padding="20")
        right_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # Left column buttons
        kernel_btn = ttk.Button(left_frame, text="KERNEL\nInstall custom kernel packages", 
                               command=lambda: self.show_folder_screen("Kernel"), 
                               style='Kernel.TButton', width=30)
        kernel_btn.pack(pady=10, fill="x")
        
        nvm_btn = ttk.Button(left_frame, text="NVM\nFlash NVMe firmware and images", 
                            command=lambda: self.show_folder_screen("NVM"), 
                            style='NVM.TButton', width=30)
        nvm_btn.pack(pady=10, fill="x")
        
        ssd_btn = ttk.Button(left_frame, text="SSD\nBurn SSD images and recovery tools", 
                            command=lambda: self.show_folder_screen("SSD"), 
                            style='SSD.TButton', width=30)
        ssd_btn.pack(pady=10, fill="x")
        
        # Right column (future development)
        future_btn1 = ttk.Button(right_frame, text="Advanced Settings\n(Coming Soon)", 
                                state="disabled", width=30)
        future_btn1.pack(pady=10, fill="x")
        
        future_btn2 = ttk.Button(right_frame, text="Auto Download\n(Coming Soon)", 
                                state="disabled", width=30)
        future_btn2.pack(pady=10, fill="x")
        
        future_btn3 = ttk.Button(right_frame, text="System Monitor\n(Coming Soon)", 
                                state="disabled", width=30)
        future_btn3.pack(pady=10, fill="x")
        
        # Status bar
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill="x", pady=(20, 0))
        
        mount_status = "🟢 Mounted" if self.is_mounted else "🔴 Not Mounted"
        status_label = ttk.Label(status_frame, text=f"Mount point: {self.mount_dir} | Status: {mount_status}")
        status_label.pack()
    
    def show_folder_screen(self, folder_name):
        """Display the folder contents screen"""
        self.clear_frame()
        self.current_screen = "folder"
        self.selected_folder = folder_name
        self.selected_item = None
        self.installation_complete = False
        self.available_kernels = []
        self.selected_kernel = None
        
        # Header
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill="x", pady=(10, 20))
        
        back_btn = ttk.Button(header_frame, text="← Back", command=self.show_main_screen)
        back_btn.pack(side="left")
        
        title_label = ttk.Label(header_frame, text=f"{folder_name} Repository", style='Header.TLabel')
        title_label.pack(side="left", padx=(20, 0))
        
        # Path display
        path_frame = ttk.LabelFrame(self.main_frame, text="Current Path", padding="10")
        path_frame.pack(fill="x", pady=(0, 20))
        
        path_label = ttk.Label(path_frame, text=f"{self.mount_dir}/{folder_name}", font=('Courier', 10))
        path_label.pack(anchor="w")
        
        # Content list
        self.create_content_list()
        
        # Load folder contents
        self.load_folder_contents(folder_name)
    
    def create_content_list(self):
        """Create the content list widget"""
        list_frame = ttk.LabelFrame(self.main_frame, text="Files", padding="10")
        list_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Treeview for file listing
        columns = ("Type", "Size", "Date")
        self.file_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", height=15)
        
        # Configure columns
        self.file_tree.heading("#0", text="Name")
        self.file_tree.heading("Type", text="Type")
        self.file_tree.heading("Size", text="Size") 
        self.file_tree.heading("Date", text="Date")
        
        self.file_tree.column("#0", width=400)
        self.file_tree.column("Type", width=100)
        self.file_tree.column("Size", width=100)
        self.file_tree.column("Date", width=200)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        
        self.file_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind selection
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select)
        
        # Status text area
        self.status_frame = ttk.LabelFrame(self.main_frame, text="Operation Status", padding="10")
        self.status_frame.pack(fill="x", pady=(0, 20))
        
        self.status_text = scrolledtext.ScrolledText(self.status_frame, height=5, state="disabled")
        self.status_text.pack(fill="x")
        
        # Action buttons frame
        self.action_frame = ttk.Frame(self.main_frame)
        self.action_frame.pack(fill="x")
    
    def load_folder_contents(self, folder_name):
        """Load contents of the specified folder"""
        folder_path = os.path.join(self.mount_dir, folder_name)
        
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        if not os.path.exists(folder_path):
            self.log_status(f"Error: Folder {folder_path} not found. Make sure the share is mounted.")
            return
        
        try:
            items = os.listdir(folder_path)
            for item in sorted(items):
                item_path = os.path.join(folder_path, item)
                
                # Get file info
                stat_info = os.stat(item_path)
                size = self.format_size(stat_info.st_size)
                date = datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M")
                
                # Determine type
                if os.path.isdir(item_path):
                    file_type = "DIR"
                elif item.lower().endswith(('.tgz', '.tar.gz')):
                    file_type = "KERNEL"
                elif item.lower().endswith(('.img', '.iso', '.bin', '.raw')):
                    file_type = "IMAGE"
                else:
                    file_type = "FILE"
                
                # Insert into tree
                self.file_tree.insert("", "end", text=item, values=(file_type, size, date))
                
        except Exception as e:
            self.log_status(f"Error loading folder contents: {str(e)}")
    
    def format_size(self, size_bytes):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def on_file_select(self, event):
        """Handle file selection in the tree"""
        selection = self.file_tree.selection()
        if selection:
            item = self.file_tree.item(selection[0])
            self.selected_item = {
                'name': item['text'],
                'type': item['values'][0],
                'size': item['values'][1],
                'date': item['values'][2]
            }
            self.update_action_buttons()
    
    def update_action_buttons(self):
        """Update action buttons based on selection and state"""
        # Clear existing buttons
        for widget in self.action_frame.winfo_children():
            widget.destroy()
        
        if not self.selected_item:
            return
        
        if self.selected_folder == "Kernel" and not self.installation_complete:
            if self.selected_item['type'] in ['KERNEL', 'FILE']:
                install_btn = ttk.Button(self.action_frame, text="📦 Install Kernel Package", 
                                       command=self.install_kernel, style='Action.TButton')
                install_btn.pack(side="left", padx=10)
        
        elif self.selected_folder == "Kernel" and self.installation_complete:
            self.show_kernel_list()
            if self.selected_kernel:
                commit_btn = ttk.Button(self.action_frame, text="✅ Commit Kernel", 
                                      command=self.commit_kernel, style='Action.TButton')
                commit_btn.pack(side="left", padx=10)
        
        elif self.selected_folder in ["NVM", "SSD"]:
            if self.selected_item['type'] in ['IMAGE', 'FILE']:
                burn_btn = ttk.Button(self.action_frame, text="🔥 Burn Image to Device", 
                                    command=self.burn_image, style='Action.TButton')
                burn_btn.pack(side="left", padx=10)
    
    def show_kernel_list(self):
        """Show available kernels after installation"""
        if hasattr(self, 'kernel_frame'):
            self.kernel_frame.destroy()
        
        self.kernel_frame = ttk.LabelFrame(self.main_frame, text="Available Kernels", padding="10")
        self.kernel_frame.pack(fill="x", pady=(0, 10))
        
        # Mock kernel list - in real implementation, you'd get this from grub
        kernels = [
            "kernel-5.15.0-mev",
            "kernel-5.14.0-ipu", 
            "kernel-6.1.0-custom"
        ]
        
        self.kernel_var = tk.StringVar()
        for kernel in kernels:
            rb = ttk.Radiobutton(self.kernel_frame, text=kernel, variable=self.kernel_var, 
                               value=kernel, command=self.on_kernel_select)
            rb.pack(anchor="w", pady=2)
    
    def on_kernel_select(self):
        """Handle kernel selection"""
        self.selected_kernel = self.kernel_var.get()
        self.update_action_buttons()
    
    def log_status(self, message):
        """Log a status message"""
        self.status_text.config(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert("end", f"[{timestamp}] {message}\n")
        self.status_text.see("end")
        self.status_text.config(state="disabled")
        self.root.update()
    
    def run_threaded_operation(self, operation, *args):
        """Run an operation in a separate thread"""
        def worker():
            try:
                operation(*args)
            except Exception as e:
                self.operation_queue.put(("error", str(e)))
        
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
    
    def check_queue(self):
        """Check for messages from worker threads"""
        try:
            while True:
                message_type, message = self.operation_queue.get_nowait()
                if message_type == "error":
                    messagebox.showerror("Error", message)
                elif message_type == "success":
                    messagebox.showinfo("Success", message)
                elif message_type == "status":
                    self.log_status(message)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_queue)
    
    def mount_share_startup(self):
        """Mount the share on startup"""
        def mount_worker():
            try:
                self.operation_queue.put(("status", "Mounting remote share..."))
                mount_remote_share(self.remote_path, self.mount_dir, self.username, self.password)
                self.is_mounted = True
                self.operation_queue.put(("status", "Remote share mounted successfully"))
            except Exception as e:
                self.operation_queue.put(("status", f"Failed to mount share: {str(e)}"))
        
        self.run_threaded_operation(mount_worker)
    
    def install_kernel(self):
        """Install the selected kernel package"""
        if not self.selected_item:
            return
        
        file_path = os.path.join(self.mount_dir, self.selected_folder, self.selected_item['name'])
        
        def install_worker():
            try:
                self.operation_queue.put(("status", f"Starting kernel installation from {self.selected_item['name']}"))
                success = install_kernel_from_tgz(file_path, auto_reboot=False)
                
                if success:
                    self.installation_complete = True
                    self.operation_queue.put(("status", "Kernel installation completed successfully!"))
                    self.operation_queue.put(("success", "Kernel installed! Now select a kernel to commit."))
                    # Update UI in main thread
                    self.root.after(100, self.update_action_buttons)
                else:
                    self.operation_queue.put(("error", "Kernel installation failed"))
            except Exception as e:
                self.operation_queue.put(("error", f"Installation error: {str(e)}"))
        
        self.run_threaded_operation(install_worker)
    
    def commit_kernel(self):
        """Commit the selected kernel as default"""
        if not self.selected_kernel:
            return
        
        def commit_worker():
            try:
                self.operation_queue.put(("status", f"Setting {self.selected_kernel} as default kernel..."))
                # Here you would call your kernel_commit function
                success = run_kernel_commit_interactive()
                
                if success:
                    self.operation_queue.put(("success", f"Kernel {self.selected_kernel} set as default! Reboot to activate."))
                else:
                    self.operation_queue.put(("error", "Failed to set default kernel"))
            except Exception as e:
                self.operation_queue.put(("error", f"Commit error: {str(e)}"))
        
        self.run_threaded_operation(commit_worker)
    
    def burn_image(self):
        """Burn the selected image to device"""
        if not self.selected_item:
            return
        
        # Confirm operation
        result = messagebox.askyesno(
            "Confirm Burn Operation", 
            f"Are you sure you want to burn {self.selected_item['name']} to {self.disk_name}?\n\n"
            "This will OVERWRITE all data on the device!"
        )
        
        if not result:
            return
        
        file_path = os.path.join(self.mount_dir, self.selected_folder, self.selected_item['name'])
        
        def burn_worker():
            try:
                self.operation_queue.put(("status", f"Burning {self.selected_item['name']} to {self.disk_name}..."))
                burn_image_to_ssd(file_path, self.disk_name)
                self.operation_queue.put(("success", "Image burned successfully!"))
            except Exception as e:
                self.operation_queue.put(("error", f"Burn error: {str(e)}"))
        
        self.run_threaded_operation(burn_worker)
    
    def on_closing(self):
        """Handle application closing"""
        if self.is_mounted:
            try:
                unmount_share(self.mount_dir)
            except:
                pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = NVMBurnerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()