import tkinter
import tomllib
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
    def __init__(self, cmd, show_status, cmd_file, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd = cmd
        self.show_status = show_status
        self.cmd_file = cmd_file
        self.bind("<Button-1>", lambda x, y=self: y.on_l_click())
        self.bind("<Button-3>", lambda x, y=self: y.on_r_click())
    def _run_thread(self):
        self.config(state="disabled")
        if self.show_status: self.config(bg="grey80")
        ret = subprocess.Popen(self.cmd, creationflags=subprocess.CREATE_NEW_CONSOLE).wait()
        if self.show_status and ret == 0: self.config(bg="green3", activebackground="green2")
        elif self.show_status: self.config(bg="red2",activebackground="red1")
        self.config(state="normal")
    def on_l_click(self):
        if self.thread == None or not self.thread.is_alive():
            self.thread = threading.Thread(target=lambda x: x._run_thread(), args=[self])
            self.thread.start()
    def on_r_click(self):
        webbrowser.open(self.cmd_file)
        pass

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

# Handle settings
try: settings_file = sys.argv[1] if os.path.exists(sys.argv[1]) else os.path.dirname(__file__)+"/tabber.toml"
except: settings_file = os.path.dirname(__file__)+"/tabber.toml"
settings = tomllib.load(open(settings_file, "rb"))
curdir = os.path.dirname(settings_file)
os.chdir(curdir)

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

included = []
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

# Setup Tkinter

master=tkinter.Tk()
title = settings["title"] if "title" in settings else "tabber"
master.title(title)
master.geometry("350x275")
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
    global current_tab
    if current_tab: current_tab.configure(relief=tkinter.RAISED)
    current_tab = widget
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

show_tab(tabs.winfo_children()[0])

master.mainloop()