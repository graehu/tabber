import tkinter
import tkinter.messagebox
import tomllib
import os
import re
import platform
import sys
import subprocess
import shlex
try: from idlelib.tooltip import Hovertip
except Exception: pass
import threading
import webbrowser
import datetime
import time
import signal
import math
import shutil
import smtplib
import email.mime.text as mime_text
import email.mime.multipart as mime_multipart
import email.mime.application as mime_application

html = """
<html>
  <body>
    Hello,
    <br>
    button: {button}<br>
    result: {status}<br>
    time elapsed: {time_taken}<br>
    <br>
    Thanks,<br>
    Tabber
  </body>
</html>
"""

def send_report(login, host, recipients, report, attachments=None):
    if not login or not host or not recipients or not report:
        print("failed to send mail, required arguments not given.")
        return
    message = mime_multipart.MIMEMultipart('html')
    message["Subject"] = f"Tabber - {report['button']} - {report['status']}"
    message["From"] = login[0]
    message["To"] = ", ".join(recipients)

    message_str = html
    message_str = message_str.format_map(report)

    message_mime = mime_text.MIMEText(message_str, 'html')
    message.attach(message_mime)
    if attachments:
        for f in attachments:
            if f is None or (not os.path.exists(f)):
                print("failed to send attachement: "+str(f))
                continue
            with open(f, "rb") as fil:
                part = mime_application.MIMEApplication(
                    fil.read(),
                    Name=os.path.basename(f)
                )
            # After the file is closed
            part['Content-Disposition'] = (
                'attachment; filename="%s"'
                % os.path.basename(f)
            )
            message.attach(part)

    try:
        server = smtplib.SMTP(host)
        server.ehlo()
        if len(login) == 2: server.login(*login)
        server.send_message(message)
        server.quit()
    except Exception as e:
        print("failed to send mail using smpt, trying smptssl")
        print(e)
        try:
            server = smtplib.SMTP_SSL(host)
            server.ehlo()
            if len(login) == 2: server.login(*login)
            server.send_message(message)
            server.quit()
        except Exception as e:
            print("failed to send mail using smptssl")
            print(e)


if platform.system() == "Windows":
    import ctypes
    myappid = 'graehu.tabber.tabber.1' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


editors = ["code", "subl", "notepad++", "gedit", "notepad"]
editor = None
for edit in editors:
    if shutil.which(edit):
        editor = shutil.which(edit); break


def kill_proc(proc):
    if platform.system() == 'Windows':
        subprocess.Popen("TASKKILL /F /PID {pid} /T".format(pid=proc.pid), shell=True)
    elif platform.system() == 'Linux':
        os.kill(proc.pid, signal.SIGTERM)
    else:
        proc.kill()


def open_file(in_path, line=0):
    path = os.path.abspath(in_path)
    if os.path.isfile(in_path):
        if platform.system() == 'Windows':
            if "code" in editor:
                subprocess.run([editor, "--goto", path+f":{line}:0"], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.run([editor, path], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            if "/code" in editor:
                subprocess.run([editor, "--goto", path+f":{line}:0"])
            else: subprocess.run([editor, path])
    else:
        if os.path.isdir(path): webbrowser.open(path)
        # Never open a file without an editor, it may run.
        else: webbrowser.open(os.path.dirname(path))


class TabButton(tkinter.Button):
    keyname = ""
    rows = 0
    def __init__(self, keyname, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keyname = keyname


class CmdButton(tkinter.Button):
    cmd = ""
    text = ""
    text_strvar = None
    tab = None
    keyname = ""
    show_status = False
    thread = None
    cmd_file = ""
    cmd_line = 0
    menu = None
    log_fmt = ""
    last_log = ""
    last_ret = 0
    confirm = False
    all_buttons = []
    is_running = False
    conf_globals = {}
    mail_conditions = []
    def __init__(self, tab, keyname, cmd, show_status, cmd_file, cmd_line, log_dir, confirm, mail_conditions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = self.cget("text")
        self.tab = tab
        self.keyname = keyname
        self.cmd = cmd
        self.show_status = show_status
        self.cmd_file = cmd_file
        self.cmd_line = cmd_line
        self.menu = tkinter.Menu(self, tearoff = 0)
        self.text_strvar = tkinter.StringVar(self, self.text)
        self.config(textvariable=self.text_strvar)
        # edit_menu = tkinter.Menu(self.menu, tearoff = 0)
        self.conf_globals = g_conf_globals.copy()
        self.mail_conditions = mail_conditions

        # self.configure(command=lambda y=self: y.on_l_click())
        self.bind("<Button-1>", lambda x, y=self: y.on_l_click())
        self.bind("<Shift-Button-1>", lambda x, y=self: y.on_shift_l_click())
        self.menu.add_command(label="edit button", command=lambda s=self: open_file(s.cmd_file, s.cmd_line))
        # self.menu.add_cascade(label="files", menu=edit_menu)

        for path in shlex.split(cmd):
            if os.path.exists(path) and os.path.isfile(path):
                self.menu.add_command(label ="edit "+os.path.basename(path), command=lambda s=self, p=path: open_file(p))
            elif os.path.exists(path) and os.path.isdir(path):
                try:
                    for file in os.listdir(path):
                        if file in cmd:
                            path = "/".join((path,file))
                            self.menu.add_command(label ="edit "+file, command=lambda s=self, p=path: open_file(p))
                except Exception: pass

        self.menu.add_command(label ="copy command", command=lambda s=self: set_clipboard(s.cmd))
        self.menu.add_command(label ="open log", command=lambda s=self: open_file(s.last_log))
        log_dir = (os.path.dirname(cmd_file)+"/"+log_dir).replace("\\", "/")
        self.menu.add_command(label ="open log folder", command=lambda s=self: open_file(log_dir))
        self.bind("<Button-3>", lambda x, s=self: s.show_menu(x))
        
        self.log_fmt = log_dir+"/"+os.path.basename(log_dir)+"_{now}.log"
        
        if os.path.exists(log_dir+"/") and os.listdir(log_dir+"/"):
            self.last_log = sorted([log_dir+"/"+l for l in os.listdir(log_dir)], key=lambda x: os.path.getmtime(x))[-1]
        self.confirm = confirm
        CmdButton.all_buttons.append(self)
        # Making room for time stats.
        self.text_strvar.set(self.text+"\n--------")

    def show_menu(self, event):
        try:
            bindids = []
            def pop_unpost(self):
                nonlocal bindids
                self.menu.unpost()
                if self.thread == None or not self.thread.is_alive():
                    self.after(1, lambda x=self: x.config(state="normal"))
                for b in bindids: master.unbind(*b)
                return "break"

            for butt in CmdButton.all_buttons:
                if butt == self: continue
                pop_unpost(butt)

            self.config(state="disabled")
            self.menu.post(event.x_root, event.y_root)
            bindids = [["<Escape>", master.bind("<Escape>", lambda x, y=self: pop_unpost(y))]]
            bindids += [["<Button-1>", master.bind("<Button-1>", lambda x, y=self: pop_unpost(y))]]
            bindids += [["<FocusOut>", master.bind("<FocusOut>", lambda x, y=self: pop_unpost(y))]]

        finally:
            self.menu.grab_release()
            return "break"


    def _run_thread(self):
        global g_is_running
        if self.confirm and not tkinter.messagebox.askyesno("Confirm", f"Are you sure you want to run '{self.text}'?"): return
        if self.cget("state") != "disabled":
            print(f"running '{self.text}': {self.cmd}")
            self.is_running = True
            wants_mail = True
            self.config(state="disabled")
            now  = datetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
            log_path = self.log_fmt.format(now=now)
            log_path = os.path.abspath(log_path)
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            self.last_log = log_path
            if self.show_status: self.config(bg="grey80")
            with open(log_path, "w") as writer:
                with open(log_path, "r") as reader:
                    cmd_window = tkinter.Toplevel()
                    cmd_window.title(self.text+" > "+self.cmd)
                    cmd_window.config(width=300, height=200)
                    txt = tkinter.Text(cmd_window)
                    txt.configure(state=tkinter.DISABLED, bg="black", fg="lightgrey")
                    txt.pack(expand=True, fill="both")
                    start_time = time.time()
                    proc = subprocess.Popen(self.cmd, stdout=writer, stderr=subprocess.STDOUT, shell=True)
                    def stop_process():
                        nonlocal wants_mail, proc
                        wants_mail = False
                        kill_proc(proc)
                    
                    cmd_window.protocol("WM_DELETE_WINDOW", lambda: stop_process())
                    self.menu.add_separator()
                    self.menu.add_command(label ="stop process", command=lambda: stop_process())

                    # Run loop
                    current_text = self.text
                    while proc.poll() == None:

                        time_text = self.text+"\n"+str(datetime.timedelta(seconds=int(time.time()-start_time)))
                        if self.show_status and current_text != time_text:
                            current_text = time_text
                            self.text_strvar.set(current_text)

                        line = reader.readline(1024*4)
                        if line:
                            txt.configure(state=tkinter.NORMAL)
                            while line:
                                txt.insert(tkinter.END, line)
                                line = reader.readline(1024*4)
                            txt.configure(state=tkinter.DISABLED)
                            txt.see(tkinter.END)

                        time.sleep(0.1)
                        if not g_is_running: kill_proc(proc); break

                    ret = proc.wait()
                    self.menu.delete("stop process")
                    self.menu.delete(self.menu.index(tkinter.END))
                    cmd_window.destroy()
                print("\n",file=writer)
                print("[tabber]", file=writer)
                print("cmd    : "+self.cmd, file=writer)
                print("time   : "+str(datetime.timedelta(seconds=time.time()-start_time)), file=writer)
                print("success: "+str(bool(ret==0)) + f" ({ret})", file=writer)
                if wants_mail and self.mail_conditions and ((ret==0) in self.mail_conditions):
                    send_report(self.conf_globals["mail_login"],
                                self.conf_globals["mail_host"],
                                self.conf_globals["mail_to"],
                                {
                                    "button": self.text,
                                    "status": str(bool(ret==0)) + f" ({ret})",
                                    "time_taken": str(datetime.timedelta(seconds=time.time()-start_time))
                                },
                                [self.last_log])

            self.is_running = False

            if self.show_status and ret == 0: self.config(bg="green3", activebackground="green2")
            elif self.show_status: self.config(bg="red2",activebackground="red1")
            else: self.config(bg="#e0e0e0",activebackground="#f0f0f0")
            self.last_ret = ret
            if ret != 0: open_file(log_path)
            self.config(state="normal")


    def run(self):
        if self.thread == None or not self.thread.is_alive():
            self.thread = threading.Thread(target=lambda x: x._run_thread(), args=[self])
            confirm = self.confirm
            self.confirm = False
            self.thread.start()
            self.thread.join()
            self.confirm = confirm
            return self.last_ret
        return -1


    def on_l_click(self):
        if self.thread == None or not self.thread.is_alive():
            self.thread = threading.Thread(target=lambda x: x._run_thread(), args=[self])
            self.thread.start()
        return "break"


    def on_shift_l_click(self):
        if self.thread == None or not self.thread.is_alive():
            if not self in g_button_queue:
                g_button_queue.append(self)
                self.config(bg="yellow", activebackground="lightyellow")
            else:
                g_button_queue.remove(self)
                self.config(bg="#e0e0e0",activebackground="#f0f0f0")
        return "break"


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
master.minsize(256, 128+64)
tab_num = 0
included = []
img_map = { "": None }
g_show_tab = None # TODO: this is a bit of a hack, too much stuff happens inside of build_widgets, fix later.
g_button_queue = []
g_conf_globals = {}
g_is_running = True

def build_widgets():
    global g_show_tab
    global included
    CmdButton.all_buttons.clear()
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
                    print("loading "+include)
                    inc = tomllib.load(open(include, "rb"))
                    recursive_add_keyval(inc, "origin_toml", include)

                    lines = open(include, "r", encoding="utf-8").readlines()
                    lines = zip(lines, range(1, len(lines)))
                    for k1 in inc:
                        if isinstance(inc[k1], dict):
                            for k2 in inc[k1]:
                                if isinstance(inc[k1][k2], dict):
                                    tab_name = f"[{k1}.{k2}]"
                                    # print("finding: "+tab_name)
                                    for l,n in lines:
                                        if tab_name in l:
                                            inc[k1][k2]["line"] = n
                                            break
                                    # if "line" in inc[k1][k2]:
                                    #     print(k1+"."+k2+" "+str(inc[k1][k2]["line"]))

                    with pushd(os.path.dirname(include)):
                        if "includes" in inc: inc["includes"] = [os.path.abspath(p) for p in inc["includes"]]
                        recursive_abspath(inc, "icon")
                    inc_settings.append(inc)
            del settings["includes"]
            for new_settings in inc_settings:
                settings = {**settings, **new_settings}
    except Exception as e:
        error_message = include +": \n"+str(e)
        line = 0
        if match := re.search("\(at line ([0-9]+)", str(e)): line = int(match.group(1))
        lab = tkinter.Label(master, text=error_message)
        lab.place(relx=0.5, rely=0.5, anchor=tkinter.CENTER)
        master.configure(bg="#d9d9d9")
        if os.path.exists(include):
            open_file(include, line)
            if not include in old_included: old_included.append(include)

        master.after(100, lambda x: master.lift())
        included = old_included
        return

    title = settings["title"] if "title" in settings else "tabber - "+settings_file
    master.title(title)
    master.configure(bg="grey", borderwidth=5)
    photo=tkinter.PhotoImage(file=os.path.dirname(__file__)+'/tabber.png')
    master.wm_iconphoto(False, photo.subsample(4,4))
    photo = photo.subsample(8,8)


    # Create Frames
    tabs = tkinter.Frame(master)
    butts = tkinter.Frame(master)

    # "Styling"
    tabs.config(bg="grey",borderwidth=5)
    butts.config(bg="grey", borderwidth=5)
    tabs.pack(side="top", expand=False, fill="both")
    butts.pack(side="top", expand=True, fill="both")

    current_tab = None
    def show_tab(widget : tkinter.Widget):
        nonlocal current_tab
        global tab_num
        if current_tab: current_tab.configure(relief=tkinter.RAISED)
        current_tab = widget
        tab_num = tabs.winfo_children().index(current_tab)
        name = widget.keyname
        tab_butts = tab_dict[name]["buttons"]

        num_butts = len(tab_butts)
        bx = current_tab.rows
        if not bx: bx = int(math.sqrt(num_butts))

        for child in butts.winfo_children():
            child.pack_forget()
            if not "cmdbutton" in str(child): child.destroy()

        frames = []
        for i in range(0, bx):
            frame = tkinter.Frame(butts)
            frame.pack(side="left", expand=True, fill="both")
            frames.append(frame)

        for i in range(0, num_butts):
            tab_butts[i].pack(in_=frames[i%bx], side="top", expand=True, fill="both")
            tab_butts[i].lift()

        inv_remainder =(num_butts*bx-(num_butts%bx))%bx
        remainder =  num_butts%bx
        for i in range(0, inv_remainder):
            spacer = tkinter.Button(butts)
            spacer.config(text="\n") # becaues I add the ---- to buttons now. I should do something better.
            spacer.pack(in_=frames[(i+remainder)%bx], side="top", expand=True, fill="both")
            spacer.config(state="disabled")

        master.after(1, lambda widget=widget:widget.configure(relief=tkinter.RIDGE))

    g_show_tab = show_tab
    tab_dict = {}

    def get_image(path, subsample=(1,1)):
        if not path in img_map and os.path.exists(path):
            img_map[path] = tkinter.PhotoImage(file=path).subsample(*subsample)
        return img_map[path]


    def create_tab(tab_name, tab):
        log_dir = "logs/"+tab_name+"/"
        keyname = tab_name
        tab_icon = ""
        tab_icon_subsample = (1,1)
        tab_button = TabButton(keyname, tabs)
        tab_button.pack(side="left", expand=True, fill="both")
        tab_button.bind("<Button-1>", lambda x: show_tab(x.widget))
        tab_butts = []
        tab_configs = {}
        # TODO: all of this is going to get very messy, might want a better way to handle these.
        defaults = {}
        for sec in tab:
            section = tab[sec]
            if isinstance(section, dict):
                icon = section["icon"] if "icon" in section else (defaults["icon"] if "icon" in defaults else "")
                cmd_line = section["line"] if "line" in section else 0
                toml_file = section["origin_toml"] if "origin_toml" in section else settings_file
                cmd = section["command"] if "command" in section else "no_command"
                show_status = section["show_status"] if "show_status" in section else (defaults["show_status"] if "show_status" in defaults else False)
                name = section["name"] if "name" in section else sec
                confirm = section["confirm"] if "confirm" in section else (defaults["confirm"] if "confirm" in defaults else True)
                mail_conditions = section["mail_conditions"] if "mail_conditions" in section else (defaults["mail_conditions"] if "mail_conditions" in defaults else [])
                icon_subsample = section["icon_subsample"] if "icon_subsample" in section else (1,1)
                image = get_image(icon, icon_subsample)
                button = CmdButton(tab_button, sec, cmd, show_status, toml_file, cmd_line, log_dir+sec, confirm, mail_conditions, butts, text=name, image=image, compound="left")
                configs = {}
                for k in section:
                    if k in ["command", "icon", "name", "image", "confirm"]: continue
                    if k in button.configure().keys(): configs.update({k:section[k]})
                try:
                    button.configure(configs)
                except Exception as e:
                    open_file(toml_file)
                    tkinter.messagebox.showerror(f"ERROR '[{tab_name}.{sec}]'", str(e))
                try: Hovertip(button, ">"+cmd, 500)
                except Exception: pass
                tab_butts.append(button)
            elif sec.startswith("buttons_"): defaults[sec.replace("buttons_", "")] = section
            elif sec == "name": tab_name = section
            elif sec == "icon": tab_icon = section
            elif sec == "icon_subsample": tab_icon = section
            elif sec == "image": pass
            elif sec == "rows": tab_button.rows = section if isinstance(section, int) else 0
            elif sec in tab_button.configure().keys(): tab_configs.update({sec:section})
        image = get_image(tab_icon, tab_icon_subsample)
        tab_button.configure(text=tab_name, image=image, compound="left")
        try:
            tab_button.configure(tab_configs)
        except Exception as e:
            open_file(toml_file)
            tkinter.messagebox.showerror(f"ERROR '[{keyname}]'", str(e))
        tab_dict[keyname] = {"tab": tab_button, "buttons": tab_butts}


    for tab in settings:
        new_tab = settings[tab]
        if isinstance(new_tab, dict):
            create_tab(tab, new_tab)
        else:
            g_conf_globals[tab] = settings[tab]

    if len(tabs.winfo_children()) > tab_num:
        show_tab(tabs.winfo_children()[tab_num])
    else:
        show_tab(tabs.winfo_children()[0])

    return tab_dict

def run_buttons(in_tabs):
    runners = []
    buttons = []
    try:
        for arg in sys.argv:
            if arg.startswith("-run="):
                arg = arg.replace("-run=", "", 1)
                arg = [a.split(".") for a in arg.split(",")]
                for a in arg:
                    if len(a) != 2: tkinter.messagebox.showerror("Run Failure", f"{'.'.join(a)} is not a button in tabber!\n\nRun cancelled."); return

                runners.extend(arg)

        for t, b in runners:
            if t in in_tabs:
                but = next(iter([tb for tb in in_tabs[t]["buttons"] if tb.keyname == b]), None)
                if but: buttons.append(but)
                else: tkinter.messagebox.showerror("Run Failure", f"{t}.{b} is not a button in tabber!\n\nRun cancelled."); return
            else: tkinter.messagebox.showerror("Run Failure", f"{t} is not a tab in tabber!\n\nRun cancelled."); return

        for button in buttons:
            button.on_shift_l_click()

    except Exception as e:
        argv = " ".join(sys.argv[1:])
        tkinter.messagebox.showerror("Run Failure", f"Uncaught Exception: \n\n{argv}\n\n{str(e)}\n\nRun cancelled.")


def button_queue():
    global g_button_queue, g_is_running
    while g_is_running:
        time.sleep(0.5)
        if g_button_queue and not any([b.is_running for b in CmdButton.all_buttons]):
            button = g_button_queue.pop(0)
            g_show_tab(button.tab)
            if button.run() != 0:
                tkinter.messagebox.showerror("Run Failure", f"{button.keyname} returned non zero!\n\nRun cancelled.")
                for button in g_button_queue:
                    button.config(bg="#e0e0e0",activebackground="#f0f0f0")
                g_button_queue = []



tab_dict = build_widgets()
run_buttons(tab_dict)

queue_thread = threading.Thread(target=button_queue)
queue_thread.start()

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
    if wants_build:
        if not any([b.is_running for b in CmdButton.all_buttons]):
            build_widgets()
        else:
            tkinter.messagebox.showerror("Reload Failure", "Command in progress!\n\nSave the config after the command finishes or open a new instance of tabber.")
    master.after(500, watch_includes)

watch_includes()
master.mainloop()
g_is_running = False