import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import subprocess
import sys
from k_interpreter import KInterpreter  # Import the updated interpreter

class TextLineNumbers(tk.Canvas):
    def __init__(self, master, text_widget, **kwargs):
        super().__init__(master, **kwargs)
        self.text_widget = text_widget
        self.text_widget.bind("<<Change>>", self.redraw)
        self.text_widget.bind("<Configure>", self.redraw)

    def redraw(self, *args):
        self.delete("all")

        i = self.text_widget.index("@0,0")
        while True :
            dline= self.text_widget.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(2, y, anchor="nw", text=linenum, fill="green", font=("Consolas", 24))
            i = self.text_widget.index(f"{i}+1line")

class CustomText(scrolledtext.ScrolledText):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<<Change>>", self._on_change)
        self.bind("<KeyRelease>", self._on_change)

    def _on_change(self, event=None):
        self.event_generate("<<Change>>")

def execute_k_script(script):
    """
    Integrate with the K language interpreter.
    """
    try:
        interpreter = KInterpreter()
        result = interpreter.interpret(script)
        return result
    except Exception as e:
        return f"Error executing script: {e}"

class KTerminal:
    def __init__(self, root):
        self.root = root
        self.root.title("K Language Terminal")
        self.root.geometry("800x600")
        self.root.configure(bg="#121212")  # Set main window background color

        # Create Menu
        self.create_menu()

        # Create Frame for Line Numbers and Text Area
        self.main_frame = tk.Frame(self.root, bg="#121212")
        self.main_frame.pack(expand=True, fill='both')

        # Create Text Area with Line Numbers
        self.create_text_area()

        # Create Run Button
        self.create_run_button()

    def create_menu(self):
        menu = tk.Menu(self.root, bg="#121212", fg="green", activebackground="#1e1e1e", activeforeground="green")
        self.root.config(menu=menu)

        # File Menu
        file_menu = tk.Menu(menu, tearoff=0, bg="#121212", fg="green", activebackground="#1e1e1e", activeforeground="green")
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_script, activebackground="#1e1e1e")
        file_menu.add_command(label="Open...", command=self.open_script, activebackground="#1e1e1e")
        file_menu.add_command(label="Save", command=self.save_script, activebackground="#1e1e1e")
        file_menu.add_command(label="Save As...", command=self.save_as_script, activebackground="#1e1e1e")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, activebackground="#1e1e1e")

        # Help Menu
        help_menu = tk.Menu(menu, tearoff=0, bg="#121212", fg="green", activebackground="#1e1e1e", activeforeground="green")
        menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about, activebackground="#1e1e1e")

    def create_text_area(self):
        # Create Text Area
        self.text_area = CustomText(self.main_frame, wrap=tk.NONE, font=("Consolas", 12),
                                    bg="#1e1e1e", fg="#00FF00", insertbackground="#00FF00",
                                    selectbackground="#333333", insertwidth=2)
        self.text_area.pack(side=tk.RIGHT, expand=True, fill='both')

        # Create Line Numbers
        self.line_numbers = TextLineNumbers(self.main_frame, self.text_area, width=50, bg="#121212")
        self.line_numbers.pack(side=tk.LEFT, fill='y')

    def create_run_button(self):
        run_button = tk.Button(
            self.root,
            text="Run",
            command=self.run_script,
            bg="#2e2e2e",          # Dark button background
            fg="#00FF00",          # Green text
            activebackground="#3e3e3e",
            activeforeground="#00FF00",
            font=("Helvetica", 12, "bold"),
            bd=0,
            padx=10,
            pady=5
        )
        run_button.pack(side=tk.BOTTOM, pady=10)

    def run_script(self):
        script = self.text_area.get("1.0", tk.END).strip()
        if not script:
            messagebox.showwarning("No Script", "Please write a script before running.")
            return
        output = execute_k_script(script)
        self.show_output(output)

    def show_output(self, output):
        output_window = tk.Toplevel(self.root)
        output_window.title("Output")
        output_window.geometry("600x400")
        output_window.configure(bg="#121212")

        output_text = scrolledtext.ScrolledText(
            output_window,
            wrap=tk.WORD,
            font=("Consolas", 12),
            bg="#1e1e1e",
            fg="#00FF00",
            insertbackground="#00FF00",
            selectbackground="#333333",
            bd=0
        )
        output_text.pack(expand=True, fill='both')
        output_text.insert(tk.END, output)
        output_text.config(state=tk.DISABLED)

    def new_script(self):
        if messagebox.askyesno("New Script", "Are you sure you want to create a new script? Unsaved changes will be lost."):
            self.text_area.delete("1.0", tk.END)
            if hasattr(self, 'current_file'):
                del self.current_file

    def open_script(self):
        file_path = filedialog.askopenfilename(filetypes=[("K Scripts", "*.k"), ("All Files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    script = file.read()
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert(tk.END, script)
                self.current_file = file_path
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {e}")

    def save_script(self):
        if hasattr(self, 'current_file') and self.current_file:
            try:
                script = self.text_area.get("1.0", tk.END)
                with open(self.current_file, 'w') as file:
                    file.write(script)
                messagebox.showinfo("Saved", "Script saved successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
        else:
            self.save_as_script()

    def save_as_script(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".k", filetypes=[("K Scripts", "*.k"), ("All Files", "*.*")])
        if file_path:
            try:
                script = self.text_area.get("1.0", tk.END)
                with open(file_path, 'w') as file:
                    file.write(script)
                self.current_file = file_path
                messagebox.showinfo("Saved", "Script saved successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")

    def show_about(self):
        messagebox.showinfo("About", "K Language Terminal\nCreated with Python and Tkinter.\n\nYour new programming language: K")

def main():
    root = tk.Tk()
    app = KTerminal(root)
    root.mainloop()

if __name__ == "__main__":
    main()
