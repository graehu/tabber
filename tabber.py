import tkinter
import tomllib
import shlex
import zlib
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

_grampy_icon = zlib.decompress(b'x\x9c\xeb\x0c\xf0s\xe7\xe5\x92\xe2b``\xe0\xf5\xf4p\t\x02\xd2\x02 \xcc\xc1\x06$\xe5?\xffO\x04R\x8c\xc5A\xeeN\x0c\xeb\xce\xc9\xbc\x04rX\xd2\x1d}\x1d\x19\x186\xf6s\xffId\x05\xf29\x0b<"\x8b\x19\x18\xc4TA\x98\xd13H\xe5\x03P\xd0\xce\xd3\xc51\xc4\xc2?\xf9\x87\xbf\xa2\x84\x1f\x9b\x81\x81\x81\xc2\x86\xab,+4x\xee\x1c\xd3\xec\x7f\xd4\x94\x9b)\xc0\xba\x83\xc1\xec\xe7\xc34\x06K\x86v\xc6\xdb\x07\xcc\x14\x93c\x1a\xc2\xf4\x14\xe4x*\x99\xff\xfdgg\xe8\xb9\xb8\xa9\xf3\xfa\x8e\x1f\xf9@\x93\x18<]\xfd\\\xd69%4\x01\x00 >/\xb2')
photo = tkinter.PhotoImage(data=_grampy_icon)

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
def create_tab(tab):
    if "tab" in tab:
        conf = tab["tab"]
        tab_name = conf["name"] if "name" in conf else "tab_name"
        tab_icon = conf["icon"] if "icon" in conf else ""
        if os.path.exists(tab_icon): image = tkinter.PhotoImage(file=tab_icon)
        else: image = photo
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
            if os.path.exists(icon): image = tkinter.PhotoImage(file=icon)
            else: image = photo
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