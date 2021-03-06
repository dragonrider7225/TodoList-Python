import tkinter as tk
import os
import os.path
from tkinter import filedialog as fd
from tkinter import ttk
from tkinter.constants import *

def bitsToBytes(bits, numBytes):
    ret = b""
    for i in range(numBytes):
        ret = bytes([bits & ((1 << 8) - 1)]) + ret
        bits >>= 8
    return ret

def bytesToBits(s):
    ret = 0
    while s:
        ret <<= 8
        ret += s[0]
        s = s[1:]
    return ret

class BoundedRollover(type):
    def __call__(cls, *args, **kwargs):
        ret = type.__call__(cls, *cls.roll(args), **kwargs)
        return ret

class Datetime(metaclass=BoundedRollover):
    NUM_MIN_BITS, NUM_HR_BITS, NUM_DAY_BITS, NUM_MNT_BITS = 6, 5, 5, 4
    NUM_YR_BITS = 21
    NUM_BITS = NUM_MIN_BITS + NUM_HR_BITS + NUM_DAY_BITS + NUM_MNT_BITS + NUM_YR_BITS
    MIN_BITS, HR_BITS = (1 << NUM_MIN_BITS) - 1, (1 << NUM_HR_BITS) - 1
    DAY_BITS, MNT_BITS = (1 << NUM_DAY_BITS) - 1, (1 << NUM_MNT_BITS) - 1
    YR_BITS = (1 << NUM_YR_BITS) - 1

    def __init__(self, year, month, day, hour, minute):
        self.__yr = year
        self.__mnt = month
        self.__day = day
        self.__hr = hour
        self.__min = minute

    def __compare(self, other, l):
        return l(self.toStoreFmt(), other.toStoreFmt())

    def __lt__(self, other):
        return self.__compare(other, lambda s, o: s < o)

    def __gt__(self, other):
        return self.__compare(other, lambda s, o: s > o)

    def __eq__(self, other):
        return self.__compare(other, lambda s, o: s == o)

    def __le__(self, other):
        return self.__compare(other, lambda s, o: s <= o)

    def __ge__(self, other):
        return self.__compare(other, lambda s, o: s >= o)

    def __ne__(self, other):
        return self.__compare(other, lambda s, o: s != o)

    @property
    def year(self):
        return self.__yr

    @property
    def month(self):
        return self.__mnt

    @property
    def day(self):
        return self.__day

    @property
    def hour(self):
        return self.__hr

    @property
    def minute(self):
        return self.__min

    @staticmethod
    def roll(times):
        times = list(times)
        if len(times) != 5:
            raise ValueError("Datetime instantiation requires exactly five explicit positional arguments")
        YR, MNT, DAY, HR, MIN = (0, 1, 2, 3, 4)
        minphr = 60
        hrpday = 24
        long = lambda yr: 31
        short = lambda yr: 30
        mntpyr = 12
        if not (0 <= times[MIN] < minphr):
            times[HR] += times[MIN] // minphr
            times[MIN] %= minphr
        if not (0 <= times[HR] < hrpday):
            times[DAY] += times[HR] // hrpday
            times[HR] %= hrpday
        if not (0 <= times[MNT] < mntpyr):
            times[YR] += times[MNT] // mntpyr
            times[MNT] %= mntpyr
        while times[DAY] < 0:
            times[DAY] += daypmnt[times[MNT] - 1](times[YR])
            times[MNT] -= 1
            if times[MNT] < 0:
                times[MNT] += 12
                times[YR] -= 1
        days = Datetime.days(times[YR], times[MNT])
        while times[DAY] >= days:
            times[DAY] -= days
            times[MNT] += 1
            if times[MNT] >= 12:
                times[MNT] -= 12
                times[YR] += 1
            days = Datetime.days(times[YR], times[MNT])
        return tuple(times)

    def toStoreFmt(self):
        """Converts the Datetime object to a sequence of Datetime.NUM_MIN_BITS
+ Datetime.NUM_HR_BITS + Datetime.NUM_DAY_BITS + Datetime.NUM_MNT_BITS +
Datetime.NUM_YR_BITS bits. This function is the inverse of
Datetime.fromStoreFmt(...) when the year of the Datetime object is at least 0
and at most Datetime.YR_BITS.
"""
        ret = Datetime.YR_BITS & self.__yr
        ret <<= Datetime.NUM_MNT_BITS
        ret += self.__mnt
        ret <<= Datetime.NUM_DAY_BITS
        ret += self.__day
        ret <<= Datetime.NUM_HR_BITS
        ret += self.__hr
        ret <<= Datetime.NUM_MIN_BITS
        ret += self.__min
        return ret

    @staticmethod
    def fromStoreFmt(bits):
        """Converts the bits to a Datetime object. All bits except the
Datetime.NUM_MNT_BITS + Datetime.NUM_DAY_BITS + Datetime.NUM_HR_BITS +
Datetime.NUM_MIN_BITS least significant bits are used as the year. This
function is the inverse of Datetime.toStoreFmt(...) when the year of the
Datetime object is at least 0 and at most Datetime.YR_BITS.
"""
        min = bits & Datetime.MIN_BITS
        bits >>= Datetime.NUM_MIN_BITS
        hr = bits & Datetime.HR_BITS
        bits >>= Datetime.NUM_HR_BITS
        day = bits & Datetime.DAY_BITS
        bits >>= Datetime.NUM_DAY_BITS
        mnt = bits & Datetime.MNT_BITS
        bits >>= Datetime.NUM_MNT_BITS
        return Datetime(bits, mnt, day, hr, min)

    @staticmethod
    def days(year, month, dpm=([lambda yr: 31] +
            [(lambda yr: 29 if (yr%4==0 and (yr%100!=0 or yr%400==0)) else 28)]
            + [lambda yr: 31, lambda yr: 30] * 2 + [lambda yr: 31] * 2 +
            [lambda yr: 30, lambda yr: 31] * 2)):
        return dpm[month](year)

    def __str__(self):
        return f"{self.__yr:04}{self.__mnt+1:02}{self.__day+1:02}T{self.__hr:02}{self.__min:02}"

    def __repr__(self):
        return f"Datetime({self.__yr}, {self.__mnt}, {self.__day}, {self.__hr}, {self.__min})"

SUN, MON, TUE, WED, THU, FRI, SAT = 0b1000000, 0b100000, 0b10000, 0b1000, 0b100, 0b10, 0b1

class Task:
    LOWBYTE = (1 << 8) - 1
    HIGHBYTE = LOWBYTE << 8

    def __init__(self, name: bytes, maxRep, repNum, repDays, date):
        def unNull(s):
            i = 0
            while i < len(s):
                if s[i]:
                    i += 1
                    continue
                s = s[:i] + s[i+1:]
            return s
        self.__name = unNull(name)
        self.__maxRep = maxRep
        self.__repNum = repNum
        self.__repDays = repDays
        self.__date = date

    @property
    def name(self):
        return self.__name

    @property
    def maxRep(self):
        return self.__maxRep

    @property
    def repNum(self):
        return self.__repNum

    @property
    def repDays(self):
        return self.__repDays

    @property
    def date(self):
        return self.__date

    def toStoreFmt(self):
        """Converts the Task object to a bytes representation.
"""
        ret = self.__name + bytes([0])
        ret += bytes([(self.__maxRep & Task.HIGHBYTE) >> 8, self.__maxRep & Task.LOWBYTE])
        ret += bytes([(self.__repNum & Task.HIGHBYTE) >> 8, self.__repNum & Task.LOWBYTE])
        bits = self.__date.toStoreFmt()
        b = (bits >> (Datetime.NUM_BITS - 1)) & 1
        bits &= (1 << (Datetime.NUM_BITS - 1)) - 1
        ret += bytes([(self.__repDays << 1) + b])
        ret += bitsToBytes(bits, Datetime.NUM_BITS // 8)
        return ret

    @staticmethod
    def fromStoreFmt(s):
        """Converts the string representation to a Task object.
"""
        name = b""
        i = 0
        while s[i]:
            i += 1
        name = s[:i]
        maxRep = ((s[i + 1]) << 8) + s[i + 2]
        repNum = ((s[i + 3]) << 8) + s[i + 4]
        b = s[i + 5] & 1
        repDays = s[i + 5] >> 1
        date = Datetime.fromStoreFmt(bytesToBits(s[i + 6:i + 6 + Datetime.NUM_BITS // 8]))
        return (Task(name, maxRep, repNum, repDays, date), s[i + 6 + Datetime.NUM_BITS // 8:])

    def __str__(self):
        return f"{self.__name} ({self.__maxRep}) {self.__repNum} {self.__repDays:b} {self.__date}"

    def __repr__(self):
        days = ""
        if SUN & self.__repDays:
            days += "SUN"
        if MON & self.__repDays:
            days += "MON"
        if TUE & self.__repDays:
            days += "TUE"
        if WED & self.__repDays:
            days += "WED"
        if THU & self.__repDays:
            days += "THU"
        if FRI & self.__repDays:
            days += "FRI"
        if SAT & self.__repDays:
            days += "SAT"
        x = len(days) - 3
        while x > 0:
            days = days[:x] + " | " + days[x:]
            x -= 3
        del x
        return "Task(" + repr(self.__name) + f", {self.__maxRep}, {self.__repNum}, {days}, " + repr(self.__date) + ")"

class TaskList(list):
    def append(self, task):
        for i in range(len(self)):
            if self[i].date <= task.date:
                self.insert(i, task)
                return
        self.insert(len(self), task)
        return

class TaskListDict(dict):
    def __getitem__(self, key):
        if self.__contains__(key):
            return super().__getitem__(key)
        ret = TaskList()
        self[key] = ret
        return ret

lists = TaskListDict()

def makeList():
    with fd.asksaveasfile(mode='x+b', defaultextension=".lst") as l:
        lists[l.name] = TaskList()
    return

def readList(l):
    lists[l.name] = TaskList()
    taskBytes = l.read()
    while taskBytes:
        task, taskBytes = Task.fromStoreFmt(taskBytes)
        lists[l.name].append(task)
    return

def loadList():
    with fd.askopenfile(mode='rb', defaultextension=".lst") as l:
        readList(l)
    return

def loadLists():
    ls = fd.askopenfiles(mode='rb', defaultextension=".lst")
    for l in ls:
        readList(l)
        l.close()
    return

def readDirectory(dir):
    """Read each list with an absolute filename that begins with dir.
"""
    for f in os.listdir(dir):
        if os.path.isdir(f):
            readDirectory(f)
        elif os.path.isfile(f) and f.endswith(".lst"):
            with open(f, mode='rb') as l:
                readList(l)
    return

def loadDirectory():
    dir = fd.askdirectory()
    if dir:
        return readDirectory(dir)
    return None

def makeTask():
    listNameVar = tk.StringVar()
    repDaysVar = [tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar(),
                  tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar(),
                  tk.BooleanVar()]
    months = ("January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November",
              "December")
    dateMonthVar = tk.StringVar()
    dateBoxes = []
    ret = []

    def makeDaysButtonsFrame():
        repDaysFrame = tk.Frame(win)
        repDaysSun = tk.Checkbutton(repDaysFrame, text="Sunday", variable=repDaysVar[0])
        repDaysMon = tk.Checkbutton(repDaysFrame, text="Monday", variable=repDaysVar[1])
        repDaysTue = tk.Checkbutton(repDaysFrame, text="Tuesday", variable=repDaysVar[2])
        repDaysWed = tk.Checkbutton(repDaysFrame, text="Wednesday", variable=repDaysVar[3])
        repDaysThu = tk.Checkbutton(repDaysFrame, text="Thursday", variable=repDaysVar[4])
        repDaysFri = tk.Checkbutton(repDaysFrame, text="Friday", variable=repDaysVar[5])
        repDaysSat = tk.Checkbutton(repDaysFrame, text="Saturday", variable=repDaysVar[6])
        repDaysSun.grid(row=0, sticky=W)
        repDaysMon.grid(row=1, sticky=W)
        repDaysTue.grid(row=2, sticky=W)
        repDaysWed.grid(row=3, sticky=W)
        repDaysThu.grid(row=4, sticky=W)
        repDaysFri.grid(row=5, sticky=W)
        repDaysSat.grid(row=6, sticky=W)
        return repDaysFrame

    def makeDateFrame():
        frame = tk.Frame(win)
        dateYearBox = tk.Spinbox(frame, from_=0, to=Datetime.YR_BITS)
        dateMonthMenu = tk.OptionMenu(frame, dateMonthVar, "", *months)
        dateDayBox = tk.Spinbox(frame, from_=0, to=31)
        dateHourBox = tk.Spinbox(frame, from_=0, to=23)
        dateMinBox = tk.Spinbox(frame, from_=0, to=59)
        dateBoxes.append(dateYearBox)
        dateYearBox.pack(side=LEFT)
        dateMonthMenu.pack(side=LEFT)
        dateBoxes.append(dateDayBox)
        dateDayBox.pack(side=LEFT)
        dateBoxes.append(dateHourBox)
        dateHourBox.pack(side=LEFT)
        dateBoxes.append(dateMinBox)
        dateMinBox.pack(side=LEFT)
        return frame

    def buildTask(event=None):
        n = bytes(name.get(), "UTF-8")
        mr = int(maxRep.get())
        rn = int(repNum.get())
        rSun = repDaysVar[0].get()
        rMon = repDaysVar[1].get()
        rTue = repDaysVar[2].get()
        rWed = repDaysVar[3].get()
        rThu = repDaysVar[4].get()
        rFri = repDaysVar[5].get()
        rSat = repDaysVar[6].get()
        rd = ((SUN if rSun else 0) | (MON if rMon else 0) |
              (TUE if rTue else 0) | (WED if rWed else 0) |
              (THU if rThu else 0) | (FRI if rFri else 0) |
              (SAT if rSat else 0))
        yr = int(dateBoxes[0].get())
        mnt = months.index(dateMonthVar.get())
        day = int(dateBoxes[1].get()) - 1
        hr = int(dateBoxes[2].get())
        min = int(dateBoxes[3].get())
        d = Datetime(yr, mnt, day, hr, min)
        lists[listNameVar.get()].append(Task(n, mr, rn, rd, d))
        top.destroy()

    def cancel(event=None):
        top.destroy()
        return

    top = tk.Toplevel()
    top.title("New Task...")
    win = tk.Frame(top)
    lNameLabel = tk.Label(win, text="List Name: ")
    lName = tk.OptionMenu(win, listNameVar, "", *lists.keys())
    nameLabel = tk.Label(win, text="Name: ")
    name = tk.Entry(win)
    maxRepLabel = tk.Label(win, text="Maximum Repeat Number: ")
    maxRep = tk.Entry(win)
    repNumLabel = tk.Label(win, text="Current Repeat Number: ")
    repNum = tk.Entry(win)
    repDaysLabel = tk.Label(win, text="Repeat Days: ")
    repDays = makeDaysButtonsFrame()
    dateLabel = tk.Label(win, text="Date: ")
    date = makeDateFrame()
    lNameLabel.grid(column=0, row=0, sticky=W)
    lName.grid(column=1, row=0, sticky=W)
    nameLabel.grid(column=0, row=1, sticky=W)
    name.grid(column=1, row=1, sticky=W)
    maxRepLabel.grid(column=0, row=2, sticky=W)
    maxRep.grid(column=1, row=2, sticky=W)
    repNumLabel.grid(column=0, row=3, sticky=W)
    repNum.grid(column=1, row=3, sticky=W)
    repDaysLabel.grid(column=0, row=4, sticky=(N, W))
    repDays.grid(column=1, row=4, sticky=W)
    dateLabel.grid(column=0, row=5, sticky=W)
    date.grid(column=1, row=5, sticky=W)
    win.grid(column=0, row=0, sticky=(N, E, S, W))
    win = tk.Frame(top)
    cancelButton = tk.Button(win, text="Cancel", command=cancel)
    top.bind("<Escape>", cancel)
    okButton = tk.Button(win, text="OK", command=buildTask)
    top.bind("<Return>", buildTask)
    cancelButton.grid(column=0, row=0, sticky=E)
    okButton.grid(column=1, row=0, sticky=W)
    win.grid(column=0, row=1, sticky=(N, E, S, W))
    top.focus()
    return

def makeMenubar(window):
    def loadFile():
        return fd.LoadFileDialog(window)

    def saveAndQuit(event=None):
        for filename in lists.keys():
            with open(filename, "w+b") as l:
                for t in lists[filename]:
                    l.write(t.toStoreFmt())
                l.write(bytes([ord("\n")]))
        window.quit()

    ctrln, ctrlo, ctrlshifto, ctrlshiftd, ctrlq = ("Ctrl+N", "Ctrl+O",
            "Ctrl+Shift+O", "Ctrl+Shift+D", "Ctrl+Q")
    ctrlt = "Ctrl+T"

    funcs = {ctrln: lambda e: makeList(), ctrlo: lambda e: loadList(),
             ctrlshifto: lambda e: loadLists(),
             ctrlshiftd: lambda e: loadDirectory(),
             ctrlq: saveAndQuit,
             ctrlt: lambda e: makeTask()}

    menubar = tk.Menu(window)

    fileMenu = tk.Menu(menubar, tearoff = 0)
    fileMenu.add_command(label="New List", command=makeList, accelerator="Ctrl+N")
    window.bind("<Control-n>", funcs[ctrln])
    fileMenu.add_command(label="Load List", command=loadList, accelerator="Ctrl+O")
    window.bind("<Control-o>", funcs[ctrlo])
    fileMenu.add_command(label="Load Lists", command=loadLists, accelerator="Ctrl+Shift+O")
    window.bind("<Control-O>", funcs[ctrlshifto])
    fileMenu.add_command(label="Load Directory", command=loadDirectory, accelerator="Ctrl+Shift+D")
    window.bind("<Control-D>", funcs[ctrlshiftd])
    fileMenu.add_separator()
    fileMenu.add_command(label="Save and Quit", command=funcs[ctrlq], accelerator="Ctrl+Q")
    window.bind("<Control-q>", funcs[ctrlq])
    menubar.add_cascade(label="File", menu=fileMenu)

    editMenu = tk.Menu(menubar, tearoff = 0)
    editMenu.add_command(label="New Task", command=funcs[ctrlt], accelerator="Ctrl+T")
    window.bind("<Control-t>", funcs[ctrlt])
    menubar.add_cascade(label="Edit", menu=editMenu)

    return menubar

def main():
    mainWindow = tk.Tk()
    mainWindow.title("Todo List")
    frame = tk.Frame(mainWindow)
    frame.pack()
    menubar = makeMenubar(mainWindow)
    mainWindow.config(menu=menubar)
    print("Setup complete")
    mainWindow.mainloop()

if __name__ == "__main__":
    main()
else:
    dt = Datetime(2017, 11, 17, 20, 57)
    print(dt.toStoreFmt() - bytesToBits(bitsToBytes(dt.toStoreFmt(), Datetime.NUM_BITS // 8)))
    t = Task("Test a", 30, 3, SUN, dt)
    print(repr(t.toStoreFmt()))
