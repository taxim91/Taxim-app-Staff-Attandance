import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
from datetime import datetime, timedelta

# --- CONFIGURATION ---
SHIFT_START_HOUR = 11  # 11:00 AM
SHIFT_START_MINUTE = 0
STANDARD_SHIFT_HOURS = 9 # 11am to 8pm is 9 hours

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('smart_attendance.db')
    c = conn.cursor()
    # Table includes columns for Late and Overtime calculations
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
                    staff_id TEXT, 
                    date TEXT, 
                    time_in TEXT, 
                    time_out TEXT, 
                    late_minutes INTEGER DEFAULT 0,
                    overtime_minutes INTEGER DEFAULT 0,
                    PRIMARY KEY (staff_id, date)
                )''')
    conn.commit()
    conn.close()

# --- CALCULATION LOGIC ---
def calculate_late(current_time_obj):
    # Create a time object for 11:00 AM today
    shift_start = current_time_obj.replace(hour=SHIFT_START_HOUR, minute=SHIFT_START_MINUTE, second=0, microsecond=0)
    
    if current_time_obj > shift_start:
        diff = current_time_obj - shift_start
        return int(diff.total_seconds() / 60) # Return minutes late
    return 0

def calculate_overtime(time_in_str, time_out_obj):
    fmt = "%Y-%m-%d %H:%M:%S"
    t_in = datetime.strptime(time_in_str, fmt)
    
    # Calculate total duration worked
    duration = time_out_obj - t_in
    total_minutes = int(duration.total_seconds() / 60)
    standard_minutes = STANDARD_SHIFT_HOURS * 60
    
    if total_minutes > standard_minutes:
        return total_minutes - standard_minutes # Return extra minutes
    return 0

# --- BUTTON FUNCTIONS ---
def clock_in():
    staff_id = id_entry.get().strip()
    if not staff_id:
        messagebox.showwarning("Error", "Enter Staff ID")
        return

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    late_mins = calculate_late(now)
    
    conn = sqlite3.connect('smart_attendance.db')
    c = conn.cursor()
    try:
        c.execute("""INSERT INTO attendance (staff_id, date, time_in, late_minutes) 
                     VALUES (?, ?, ?, ?)""", 
                     (staff_id, date_str, time_str, late_mins))
        conn.commit()
        
        msg = f"Clocked IN at {now.strftime('%H:%M')}"
        if late_mins > 0:
            msg += f"\nNote: {late_mins} minutes LATE."
        
        messagebox.showinfo("Success", msg)
        status_label.config(text=msg, fg="blue")
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "You already clocked in today!")
    finally:
        conn.close()

def clock_out():
    staff_id = id_entry.get().strip()
    if not staff_id:
        messagebox.showwarning("Error", "Enter Staff ID")
        return

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect('smart_attendance.db')
    c = conn.cursor()
    
    # Get the check-in time to calculate overtime
    c.execute("SELECT time_in FROM attendance WHERE staff_id=? AND date=?", (staff_id, date_str))
    result = c.fetchone()
    
    if result:
        overtime_mins = calculate_overtime(result[0], now)
        
        c.execute("""UPDATE attendance 
                     SET time_out = ?, overtime_minutes = ? 
                     WHERE staff_id = ? AND date = ?""", 
                     (time_str, overtime_mins, staff_id, date_str))
        conn.commit()
        
        msg = f"Clocked OUT at {now.strftime('%H:%M')}"
        if overtime_mins > 0:
            msg += f"\nOvertime recorded: {overtime_mins} mins."
            
        messagebox.showinfo("Success", msg)
        status_label.config(text=msg, fg="green")
    else:
        messagebox.showerror("Error", "You haven't clocked in today!")
    conn.close()

# --- VIEW REPORT (Monthly Sheet) ---
def view_report():
    report_win = tk.Toplevel(root)
    report_win.title("Attendance Sheet")
    report_win.geometry("600x400")
    
    # Define Table Columns
    cols = ("ID", "Date", "In", "Out", "Late (min)", "Extra (min)")
    tree = ttk.Treeview(report_win, columns=cols, show='headings')
    
    for col in cols:
        tree.heading(col, text=col)
        tree.column(col, width=90)
        
    tree.pack(fill=tk.BOTH, expand=True)
    
    # Fetch Data
    conn = sqlite3.connect('smart_attendance.db')
    c = conn.cursor()
    c.execute("SELECT staff_id, date, time_in, time_out, late_minutes, overtime_minutes FROM attendance")
    rows = c.fetchall()
    
    for row in rows:
        # Format times to look cleaner (Time only, remove date part for display)
        t_in = row[2].split(' ')[1] if row[2] else ""
        t_out = row[3].split(' ')[1] if row[3] else ""
        tree.insert("", tk.END, values=(row[0], row[1], t_in, t_out, row[4], row[5]))
        
    conn.close()

# --- UI SETUP ---
root = tk.Tk()
root.title("Smart Attendance System")
root.geometry("400x350")

tk.Label(root, text="Staff Attendance Log", font=("Helvetica", 16, "bold")).pack(pady=10)
tk.Label(root, text="Shift: 11:00 AM - 08:00 PM", fg="gray").pack()

tk.Label(root, text="Enter Staff ID:", font=("Arial", 11)).pack(pady=(15,5))
id_entry = tk.Entry(root, font=("Arial", 14), justify='center')
id_entry.pack(pady=5)

# Button Frame
f = tk.Frame(root)
f.pack(pady=15)
tk.Button(f, text="CLOCK IN", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=12, command=clock_in).pack(side=tk.LEFT, padx=10)
tk.Button(f, text="CLOCK OUT", bg="#f44336", fg="white", font=("Arial", 10, "bold"), width=12, command=clock_out).pack(side=tk.LEFT, padx=10)

# Status Label
status_label = tk.Label(root, text="System Ready", font=("Arial", 9))
status_label.pack(pady=10)

# View Report Button
tk.Button(root, text="View Monthly Sheet", command=view_report).pack(pady=10)

init_db()
root.mainloop()
