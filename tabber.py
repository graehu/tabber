import tkinter
import tomllib
import shlex
import os
import subprocess
try: from idlelib.tooltip import Hovertip
except Exception: pass

master=tkinter.Tk()
master.title("Tabs and Buttons")
master.geometry("350x275")
master.configure(borderwidth=5)
curdir = os.path.dirname(__file__)
os.chdir(curdir)

photo=tkinter.PhotoImage(file='tabber.png')
master.wm_iconphoto(False, photo.subsample(4,4))
photo = photo.subsample(8,8)


# Create Frames
tabs = tkinter.Frame(master)
butts = tkinter.Frame(master)
spacer = tkinter.Frame(master)

# "Styling"
tabs.config(bg="grey")
spacer.config(height=2, bg="grey")
settings = tomllib.load(open("tabber.toml", "rb"))
 
tabs.pack(side="top", expand=False, fill="both")
spacer.pack(side="top", expand=False, fill="both")
butts.pack(side="top", expand=True, fill="both")


def show_tab(widget):
    name = widget.cget("text")
    tab_butts = tab_dict[name]["buttons"]
    for child in butts.winfo_children(): child.pack_forget()
    for button in tab_butts: button.pack(side="top", expand=True, fill="both")


def run_cmd(cmd): subprocess.run(cmd, shell=True)

tab_dict = {}
img_map = {"": photo.subsample(2,2) }

def get_image(path, subsample=(1,1)):
    if not path in img_map and os.path.exists(path):
        img_map[path] = tkinter.PhotoImage(file=path).subsample(*subsample)
    return img_map[path]


def create_tab(tab):
    if "tab" in tab:
        conf = tab["tab"]
        tab_name = conf["name"] if "name" in conf else "tab_name"
        tab_icon = conf["icon"] if "icon" in conf else ""
        tab_icon_subsample = conf["icon_subsample"] if "icon_subsample" in conf else (1,1)
        image = get_image(tab_icon, tab_icon_subsample)
        tab_button = tkinter.Button(tabs, text=tab_name, image=image, compound="left")
        tab_button.pack(side="left")
        tab_button.bind("<Button-1>", lambda x: show_tab(x.widget))
        tab_butts = []
        for sec in tab:
            if sec == "tab": continue
            icon = tab[sec]["icon"] if "icon" in tab[sec] else ""
            cmd = tab[sec]["command"] if "command" in tab[sec] else "no_command"
            default_name = os.path.basename(shlex.split(cmd)[0])
            name = tab[sec]["name"] if "name" in tab[sec] else default_name
            icon_subsample = tab[sec]["icon_subsample"] if "icon_subsample" in tab[sec] else (1,1)
            image = get_image(icon, icon_subsample)
            button = tkinter.Button(butts, text=name, image=image, compound="left")
            button.bind("<Button-1>", lambda x, cmd=cmd: run_cmd(cmd))
            try: Hovertip(button, ">"+cmd, 500)
            except Exception: pass
            tab_butts.append(button)
        tab_dict[tab_name] = {"tab": tab_button, "buttons": tab_butts}



while "includes" in settings:
    inc_settings = []
    for include in settings["includes"]:
         inc_settings.append(tomllib.load(open(include, "rb")))
    del settings["includes"]
    for new_settings in inc_settings:
        settings = {**settings, **new_settings}

for tab in settings:
    new_tab = settings[tab]
    if isinstance(new_tab, dict):
        if not "tab" in new_tab: new_tab["tab"] = {"name":tab}
        create_tab(new_tab)

show_tab(tabs.winfo_children()[0])

master.mainloop()