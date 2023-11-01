import tkinter
import tomllib
import shlex
import os
import sys
import subprocess
try: from idlelib.tooltip import Hovertip
except Exception: pass
import threading
import webbrowser

class CmdButton(tkinter.Button):
    cmd = ""
    show_status = False
    thread = None
    cmd_file = ""
    menu = None
    def __init__(self, cmd, show_status, cmd_file, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd = cmd
        self.show_status = show_status
        self.cmd_file = cmd_file
        self.bind("<Button-1>", lambda x, y=self: y.on_l_click())
        self.menu = tkinter.Menu(self, tearoff = 0)
        self.menu.bind("<Leave>", lambda x, m=self.menu: m.unpost())
        self.menu.add_command(label ="edit button", command=lambda s=self: webbrowser.open(s.cmd_file))
        self.menu.add_command(label ="copy command", command=lambda s=self: set_clipboard(s.cmd))
        self.bind("<Button-3>", lambda x, s=self: s.show_menu(x))
        # m.add_separator()
        # m.add_command(label ="Rename")
    def show_menu(self, event): 
        try: 
            self.menu.tk_popup(event.x_root, event.y_root) 
        finally: 
            self.menu.grab_release()

    def _run_thread(self):
        self.config(state="disabled")
        if self.show_status: self.config(bg="grey80")
        if os.name == "nt": ret = subprocess.Popen(self.cmd, creationflags=subprocess.CREATE_NEW_CONSOLE).wait()
        else: ret = subprocess.Popen(shlex.split(self.cmd)).wait()
        if self.show_status and ret == 0: self.config(bg="green3", activebackground="green2")
        elif self.show_status: self.config(bg="red2",activebackground="red1")
        self.config(state="normal")
    def on_l_click(self):
        if self.thread == None or not self.thread.is_alive():
            self.thread = threading.Thread(target=lambda x: x._run_thread(), args=[self])
            self.thread.start()

class pushd:
    path = ""
    old_path = ""
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.old_path = os.getcwd()

    def __enter__(self):
        os.chdir(self.path)
        return self

    def __exit__(self, type, value, traceback):
        os.chdir(self.old_path)


def set_clipboard(text):
    master.clipboard_clear()
    master.clipboard_append(text)
    master.update() # now it stays on the clipboard after the window is closed

def recursive_abspath(dictionary, in_key):
    for key, value in dictionary.items():
        if type(value) is dict:
            recursive_abspath(value, in_key)
        elif key == in_key:
            dictionary[key] = os.path.abspath(dictionary[key])

def recursive_add_keyval(dictionary, in_key, in_value):
    for key, value in dictionary.items():
        if type(value) is dict:
            value[in_key] = in_value
            recursive_add_keyval(value, in_key, in_value)

# Handle settings
try: settings_file = sys.argv[1] if os.path.exists(sys.argv[1]) else os.path.dirname(__file__)+"/tabber.toml"
except: settings_file = os.path.dirname(__file__)+"/tabber.toml"
settings_file = os.path.abspath(settings_file)

# Setup Tkinter
master=tkinter.Tk()
master.geometry("350x275")
tab_num = 0
included = []

def build_widgets():
    global included
    for c in master.winfo_children(): c.destroy()
    settings = {"includes": [settings_file]}
    curdir = os.path.dirname(settings_file)
    os.chdir(curdir)
    old_included = included
    included = []
    try:
        while "includes" in settings:
            inc_settings = []
            for include in settings["includes"]:
                include = os.path.abspath(include)
                if not include in included:
                    included.append(include)
                    inc = tomllib.load(open(include, "rb"))
                    recursive_add_keyval(inc, "origin_toml", include)
                    with pushd(os.path.dirname(include)):                
                        if "includes" in inc: inc["includes"] = [os.path.abspath(p) for p in inc["includes"]]
                        recursive_abspath(inc, "icon")
                    inc_settings.append(inc)
            del settings["includes"]
            for new_settings in inc_settings:
                settings = {**settings, **new_settings}
    except Exception as e:
        error_message = include +": \n"+str(e)
        lab = tkinter.Label(master, text=error_message)
        lab.place(relx=0.5, rely=0.5, anchor=tkinter.CENTER)
        if os.path.exists(include):
            webbrowser.open(include)
            if not include in old_included: old_included.append(include)

        master.after(100, lambda x: master.lift())
        included = old_included
        return

    title = settings["title"] if "title" in settings else "tabber"
    master.title(title)
    master.configure(borderwidth=5)

    photo=tkinter.PhotoImage(file=os.path.dirname(__file__)+'/tabber.png')
    master.wm_iconphoto(False, photo.subsample(4,4))
    photo = photo.subsample(8,8)


    # Create Frames
    tabs = tkinter.Frame(master)
    butts = tkinter.Frame(master)
    spacer = tkinter.Frame(master)

    # "Styling"
    tabs.config(bg="grey")
    spacer.config(height=2, bg="grey")

    
    tabs.pack(side="top", expand=False, fill="both")
    spacer.pack(side="top", expand=False, fill="both")
    butts.pack(side="top", expand=True, fill="both")

    current_tab = None
    def show_tab(widget : tkinter.Widget):
        nonlocal current_tab
        global tab_num
        if current_tab: current_tab.configure(relief=tkinter.RAISED)
        current_tab = widget
        tab_num = tabs.winfo_children().index(current_tab)
        name = widget.cget("text")
        tab_butts = tab_dict[name]["buttons"]
        for child in butts.winfo_children(): child.pack_forget()
        for button in tab_butts: button.pack(side="top", expand=True, fill="both")
        master.after(1, lambda widget=widget:widget.configure(relief=tkinter.RIDGE))


    tab_dict = {}
    img_map = {"": None } # photo.subsample(2,2)

    def get_image(path, subsample=(1,1)):
        if not path in img_map and os.path.exists(path):
            img_map[path] = tkinter.PhotoImage(file=path).subsample(*subsample)
        return img_map[path]


    def create_tab(tab_name, tab):
        tab_icon = ""
        tab_icon_subsample = (1,1)
        tab_button = tkinter.Button(tabs)
        tab_button.pack(side="left")
        tab_button.bind("<Button-1>", lambda x: show_tab(x.widget))
        tab_butts = []
        for sec in tab:
            section = tab[sec]
            if isinstance(section, dict):
                icon = section["icon"] if "icon" in section else ""
                toml_file = section["origin_toml"] if "origin_toml" in section else settings_file
                cmd = section["command"] if "command" in section else "no_command"
                show_status = section["show_status"] if "show_status" in section else False
                name = section["name"] if "name" in section else sec
                icon_subsample = section["icon_subsample"] if "icon_subsample" in section else (1,1)
                image = get_image(icon, icon_subsample)
                button = CmdButton(cmd, show_status, toml_file, butts, text=name, image=image, compound="left")
                try: Hovertip(button, ">"+cmd, 500)
                except Exception: pass
                tab_butts.append(button)
            elif sec == "name": tab_name = section
            elif sec == "icon": tab_icon = section
            elif sec == "icon_subsample": tab_icon = section
        image = get_image(tab_icon, tab_icon_subsample)
        tab_button.configure(text=tab_name, image=image, compound="left")
        tab_dict[tab_name] = {"tab": tab_button, "buttons": tab_butts}


    for tab in settings:
        new_tab = settings[tab]
        if isinstance(new_tab, dict): create_tab(tab, new_tab)

    if len(tabs.winfo_children()) > tab_num:
        show_tab(tabs.winfo_children()[tab_num])
    else:
        show_tab(tabs.winfo_children()[0])
    master.bind("<Control-s>", lambda x: build_widgets())

build_widgets()
mod_times = {}
def watch_includes():
    global included
    wants_build = False
    for inc in included:
        if inc in mod_times:
            if mod_times[inc] != os.path.getmtime(inc):
                mod_times[inc] = os.path.getmtime(inc)
                wants_build = True
        else:
            mod_times[inc] = os.path.getmtime(inc)
    if wants_build: build_widgets()
    master.after(500, watch_includes)

watch_includes()
master.mainloop()