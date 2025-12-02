import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading
import subprocess
import os
from datetime import datetime
import webbrowser
import queue
import time
from supabase import create_client, Client
from dotenv import load_dotenv

# --- VS Code Theme Colors ---
COLOR_BG_MAIN = "#1e1e1e"
COLOR_BG_SIDE = "#252526" # Header, Side, Control Panel
COLOR_ACCENT = "#007acc"  # Blue
COLOR_ACCENT_HOVER = "#0063a5"
COLOR_BORDER = "#333333"
COLOR_INPUT_BG = "#3c3c3c"
COLOR_TEXT_MAIN = "#cccccc"
COLOR_TEXT_GRAY = "#858585"
COLOR_SELECTION = "#094771"
COLOR_DANGER = "#ef4444"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TechStackManager:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("AI Stack List Manager (Updated)")
        self.root.geometry("1400x900")
        self.root.configure(fg_color=COLOR_BG_MAIN)
        
        # Fonts
        self.font_bold = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        self.font_normal = ctk.CTkFont(family="Segoe UI", size=13)
        self.font_small = ctk.CTkFont(family="Segoe UI", size=11)
        self.font_mono = ctk.CTkFont(family="Consolas", size=12)

        # State
        self.log_queue = queue.Queue()
        self.log_text = None
        self.supabase = None
        self.supabase_enabled = False
        self.stacks_data = self.load_stacks_data()

        # UI Setup
        self.setup_ui()
        
        # Init
        self.init_supabase()
        self.refresh_stack_list()
        self.check_log_queue()
        
        # Check available techs on startup
        self.check_available_techs()

    def run(self):
        self.root.mainloop()

    # --- Data & Logic ---
    def init_supabase(self):
        try:
            load_dotenv()
            url = os.environ.get('SUPABASE_URL')
            key = os.environ.get('SUPABASE_KEY')
            
            if url and key:
                self.supabase = create_client(url, key)
                if self.test_supabase_connection():
                    self.supabase_enabled = True
                    self.update_status(True)
                    self.add_log("Supabase Connected")
                else:
                    self.update_status(False)
            else:
                self.update_status(False)
        except Exception as e:
            self.add_log(f"Supabase Init Error: {e}")
            self.update_status(False)

    def test_supabase_connection(self):
        try:
            self.supabase.table('techs').select('*').limit(1).execute()
            return True
        except:
            return False

    def update_status(self, connected):
        if hasattr(self, 'status_dot'):
            color = "#22c55e" if connected else "#ef4444"
            text = "Connected" if connected else "Disconnected"
            self.status_dot.configure(fg_color=color)
            self.status_text.configure(text=text, text_color=color)

    def load_stacks_data(self):
        try:
            with open('stacks.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def save_stacks_data(self):
        try:
            with open('stacks.json', 'w', encoding='utf-8') as f:
                json.dump(self.stacks_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.add_log(f"Save Error: {e}")
            return False

    # --- UI Construction ---
    def setup_ui(self):
        # Main Grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1) # Content expands

        # 1. Header (40px)
        self.setup_header()

        # 2. Control Panel (48px)
        self.setup_control_panel()

        # 3. Main Content Area
        self.content_frame = ctk.CTkFrame(self.root, fg_color=COLOR_BG_MAIN, corner_radius=0)
        self.content_frame.grid(row=2, column=0, sticky="nsew")
        
        # Configure Content Frame Grid
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1) # Split View expands
        self.content_frame.grid_rowconfigure(3, weight=0) # Log Panel fixed height
        
        # Top Border (Row 0)
        ctk.CTkFrame(self.content_frame, height=1, fg_color=COLOR_BORDER).grid(row=0, column=0, sticky="ew")

        # 3a. Split View (List + Details) (Row 1)
        self.split_frame = ctk.CTkFrame(self.content_frame, fg_color=COLOR_BG_MAIN, corner_radius=0)
        self.split_frame.grid(row=1, column=0, sticky="nsew")
        
        # Enforce list width
        self.split_frame.grid_columnconfigure(0, minsize=420, weight=0) 
        self.split_frame.grid_columnconfigure(1, weight=1)
        self.split_frame.grid_rowconfigure(0, weight=1)

        self.setup_stack_list()
        self.setup_stack_details()

        # Resizer Bar (Row 2)
        self.resize_bar = tk.Frame(self.content_frame, bg=COLOR_BORDER, height=8, cursor="sb_v_double_arrow")
        self.resize_bar.grid(row=2, column=0, sticky="ew")
        self.resize_bar.bind("<Button-1>", self.start_resize)
        self.resize_bar.bind("<B1-Motion>", self.perform_resize)
        self.resize_bar.bind("<Enter>", lambda e: self.resize_bar.configure(bg="#444444"))
        self.resize_bar.bind("<Leave>", lambda e: self.resize_bar.configure(bg=COLOR_BORDER))

        # 3b. Log Panel (Row 3)
        self.setup_log_panel() # Creates self.log_frame
        self.log_frame.grid(row=3, column=0, sticky="ew")
        
        # 4. Footer (24px)
        self.setup_footer()

    def setup_log_panel(self):
        # Bottom Log Panel
        self.log_frame = ctk.CTkFrame(self.content_frame, height=180, fg_color=COLOR_BG_MAIN, border_width=0)
        self.log_frame.grid_propagate(False) # Fix: Use grid_propagate since children use grid
        
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(self.log_frame, font=self.font_mono, fg_color=COLOR_BG_MAIN, text_color=COLOR_TEXT_MAIN, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.log_text.configure(state="disabled")
        
        # Configure Tags
        try:
            tb = self.log_text._textbox
            tb.tag_config("INFO", foreground="#cccccc")
            tb.tag_config("SUCCESS", foreground="#4ade80")
            tb.tag_config("ERROR", foreground="#f87171")
            tb.tag_config("WARNING", foreground="#facc15")
            tb.tag_config("SEARCH", foreground="#60a5fa")
            tb.tag_config("CRAWL", foreground="#a78bfa")
            tb.tag_config("TIME", foreground="#6b7280")
            tb.tag_config("TIMESTAMP", foreground="#4b5563")
        except: pass

        # Clear Btn (Floating top-right)
        ctk.CTkButton(self.log_frame, text="Clear Output", command=self.clear_log, width=80, height=20, fg_color=COLOR_BG_MAIN, text_color=COLOR_TEXT_GRAY, hover_color="#333333").place(relx=1.0, x=-5, y=5, anchor="ne")

    def start_resize(self, event):
        self.start_y = event.y_root
        self.start_height = self.log_frame.winfo_height()

    def perform_resize(self, event):
        try:
            current_time = time.time()
            if not hasattr(self, 'last_resize_time'):
                self.last_resize_time = 0
            
            # Throttle to ~50fps (20ms)
            if current_time - self.last_resize_time < 0.02:
                return

            self.last_resize_time = current_time
            
            delta = self.start_y - event.y_root # Dragging UP increases height
            new_height = self.start_height + delta
            
            # Limits
            cf_height = self.content_frame.winfo_height()
            if new_height < 50: new_height = 50
            if new_height > cf_height - 100: new_height = cf_height - 100
            
            if new_height != self.log_frame.winfo_height():
                self.log_frame.configure(height=new_height)
                
        except Exception as e:
            pass

    # ... (rest of methods)

    def check_available_techs(self):
        def task():
            try:
                # Run with --check-only
                print("[DEBUG] Running check_available_techs...")
                self.log_queue.put("[INFO] Checking for available technologies...")
                
                process = subprocess.Popen(
                    ["python3", "dynamic_tech_discovery.py", "--check-only"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                out, err = process.communicate()
                print(f"[DEBUG] Check output: {out}")
                if err: print(f"[DEBUG] Check error: {err}")
                
                # Send output to log panel
                if out:
                    for line in out.splitlines():
                        self.log_queue.put(line)
                
                # Parse output for [RESULT] Available: X
                import re
                match = re.search(r"\[RESULT\] Available: (\d+)", out)
                if match:
                    count = match.group(1)
                    print(f"[DEBUG] Found count: {count}")
                    self.root.after(0, lambda: self.update_avail_count(count))
                else:
                    print("[DEBUG] Count not found in output")
                    self.log_queue.put("[WARNING] Could not determine available count.")
            except Exception as e:
                print(f"Check Error: {e}")
                self.log_queue.put(f"[ERROR] Check failed: {e}")
        threading.Thread(target=task, daemon=True).start()

    def update_avail_count(self, count):
        if hasattr(self, 'avail_status'):
            self.avail_status.configure(text=f"Available: {count}")

    def setup_footer(self):
        footer = ctk.CTkFrame(self.root, height=24, fg_color=COLOR_ACCENT, corner_radius=0)
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_propagate(False)

        ctk.CTkLabel(footer, text="Ready", font=self.font_small, text_color="white").pack(side="left", padx=10)
        
        right = ctk.CTkFrame(footer, fg_color=COLOR_ACCENT)
        right.pack(side="right", padx=10)
        
        self.avail_status = ctk.CTkLabel(right, text="Available: Checking...", font=self.font_small, text_color="#e5e5e5")
        self.avail_status.pack(side="left", padx=10)
        
        self.limit_status = ctk.CTkLabel(right, text="Limit: 50", font=self.font_small, text_color="#e5e5e5")
        self.limit_status.pack(side="left", padx=10)
        self.count_status = ctk.CTkLabel(right, text="0 Records", font=self.font_small, text_color="#e5e5e5")
        self.count_status.pack(side="left", padx=10)

    # ... (rest of file)

    def __init__(self):
        # ... (existing init code)
        self.root = ctk.CTk()
        self.root.title("AI Stack List Manager (Updated)")
        self.root.geometry("1400x900")
        self.root.configure(fg_color=COLOR_BG_MAIN)
        
        # Fonts
        self.font_bold = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        self.font_normal = ctk.CTkFont(family="Segoe UI", size=13)
        self.font_small = ctk.CTkFont(family="Segoe UI", size=11)
        self.font_mono = ctk.CTkFont(family="Consolas", size=12)

        # State
        self.log_queue = queue.Queue()
        self.log_text = None
        self.supabase = None
        self.supabase_enabled = False
        self.stacks_data = self.load_stacks_data()

        # UI Setup
        self.setup_ui()
        
        # Init
        self.init_supabase()
        self.refresh_stack_list()
        self.check_log_queue()
        
        # Check available techs on startup
        self.check_available_techs()

    def run(self):
        self.root.mainloop()


    def setup_header(self):
        # Header with bottom border
        header = ctk.CTkFrame(self.root, height=40, fg_color=COLOR_BG_SIDE, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        
        # Bottom border for header
        ctk.CTkFrame(header, height=1, fg_color=COLOR_BORDER).pack(side="bottom", fill="x")

        # Left: Icon & Title
        box = ctk.CTkFrame(header, width=24, height=24, fg_color=COLOR_ACCENT, corner_radius=3)
        box.pack(side="left", padx=(15, 10), pady=8)
        ctk.CTkLabel(box, text="", image=None).pack() 

        ctk.CTkLabel(header, text="Tech Stack Collector", font=("Segoe UI", 14, "bold"), text_color="#e1e1e1").pack(side="left")
        ctk.CTkLabel(header, text="v1.0.3", font=self.font_small, text_color=COLOR_TEXT_GRAY).pack(side="left", padx=8)

        # Right: Status
        # Remove fixed height to allow content to fit, add internal padding
        status_frame = ctk.CTkFrame(header, fg_color="#1e1e1e", border_width=1, border_color="#333333", corner_radius=4)
        status_frame.pack(side="right", padx=15, pady=6) # slightly less pady to allow height
        
        self.status_dot = ctk.CTkFrame(status_frame, width=6, height=6, corner_radius=3, fg_color=COLOR_DANGER)
        self.status_dot.pack(side="left", padx=(10, 5), pady=8) # Adjust padding for vertical center
        self.status_text = ctk.CTkLabel(status_frame, text="Disconnected", font=("Segoe UI", 11), text_color=COLOR_DANGER)
        self.status_text.pack(side="left", padx=(0, 10), pady=2)

    def setup_control_panel(self):
        panel = ctk.CTkFrame(self.root, height=48, fg_color=COLOR_BG_SIDE, corner_radius=0)
        panel.grid(row=1, column=0, sticky="ew")
        panel.grid_propagate(False)
        
        # Helper for buttons
        def create_btn(parent, text, cmd, width=None, color="#3c3c3c", text_color="#e1e1e1", hover_color="#4c4c4c", **kwargs):
            border_col = kwargs.pop("border_color", color)
            corner_rad = kwargs.pop("corner_radius", 2)
            border_wid = kwargs.pop("border_width", 1)
            btn = ctk.CTkButton(parent, text=text, command=cmd, width=width or 30, height=28, 
                                fg_color=color, hover_color=hover_color, text_color=text_color,
                                font=self.font_small, corner_radius=corner_rad, border_width=border_wid, border_color=border_col, **kwargs)
            return btn

        # Left Container
        left_box = ctk.CTkFrame(panel, fg_color=COLOR_BG_SIDE)
        left_box.pack(side="left", padx=15, fill="y")

        # Refresh
        create_btn(left_box, "Refresh", self.refresh_stack_list, width=60).pack(side="left", padx=2, pady=10)
        
        # Sync DB
        create_btn(left_box, "Sync DB", self.sync_with_supabase, width=70, text_color="#60a5fa").pack(side="left", padx=2, pady=10)

        # Separator (Vertical)
        ctk.CTkFrame(left_box, width=1, height=20, fg_color="#444444").pack(side="left", padx=8, pady=14)

        # Limit & Auto Collect Group
        group_frame = ctk.CTkFrame(left_box, fg_color="#1e1e1e", border_width=1, border_color=COLOR_INPUT_BG, corner_radius=2, height=30)
        group_frame.pack(side="left", padx=2, pady=9)
        
        ctk.CTkLabel(group_frame, text="LIMIT", font=("Consolas", 10), text_color=COLOR_TEXT_GRAY).pack(side="left", padx=(8, 4))
        self.limit_entry = ctk.CTkEntry(group_frame, width=40, height=20, fg_color="#252526", border_width=0, 
                                        justify="center", font=("Consolas", 12), text_color="white")
        self.limit_entry.insert(0, "50")
        self.limit_entry.pack(side="left", padx=2)

        create_btn(group_frame, "Auto Collect", self.run_auto_discovery, width=90, color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, corner_radius=2, border_width=0).pack(side="left", padx=2, pady=1)

        # Separator (Vertical)
        ctk.CTkFrame(left_box, width=1, height=20, fg_color="#444444").pack(side="left", padx=8, pady=14)

        # Add / Del
        create_btn(left_box, "+ Add", self.add_new_stack, width=50, color=COLOR_BG_SIDE, hover_color="#3c3c3c").pack(side="left", padx=2)
        create_btn(left_box, "Del", self.delete_selected_stacks, width=50, color=COLOR_BG_SIDE, hover_color="#3c3c3c", text_color="#f87171").pack(side="left", padx=2)

        # Right Container
        right_box = ctk.CTkFrame(panel, fg_color=COLOR_BG_SIDE)
        right_box.pack(side="right", padx=15, fill="y")

        # Website
        create_btn(right_box, "Website", self.open_website, width=70, color="#1e1e1e", border_color="#3c3c3c", text_color="#d1d5db").pack(side="left", padx=8, pady=10)

        # Search
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.refresh_stack_list())
        search_entry = ctk.CTkEntry(right_box, textvariable=self.search_var, placeholder_text="Filter...", 
                                    width=180, height=28, fg_color="#1e1e1e", border_color=COLOR_INPUT_BG,
                                    font=self.font_small)
        search_entry.pack(side="left", pady=10)

    def setup_stack_list(self):
        # Left Panel (Widen to 540px)
        list_frame = ctk.CTkFrame(self.split_frame, width=420, fg_color=COLOR_BG_SIDE, corner_radius=0, border_width=0)
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.grid_propagate(False)
        list_frame.grid_rowconfigure(1, weight=1) # Content expands
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Right border simulation
        ctk.CTkFrame(list_frame, width=1, fg_color="#333333").pack(side="right", fill="y")
        
        # 1. Custom Header
        header_frame = ctk.CTkFrame(list_frame, height=32, fg_color=COLOR_BG_SIDE, corner_radius=0)
        header_frame.pack(side="top", fill="x")
        header_frame.pack_propagate(False)
        
        # Fixed Width Columns Configuration
        # Total 500px, leaving 40px for scrollbar/padding
        self.col_widths = [170, 100, 65, 65] # Name, Cat, Pop, Diff
        
        # Helper to create header cell
        def add_head(x, width, text, anchor="w"):
            f = ctk.CTkFrame(header_frame, width=width, height=32, fg_color="transparent", corner_radius=0)
            f.place(x=x, y=0)
            f.pack_propagate(False)
            lbl = ctk.CTkLabel(f, text=text, font=("Segoe UI", 12, "bold"), text_color="#cccccc")
            lbl.place(relx=0 if anchor=="w" else 0.5, rely=0.5, anchor=anchor if anchor=="w" else "center", x=10 if anchor=="w" else 0)

        x_pos = 0
        add_head(x_pos, self.col_widths[0], "Name"); x_pos += self.col_widths[0]
        add_head(x_pos, self.col_widths[1], "Category"); x_pos += self.col_widths[1]
        add_head(x_pos, self.col_widths[2], "Pop", "center"); x_pos += self.col_widths[2]
        add_head(x_pos, self.col_widths[3], "Diff", "center")
        
        # Header Bottom Border
        ctk.CTkFrame(list_frame, height=1, fg_color="#333333").pack(side="top", fill="x")

        # 2. Scrollable List Body
        self.stack_list_scroll = ctk.CTkScrollableFrame(list_frame, fg_color=COLOR_BG_SIDE, corner_radius=0)
        self.stack_list_scroll.pack(side="top", fill="both", expand=True)
        self.stack_list_scroll.grid_columnconfigure(0, weight=1)
        
        self.list_item_refs = [] # Keep track of row widgets

    def setup_stack_details(self):
        # Right Panel (Flex)
        self.detail_frame = ctk.CTkFrame(self.split_frame, fg_color=COLOR_BG_MAIN, corner_radius=0)
        self.detail_frame.grid(row=0, column=1, sticky="nsew")
        self.detail_frame.grid_rowconfigure(1, weight=1) # Scrollable part expands
        self.detail_frame.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self.detail_frame, height=36, fg_color=COLOR_BG_SIDE, corner_radius=0, border_width=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        
        # Bottom border for Properties header
        ctk.CTkFrame(header, height=1, fg_color=COLOR_BORDER).pack(side="bottom", fill="x")
        
        ctk.CTkLabel(header, text="PROPERTIES", font=("Segoe UI", 11, "bold"), text_color="#cccccc").pack(side="left", padx=15)
        
        # Link Buttons
        link_box = ctk.CTkFrame(header, fg_color=COLOR_BG_SIDE)
        link_box.pack(side="right", padx=10)
        ctk.CTkButton(link_box, text="Web", width=40, height=20, command=self.open_homepage, fg_color=COLOR_BG_SIDE, hover_color="#3c3c3c", text_color="#9ca3af").pack(side="left")
        ctk.CTkButton(link_box, text="Git", width=40, height=20, command=self.open_repo, fg_color=COLOR_BG_SIDE, hover_color="#3c3c3c", text_color="#9ca3af").pack(side="left")

        # Scrollable Content
        self.detail_scroll = ctk.CTkScrollableFrame(self.detail_frame, fg_color=COLOR_BG_MAIN)
        self.detail_scroll.grid(row=1, column=0, sticky="nsew")
        self.detail_scroll.grid_columnconfigure(1, weight=1)

        self._row = 0
        self.create_field("Name", "name_entry")
        self.create_field("Category", "category_combo", widget="combo", values=['Language', 'Framework', 'Library', 'Database', 'DevOps', 'Backend', 'Tool'])
        
        # Popularity
        self.create_label("Popularity")
        pop_box = ctk.CTkFrame(self.detail_scroll, fg_color=COLOR_BG_MAIN)
        pop_box.grid(row=self._row, column=1, sticky="ew", padx=10, pady=2)
        self.pop_slider = ctk.CTkSlider(pop_box, from_=0, to=100, command=lambda v: self.pop_label.configure(text=f"{int(v)}%"), height=16, button_color=COLOR_ACCENT)
        self.pop_slider.pack(side="left", fill="x", expand=True)
        self.pop_label = ctk.CTkLabel(pop_box, text="0%", font=self.font_mono, width=40, text_color=COLOR_TEXT_GRAY)
        self.pop_label.pack(side="left", padx=5)
        self._row += 1

        self.create_field("Difficulty", "diff_combo", widget="combo", values=['Low', 'Medium', 'High'])
        self.create_sep()
        self.create_field("Homepage", "homepage_entry", font="mono")
        self.create_field("GitHub", "repo_entry", font="mono")
        self.create_field("Logo URL", "logo_entry", font="mono")
        self.create_sep()
        self.create_field("Description", "desc_text", widget="text", height=60)
        
        # AI Context
        self.create_label("AI Context", color="#a855f7")
        self.ai_text = ctk.CTkTextbox(self.detail_scroll, height=100, fg_color="#2d2a30", border_color="#581c87", border_width=1, text_color="#e9d5ff", font=self.font_normal)
        self.ai_text.grid(row=self._row, column=1, sticky="ew", padx=10, pady=2)
        self._row += 1

        self.current_stack_index = -1

        # Action Footer
        footer = ctk.CTkFrame(self.detail_frame, height=50, fg_color=COLOR_BG_MAIN)
        ctk.CTkButton(footer, text="Save", command=self.save_current_stack, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, width=80, height=28).pack(side="right")



    def add_log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        
        # Determine Tag
        tag = "INFO"
        if "[SUCCESS]" in msg: tag = "SUCCESS"
        elif "[ERROR]" in msg or "[FAILED]" in msg: tag = "ERROR"
        elif "[WARNING]" in msg: tag = "WARNING"
        elif "[SEARCH]" in msg: tag = "SEARCH"
        elif "[CRAWL]" in msg or "[FETCH]" in msg or "[SCRAPE]" in msg: tag = "CRAWL"
        elif "[TIME]" in msg: tag = "TIME"
        
        # Clean up indentation
        clean_msg = msg.strip()
        
        if self.log_text:
            self.log_text.configure(state="normal")
            
            # Insert Timestamp
            self.log_text.insert("end", f"[{ts}] ", "TIMESTAMP")
            
            # Insert Message with Tag
            self.log_text.insert("end", f"{clean_msg}\n", tag)
            
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

    def clear_log(self):
        if self.log_text:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")

    def check_log_queue(self):
        try:
            while True:
                self.add_log(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self.check_log_queue)

    def refresh_stack_list(self, keep_scroll=False):
        if not keep_scroll:
            self.add_log("Refreshing list...")
        
        # Clear existing items
        for widget in self.stack_list_scroll.winfo_children():
            widget.destroy()
        self.list_item_refs = []
        
        # Reload data only if not keeping scroll (implies just visual refresh? No, refresh usually implies reload)
        # Actually, if we just want to update selection, we shouldn't reload data from disk if we haven't saved.
        # But for now, let's stick to reloading.
        self.stacks_data = self.load_stacks_data()
        q = self.search_var.get().lower()
        
        filtered = [s for s in self.stacks_data if q in s.get('name', '').lower() or q in s.get('category', '').lower()]
        
        for i, s in enumerate(filtered):
            self.create_list_row(s, i)
            
        self.count_status.configure(text=f"{len(filtered)} Records")
        try: self.limit_status.configure(text=f"Limit: {self.limit_entry.get()}")
        except: pass
        if not keep_scroll:
            self.add_log(f"Loaded {len(filtered)} items")

    def create_list_row(self, s, idx):
        # Ensure col_widths exists
        if not hasattr(self, 'col_widths'): self.col_widths = [220, 120, 80, 80]
        total_width = sum(self.col_widths)

        # Row Container - Fixed size, using pack(anchor='nw') to prevent stretching/centering issues
        row_frame = ctk.CTkFrame(self.stack_list_scroll, width=total_width, height=36, fg_color="transparent", corner_radius=0)
        row_frame.pack(anchor="nw", pady=0) 
        row_frame.pack_propagate(False) # Strict size enforcement
        
        # Selection Logic
        if not hasattr(self, 'selected_indices'): self.selected_indices = set()
        is_selected = (idx in self.selected_indices)
        if is_selected: row_frame.configure(fg_color=COLOR_SELECTION)

        # Event Bindings
        def on_enter(e): 
            if idx not in self.selected_indices: row_frame.configure(fg_color="#2a2d2e")
        def on_leave(e): 
            if idx not in self.selected_indices: row_frame.configure(fg_color="transparent")
        def on_click(e): self.on_stack_click(s, idx, e)

        row_frame.bind("<Enter>", on_enter)
        row_frame.bind("<Leave>", on_leave)
        row_frame.bind("<Button-1>", on_click)

        # Helper for cells
        def create_cell(x, width, widget_func):
            f = ctk.CTkFrame(row_frame, width=width, height=36, fg_color="transparent", corner_radius=0)
            f.place(x=x, y=0)
            
            # Bind events to cell frame
            f.bind("<Enter>", on_enter)
            f.bind("<Leave>", on_leave)
            f.bind("<Button-1>", on_click)
            
            w = widget_func(f)
            if w:
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)
                w.bind("<Button-1>", on_click)
            return f

        current_x = 0

        # 1. Name
        def name_widget(parent):
            l = ctk.CTkLabel(parent, text=s.get('name', ''), font=("Segoe UI", 12), text_color="white" if is_selected else "#e1e1e1")
            l.place(relx=0, rely=0.5, anchor="w", x=10)
            return l
        create_cell(current_x, self.col_widths[0], name_widget)
        current_x += self.col_widths[0]

        # 2. Category
        def cat_widget(parent):
            l = ctk.CTkLabel(parent, text=s.get('category', ''), font=("Segoe UI", 11), text_color=COLOR_TEXT_GRAY if not is_selected else "#d1d5db")
            l.place(relx=0, rely=0.5, anchor="w", x=5)
            return l
        create_cell(current_x, self.col_widths[1], cat_widget)
        current_x += self.col_widths[1]

        # 3. Popularity
        def pop_widget(parent):
            l = ctk.CTkLabel(parent, text=f"{int(s.get('popularity', 0))}%", font=("Consolas", 11), text_color=COLOR_TEXT_GRAY if not is_selected else "#d1d5db")
            l.place(relx=0.5, rely=0.5, anchor="center")
            return l
        create_cell(current_x, self.col_widths[2], pop_widget)
        current_x += self.col_widths[2]

        # 4. Difficulty (Text Only, Gray)
        diff = s.get('learning_difficulty')
        d_str = diff.get('label', 'Medium') if isinstance(diff, dict) else (diff if isinstance(diff, str) else 'Medium')
        
        def diff_widget(parent):
            # Simple Text, Gray color to match others
            badge = ctk.CTkLabel(parent, text=d_str, font=("Segoe UI", 11), text_color=COLOR_TEXT_GRAY if not is_selected else "#d1d5db")
            badge.place(relx=0.5, rely=0.5, anchor="center")
            return badge
        create_cell(current_x, self.col_widths[3], diff_widget)

        # Bottom Border (Underline)
        sep = ctk.CTkFrame(self.stack_list_scroll, height=1, fg_color="#2d2d2d")
        sep.pack(fill="x")
        
        self.list_item_refs.append(row_frame)
        
        # Auto-scroll to view if needed (omitted for simplicity in multi-select)

    def on_stack_click(self, s, view_idx, event=None):
        # Find real index
        real_idx = -1
        for i, item in enumerate(self.stacks_data):
            if item.get('name') == s.get('name'):
                real_idx = i
                break
        
        if real_idx != -1:
            # Multi-selection Logic
            ctrl_pressed = (event.state & 0x4) != 0 if event else False # Control key
            cmd_pressed = (event.state & 0x8) != 0 if event else False # Command key (Mac)
            shift_pressed = (event.state & 0x1) != 0 if event else False
            
            if not hasattr(self, 'selected_indices'): self.selected_indices = set()
            if not hasattr(self, 'last_selected_index'): self.last_selected_index = None

            if shift_pressed and self.last_selected_index is not None:
                # Range Selection
                start = min(self.last_selected_index, real_idx)
                end = max(self.last_selected_index, real_idx)
                
                if not (ctrl_pressed or cmd_pressed):
                    self.selected_indices = set()
                
                for i in range(start, end + 1):
                    self.selected_indices.add(i)
            elif ctrl_pressed or cmd_pressed:
                # Toggle
                if real_idx in self.selected_indices:
                    self.selected_indices.remove(real_idx)
                else:
                    self.selected_indices.add(real_idx)
                self.last_selected_index = real_idx
            else:
                # Single select
                self.selected_indices = {real_idx}
                self.last_selected_index = real_idx

            # Update Detail View (Show last clicked)
            if real_idx in self.selected_indices:
                self.load_stack(s, real_idx)
            
            # Update Visuals
            self.refresh_selection_visuals()

    def refresh_selection_visuals(self):
        # We need to map real indices back to view indices if filtering is active
        # But for simplicity, we can just iterate the list_item_refs which matches the current view
        # Wait, list_item_refs matches the filtered view.
        # We need to know which real_idx corresponds to which view_idx.
        # Let's just re-render the list or be smarter.
        # Re-rendering is safest but slow. Let's try to update existing widgets.
        
        # Actually, create_list_row is called during refresh.
        # We need to know if the item in the view is selected.
        # The view items are 'filtered'.
        
        # Let's just re-render for now to be safe and correct with filtering
        self.refresh_stack_list(keep_scroll=True)

    def on_stack_select(self, e):
        pass # Deprecated

    def load_stack(self, s, idx):
        self.current_stack_index = idx # Keep for save_current_stack
        self.name_entry.delete(0, "end"); self.name_entry.insert(0, s.get('name') or '')
        self.category_combo.set(s.get('category') or '')
        self.pop_slider.set(s.get('popularity', 0))
        self.pop_label.configure(text=f"{int(s.get('popularity', 0))}%")
        
        diff = s.get('learning_difficulty')
        self.diff_combo.set(diff.get('label', 'Medium') if isinstance(diff, dict) else (diff if isinstance(diff, str) else 'Medium'))
        
        self.homepage_entry.delete(0, "end"); self.homepage_entry.insert(0, s.get('homepage') or '')
        self.repo_entry.delete(0, "end"); self.repo_entry.insert(0, s.get('repo') or '')
        self.logo_entry.delete(0, "end"); self.logo_entry.insert(0, s.get('logoUrl') or '')
        
        self.desc_text.delete("1.0", "end"); self.desc_text.insert("1.0", s.get('description') or '')
        self.ai_text.delete("1.0", "end"); self.ai_text.insert("1.0", s.get('ai_explanation') or '')

    def save_current_stack(self):
        if self.current_stack_index == -1: return
        s = self.stacks_data[self.current_stack_index]
        
        diff = s.get('learning_difficulty', {})
        if isinstance(diff, dict): diff['label'] = self.diff_combo.get()
        else: diff = {'label': self.diff_combo.get()}

        s.update({
            'name': self.name_entry.get(),
            'category': self.category_combo.get(),
            'popularity': int(self.pop_slider.get()),
            'learning_difficulty': diff,
            'homepage': self.homepage_entry.get(),
            'repo': self.repo_entry.get(),
            'logoUrl': self.logo_entry.get(),
            'description': self.desc_text.get("1.0", "end").strip(),
            'ai_explanation': self.ai_text.get("1.0", "end").strip(),
            'updated_at': datetime.now().isoformat()
        })
        
        if self.save_stacks_data():
            if self.supabase_enabled: self.save_to_supabase(s)
            self.refresh_stack_list()
            messagebox.showinfo("Saved", f"Updated {s['name']}")

    def save_to_supabase(self, s):
        try:
            data = {
                'name': s['name'],
                'slug': s.get('slug') or s['name'].lower().replace(' ', '-'),
                'category': s.get('category'),
                'description': s.get('description'),
                'logo_url': s.get('logoUrl'),
                'popularity': int(s.get('popularity', 0)),
                'updated_at': datetime.now().isoformat()
            }
            self.supabase.table('techs').upsert(data, on_conflict='slug').execute()
            self.add_log(f"Synced {s['name']}")
        except Exception as e:
            self.add_log(f"Sync Fail: {e}")

    def delete_current_stack(self):
        if self.current_stack_index == -1: return
        if not messagebox.askyesno("Delete", "Are you sure?"): return
        del self.stacks_data[self.current_stack_index]
        self.save_stacks_data()
        self.refresh_stack_list()
        self.current_stack_index = -1

    def delete_selected_stacks(self):
        if not hasattr(self, 'selected_indices') or not self.selected_indices:
            return
            
        count = len(self.selected_indices)
        if not messagebox.askyesno("Delete", f"Delete {count} selected item(s)?"): return
        
        # Sort indices in reverse to avoid shifting issues
        indices = sorted(list(self.selected_indices), reverse=True)
        
        for idx in indices:
            if 0 <= idx < len(self.stacks_data):
                stack = self.stacks_data[idx]
                # Sync Delete
                if self.supabase_enabled:
                    self.delete_from_supabase(stack)
                del self.stacks_data[idx]
                
        self.save_stacks_data()
        self.selected_indices = set()
        self.current_stack_index = -1
        self.refresh_stack_list()
        
    def delete_from_supabase(self, s):
        try:
            slug = s.get('slug') or s['name'].lower().replace(' ', '-')
            self.supabase.table('techs').delete().eq('slug', slug).execute()
            self.add_log(f"Deleted {s['name']} from DB")
        except Exception as e:
            self.add_log(f"Delete Fail: {e}")

    def add_new_stack(self):
        new_s = {
            'name': 'New Stack', 'category': 'Tool', 'slug': f'new-{int(time.time())}',
            'popularity': 50, 'learning_difficulty': {'label': 'Medium'}, 
            'updated_at': datetime.now().isoformat(),
            'description': '', 'ai_explanation': ''
        }
        self.stacks_data.insert(0, new_s)
        
        # Immediate Save & Sync
        self.save_stacks_data()
        if self.supabase_enabled:
            self.save_to_supabase(new_s)
            
        # Select the new item
        self.selected_indices = {0}
        self.refresh_stack_list()
        
        # Load into detail view
        self.load_stack(new_s, 0)

    def run_auto_discovery(self):
        try: limit = str(int(self.limit_entry.get()))
        except: limit = "50"
        
        self.add_log(f"Auto Collect (Limit: {limit})...")
        def task():
            try:
                # Use Popen with -u for unbuffered output to capture in real-time
                process = subprocess.Popen(
                    ["python3", "-u", "dynamic_tech_discovery.py", "--max-techs", limit],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, # Merge stderr into stdout
                    text=True,
                    bufsize=1,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # Read output line by line
                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.log_queue.put(line.rstrip())
                
                process.wait()
                
                if process.returncode == 0:
                    self.log_queue.put("Collection Finished")
                    self.root.after(100, self.refresh_stack_list)
                else:
                    self.log_queue.put(f"Process failed with code {process.returncode}")
                    
            except Exception as e:
                self.log_queue.put(f"Error: {e}")
        threading.Thread(target=task, daemon=True).start()

    def sync_with_supabase(self):
        if not self.supabase_enabled: return
        threading.Thread(target=self._sync_task, daemon=True).start()

    def _sync_task(self):
        try:
            self.log_queue.put("Syncing...")
            # (Sync logic omitted for brevity, reusing existing structure if needed or keeping simple)
            # For now, just re-implementing basic fetch to update local
            res = self.supabase.table('techs').select('*').execute()
            if res.data:
                # Simple merge: prefer supabase
                remote = {i['slug']: i for i in res.data}
                local = {i.get('slug'): i for i in self.stacks_data}
                
                for slug, r in remote.items():
                    if slug not in local:
                        self.stacks_data.append(self._convert(r))
                    # Update logic could be more complex
                self.save_stacks_data()
                self.log_queue.put("Sync Complete")
                self.root.after(100, self.refresh_stack_list)
        except Exception as e:
            self.log_queue.put(f"Sync Error: {e}")

    # --- Helpers ---
    def create_label(self, text, color=COLOR_TEXT_GRAY):
        lbl = ctk.CTkLabel(self.detail_scroll, text=text, font=self.font_small, text_color=color)
        lbl.grid(row=self._row, column=0, sticky="ne", padx=(10, 10), pady=6)

    def create_field(self, label, attr, widget="entry", values=None, height=None, font="normal"):
        self.create_label(label)
        f = self.font_mono if font == "mono" else self.font_normal
        
        if widget == "entry":
            w = ctk.CTkEntry(self.detail_scroll, fg_color=COLOR_INPUT_BG, border_color=COLOR_INPUT_BG, font=f, height=28, text_color="white")
        elif widget == "combo":
            w = ctk.CTkComboBox(self.detail_scroll, values=values or [], fg_color=COLOR_INPUT_BG, border_color=COLOR_INPUT_BG, button_color=COLOR_INPUT_BG, font=f, height=28, text_color="white")
        elif widget == "text":
            w = ctk.CTkTextbox(self.detail_scroll, height=height or 60, fg_color=COLOR_INPUT_BG, border_color=COLOR_INPUT_BG, font=f, text_color="white")
        
        w.grid(row=self._row, column=1, sticky="ew", padx=10, pady=2)
        setattr(self, attr, w)
        self._row += 1

    def create_sep(self):
        ctk.CTkFrame(self.detail_scroll, height=1, fg_color=COLOR_BORDER).grid(row=self._row, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        self._row += 1

    def setup_footer(self):
        footer = ctk.CTkFrame(self.root, height=24, fg_color=COLOR_ACCENT, corner_radius=0)
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_propagate(False)

        ctk.CTkLabel(footer, text="Ready", font=self.font_small, text_color="white").pack(side="left", padx=10)
        
        right = ctk.CTkFrame(footer, fg_color=COLOR_ACCENT)
        right.pack(side="right", padx=10)
        
        self.limit_status = ctk.CTkLabel(right, text="Limit: 50", font=self.font_small, text_color="#e5e5e5")
        self.limit_status.pack(side="left", padx=10)
        self.count_status = ctk.CTkLabel(right, text="0 Records", font=self.font_small, text_color="#e5e5e5")
        self.count_status.pack(side="left", padx=10)
        ctk.CTkLabel(right, text="Python Backend", font=self.font_small, text_color="#e5e5e5").pack(side="left", padx=10)

    def _convert(self, r):
        return {
            'name': r.get('name'), 'slug': r.get('slug'), 'category': r.get('category'),
            'description': r.get('description'), 'logoUrl': r.get('logo_url'),
            'popularity': r.get('popularity'), 'updated_at': r.get('updated_at')
        }

    def open_website(self): webbrowser.open("http://stackload.wiki")
    def open_homepage(self): 
        if self.homepage_entry.get(): webbrowser.open(self.homepage_entry.get())
    def open_repo(self):
        if self.repo_entry.get(): webbrowser.open(self.repo_entry.get())

def main():
    app = TechStackManager()
    app.run()

if __name__ == "__main__":
    main()