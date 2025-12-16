import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import tkinter.font as tkFont
import random
import os

# ===== Global variables =====
CSV_FILE_PATH = None
df = None
all_categories = []


def load_file(filepath):
    """Load and validate a CSV or Excel file"""
    global df, all_categories, CSV_FILE_PATH

    try:
        # Determine file type and load accordingly
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        elif filepath.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(filepath)
        else:
            messagebox.showerror("Error", "Please select a CSV or Excel file (.csv, .xlsx, .xls)")
            return False

        CSV_FILE_PATH = filepath

        # Validate required columns
        required_cols = {"Deutsch", "English", "Category"}
        if not required_cols.issubset(df.columns):
            messagebox.showerror(
                "Error",
                f"File must have columns: 'Deutsch', 'English', 'Category'\n\nFound columns: {', '.join(df.columns)}"
            )
            return False

        # Add optional columns if missing
        if "TimesShown" not in df.columns:
            df["TimesShown"] = 0
        if "Status" not in df.columns:
            df["Status"] = "normal"

        # Get categories
        all_categories = sorted(df["Category"].dropna().unique().tolist())

        # Save with new columns if needed
        save_df()

        messagebox.showinfo("Success", f"Loaded {len(df)} entries from {len(all_categories)} categories!")
        return True

    except Exception as e:
        messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
        return False


def save_df():
    """Save dataframe to file"""
    if CSV_FILE_PATH and df is not None:
        try:
            if CSV_FILE_PATH.endswith('.csv'):
                df.to_csv(CSV_FILE_PATH, index=False)
            elif CSV_FILE_PATH.endswith(('.xlsx', '.xls')):
                df.to_excel(CSV_FILE_PATH, index=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")


def open_file():
    """Open file dialog to select data file"""
    filepath = filedialog.askopenfilename(
        title="Select your vocabulary file",
        filetypes=[
            ("CSV files", "*.csv"),
            ("Excel files", "*.xlsx *.xls"),
            ("All files", "*.*")
        ]
    )

    if filepath:
        if load_file(filepath):
            # Update UI with new categories
            setup_category_inputs()
            file_label.config(text=f"File: {os.path.basename(filepath)}")


def setup_category_inputs():
    """Dynamically create category input fields"""
    global category_vars

    # Clear existing category widgets
    for widget in category_frame.winfo_children():
        widget.destroy()

    category_vars = {}

    if not all_categories:
        ttk.Label(category_frame, text="No categories loaded").pack()
        return

    ttk.Label(category_frame, text="Category counts (default 1):",
              font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(5, 5))

    for i, cat in enumerate(all_categories):
        sv = tk.StringVar(value="1")
        category_vars[cat] = sv

        row_frame = ttk.Frame(category_frame)
        row_frame.pack(fill='x', pady=2)

        ttk.Label(row_frame, text=cat, width=20).pack(side='left')
        ttk.Entry(row_frame, textvariable=sv, width=5).pack(side='left', padx=5)


# ===== sampling logic =====
def sample_items(category_counts, review_count, display_mode):
    """Sample items based on category counts and review items"""
    if df is None or len(df) == 0:
        messagebox.showerror("Error", "No data loaded. Please open a file first.")
        return []

    selected = []
    base_pool = df[df["Status"] != "mastered"].copy()

    # 1) Pick review items first
    review_pool = base_pool[base_pool["Status"] == "review"]
    if review_count > 0 and len(review_pool) > 0:
        review_count = min(review_count, len(review_pool))
        review_sample = review_pool.sample(review_count)

        for idx, row in review_sample.iterrows():
            text = format_display_text(row, display_mode)
            selected.append((idx, text))

        base_pool = base_pool.drop(index=review_sample.index)

    # 2) Category-based sampling
    total_cat_requested = sum(category_counts.values())

    if total_cat_requested == 0 and review_count == 0:
        try:
            n = int(num_entries.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number.")
            return []

        n = min(n, len(base_pool))
        sample_rows = base_pool.sample(n)

        for idx, row in sample_rows.iterrows():
            text = format_display_text(row, display_mode)
            selected.append((idx, text))
        return selected

    # Sample from each category
    for cat, needed in category_counts.items():
        if needed <= 0:
            continue

        pool_cat = base_pool[base_pool["Category"] == cat]
        if len(pool_cat) == 0:
            continue

        needed = min(needed, len(pool_cat))
        sample_rows = pool_cat.sample(needed)

        for idx, row in sample_rows.iterrows():
            text = format_display_text(row, display_mode)
            selected.append((idx, text))

        base_pool = base_pool.drop(index=sample_rows.index)

    return selected


def format_display_text(row, mode):
    """Format text based on display mode"""
    if mode == "Deutsch":
        return row["Deutsch"]
    elif mode == "English":
        return row["English"]
    else:
        return f"{row['Deutsch']}  —  {row['English']}"


# ===== UI callbacks =====
current_selection_indices = []


def show_entries():
    """Show sampled entries"""
    global current_selection_indices

    if df is None:
        messagebox.showerror("Error", "Please load a file first!")
        return

    mode = display_mode.get()

    # Collect category counts
    cat_counts = {}
    for cat, sv in category_vars.items():
        try:
            val = int(sv.get())
        except ValueError:
            val = 0
        cat_counts[cat] = val

    # Review count
    try:
        review_n = int(review_entries.get())
    except ValueError:
        review_n = 0

    results = sample_items(cat_counts, review_n, mode)
    if not results:
        return

    # Update TimesShown
    for idx, _ in results:
        df.at[idx, "TimesShown"] = int(df.at[idx, "TimesShown"]) + 1
    save_df()

    # Update UI
    text_output.delete(1.0, tk.END)
    for row in tree.get_children():
        tree.delete(row)

    current_selection_indices = []
    for idx, text in results:
        current_selection_indices.append(idx)
        row = df.loc[idx]

        text_output.insert(tk.END, text + "\n")
        tree.insert("", tk.END, values=(
            row["Deutsch"],
            row["English"],
            row["Category"],
            row["Status"],
            row["TimesShown"],
        ))


def get_selected_df_index_from_tree():
    """Get the dataframe index of selected tree item"""
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("No selection", "Please select a word in the table.")
        return None

    item_id = selected[0]
    all_items = tree.get_children()
    pos = all_items.index(item_id)

    if pos >= len(current_selection_indices):
        return None
    return current_selection_indices[pos]


def mark_review():
    idx = get_selected_df_index_from_tree()
    if idx is None:
        return
    df.at[idx, "Status"] = "review"
    save_df()
    refresh_tree_rows()


def mark_mastered():
    idx = get_selected_df_index_from_tree()
    if idx is None:
        return
    df.at[idx, "Status"] = "mastered"
    save_df()
    refresh_tree_rows()


def clear_status():
    idx = get_selected_df_index_from_tree()
    if idx is None:
        return
    df.at[idx, "Status"] = "normal"
    save_df()
    refresh_tree_rows()


def refresh_tree_rows():
    """Refresh tree display"""
    for row in tree.get_children():
        tree.delete(row)
    for idx in current_selection_indices:
        row = df.loc[idx]
        tree.insert("", tk.END, values=(
            row["Deutsch"],
            row["English"],
            row["Category"],
            row["Status"],
            row["TimesShown"],
        ))


# ===== UI setup =====
root = tk.Tk()
root.title("German-English Trainer")
root.geometry("1000x700")

root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)

main_frame = ttk.Frame(root, padding=10)
main_frame.grid(row=0, column=0, sticky="NSEW")

# ===== Top: File selection =====
file_frame = ttk.Frame(main_frame)
file_frame.grid(row=0, column=0, columnspan=2, sticky="EW", pady=(0, 10))

ttk.Button(file_frame, text="📁 Open Vocabulary File", command=open_file).pack(side='left', padx=5)
file_label = ttk.Label(file_frame, text="No file loaded", foreground="gray")
file_label.pack(side='left', padx=10)

# ===== Left: Controls =====
controls = ttk.Frame(main_frame)
controls.grid(row=1, column=0, sticky="N", padx=(0, 10))

# Scrollable category frame
category_canvas = tk.Canvas(controls, width=250, height=400)
category_scrollbar = ttk.Scrollbar(controls, orient="vertical", command=category_canvas.yview)
category_frame = ttk.Frame(category_canvas)

category_canvas.create_window((0, 0), window=category_frame, anchor="nw")
category_canvas.configure(yscrollcommand=category_scrollbar.set)

category_canvas.pack(side="left", fill="both", expand=True)
category_scrollbar.pack(side="right", fill="y")

category_frame.bind(
    "<Configure>",
    lambda e: category_canvas.configure(scrollregion=category_canvas.bbox("all"))
)

category_vars = {}

# Control panel below categories
control_panel = ttk.Frame(main_frame)
control_panel.grid(row=2, column=0, sticky="EW", pady=(10, 0))

ttk.Label(control_panel, text="Fallback entries:").grid(row=0, column=0, sticky="W")
num_entries = tk.StringVar(value="5")
ttk.Entry(control_panel, textvariable=num_entries, width=6).grid(row=0, column=1, sticky="W", padx=5)

ttk.Label(control_panel, text="Display:").grid(row=1, column=0, sticky="W", pady=(8, 0))
display_mode = tk.StringVar(value="Deutsch")
ttk.Radiobutton(control_panel, text="Deutsch", variable=display_mode, value="Deutsch").grid(row=2, column=0, sticky="W")
ttk.Radiobutton(control_panel, text="English", variable=display_mode, value="English").grid(row=2, column=1, sticky="W")
ttk.Radiobutton(control_panel, text="Both", variable=display_mode, value="Both").grid(row=2, column=2, sticky="W")

ttk.Label(control_panel, text="Review items:").grid(row=3, column=0, sticky="W", pady=(10, 0))
review_entries = tk.StringVar(value="0")
ttk.Entry(control_panel, textvariable=review_entries, width=6).grid(row=3, column=1, sticky="W", padx=5)

ttk.Button(control_panel, text="Show", command=show_entries).grid(row=4, column=0, columnspan=3, pady=10)

# ===== Right: Output =====
output_frame = ttk.Frame(main_frame)
output_frame.grid(row=1, column=1, rowspan=2, sticky="NSEW")
output_frame.rowconfigure(1, weight=1)
output_frame.columnconfigure(0, weight=1)

big_font = tkFont.Font(family="Helvetica", size=16)

text_output = tk.Text(output_frame, height=12, wrap="word", font=big_font)
text_output.grid(row=0, column=0, sticky="NSEW")

columns = ("Deutsch", "English", "Category", "Status", "TimesShown")
tree = ttk.Treeview(output_frame, columns=columns, show="headings", height=10)
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=140, anchor="w")
tree.grid(row=1, column=0, sticky="NSEW", pady=(8, 0))

flag_frame = ttk.Frame(output_frame)
flag_frame.grid(row=2, column=0, sticky="W", pady=(8, 0))
ttk.Button(flag_frame, text="Mark as REVIEW", command=mark_review).grid(row=0, column=0, padx=5)
ttk.Button(flag_frame, text="Mark as MASTERED", command=mark_mastered).grid(row=0, column=1, padx=5)
ttk.Button(flag_frame, text="Clear status", command=clear_status).grid(row=0, column=2, padx=5)

# Configure grid weights
main_frame.rowconfigure(1, weight=1)
main_frame.columnconfigure(1, weight=1)

root.mainloop()