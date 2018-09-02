#!/usr/bin/env python3

#########################
#
# alarm.py is a python3 script to set an alarm to play songs using mpd and mpc
# at scheduled times like an alarm clock. By using crontab, alarms are naturally
# repeating.
#
# alarm.py must not alter any crontab jobs not created by this script
#
# One goal of writing this script was to understand what alarm commands are
# required for an alarm clock.
#
# I use three question (???) marks to indicate features that are not quite
# finished
#
# alarm.py was tested on a Raspberry Pi 3 model B+ running raspbian stretch
#
# To Do List
#   ??? alarm crontab command must be more than: mpc play
#   ???    set and init mpc to FM radio, songs or station prior to mpc play
#   ??? atore music source in crontab: FM radio, songs or station?
#       for now I will just use song as source
#       rather than load all_songs load just the first one
#
#   ??? post alarm.py on github
#   ??? make writeup on my rpi home automation google sites
#
# An alarm clock user needs to hear and adjust the radio volume when setting an alarm,
# and this volume should be used when the alarm goes off
#
# alarm.py stores a list of unique alarm names in the comments of a crontab job
# and crontab stores volume when alarm is created, and later sets volume when alarm
# goes off. crontab also Need to stores source of music: FM radio, songs or internet radio
#
# crontab's time and date fields are:
#   minute hour dom month dow
#      minute: 0-59
#      hour:   0-23
#      dom: day of month: 1-31
#      month: 1-12 (or names, see below)
#      dow: day of week: 0-7 (0 or 7 is Sun, or use three letter names)
#
#   Use the first three letters of the particular day or month (case doesn't matter)
#   A field may be an asterisk (*), which I understand to be ignore
#
#   Add slash /n to repeat every n months/days/hours/minutes
#   Use comma to specify multiples 0 5 * * 1,2,3,4,5 to run alarm every business day
#
#########################

import time
import datetime
import os
import sys
import subprocess
from crontab import CronTab

currentSongConfig = '/home/pi/radio/songPlayer.conf'
tempSongFile = '/home/pi/radio/songPlayer.tmp'

directoryMusic = "/home/pi/Music"

fileLog = open('/home/pi/radio/alarm.log', 'w+')
my_cron = CronTab(user='pi')
alarms = []

defaultVolume = 60
currentVolume = defaultVolume

muteVolume = False

defaultPlaylist = "all_songs"
currentPlaylist = defaultPlaylist

currentSong = ""

limitMPCoutput = " | grep \"[-,'[']\""

#########################
# Log messages should be time stamped
def timeStamp():
    t = time.time()
    s = datetime.datetime.fromtimestamp(t).strftime('%Y/%m/%d %H:%M:%S - ')
    return s

# Write messages in a standard format
def printMsg(s):
    fileLog.write(timeStamp() + s + "\n")

def lastSong():
    f = tempSongFile
    cmd = "mpc current > " + f
    subprocess.call(cmd, shell=True)
    try:
        fileSong = open(f, 'r')
        songAndTitle = fileSong.readline()
        i = songAndTitle.find("-") + 2
        songAndNewline = songAndTitle[i:]
        song = songAndNewline.rstrip()
        fileSong.close()
    except Exception as ex:
        printMsg("Exception in lastSong = [" + ex + "]")
        song = ""

    return song

def readSongPlayerConfig():
    global currentSong
    global currentVolume
    global currentPlaylist

    song = lastSong()

    try:
        f = open(currentSongConfig, 'r')
        songAndTitle = f.readline()
        if song == "":
            st = songAndTitle.rstrip()
            i = st.find("-") + 2
            song = st[i:]

        currentSong = song
        l = f.readline()
        v = l.rstrip()
        currentVolume = int(v)
        l = f.readline()
        currentPlaylist = l.rstrip()
        f.close()
    except Exception as ex:
        printMsg("Exception in readSongPlayerConfig [" + ex + "]")
        currentSong = ""
        currentVolume = defaultVolume
        currentPlaylist = defaultPlaylist
        f.close()
    except Exception as ex:
        printMsg("Exception in readSongPlayerConfig [" + ex + "]")
        currentSong = "" 
        currentVolume = defaultVolume
        currentPlaylist = defaultPlaylist
        f.close()

    printMsg("read songPlayer config")
    printMsg(" song = [" + currentSong + "]")
    printMsg(" volume = [" + str(currentVolume) + "]")
    printMsg(" playlist = [" + currentPlaylist + "]")

    cmd = "rm " + tempSongFile
    subprocess.call(cmd, shell=True)
    return

def writeSongPlayerTxt():
    global currentSong

    # current song can be null
    o = subprocess.check_output("mpc current", shell=True)
    songAndTitle = o.decode("utf-8")
    if songAndTitle != "":
        songAndTitle = songAndTitle.rstrip()

    i = songAndTitle.find("-") + 2
    currentSong = songAndTitle[i:]

    f = open(currentSongConfig, 'w')
    f.write(currentSong + "\n")
    f.write(str(currentVolume) + "\n")
    f.write(currentPlaylist + "\n")
    f.close()

def initPlaylist(playlist_name):
    global currentPlaylist

    cmd = "mpc clear" + limitMPCoutput
    subprocess.call(cmd, shell=True)

    print("Loading songs takes a few minutes. Please wait for > prompt")
    for file in os.listdir(directoryMusic):
        if file.endswith(".m4a"):
            dirName = os.path.join(directoryMusic, file)
            fileName = "file://" + dirName
            cmd = 'mpc insert ' + '"' + fileName + '"'
            subprocess.call(cmd, shell=True)

    cmd = "mpc save " + playlist_name
    subprocess.call(cmd, shell=True)

    currentPlaylist = playlist_name
    return

def readAlarms():
    global alarms

    # clear out the data structure
    alarms = []

    # read alarms from crontab and build data structure
    i = 0
    for job in my_cron:
        c = str(job.comment)
        if c.startswith('alarm'):
            j = str(job)
            alarms.append(j)
            i += 1
    return

def listAlarms():
    global alarms

    for i in range(len(alarms)):
        print("alarms[" + str(i) + "] = " + alarms[i])

    return

def removeAllAlarms():
    global alarms

    # next remove all alarms
    for a in alarms:
        s = a.find('# alarm')
        if s > 0:
            s += 2 # skip the # and space
            c = a[s:]
            my_cron.remove_all(comment=c)
            my_cron.write()
    return

def removeAlarm(n):
    global alarms

    # if an alarm is removed from the middle of crontab, then the alarm numbering is messed up
    # all alarms must be removed and re-read

    # first remove requested alarm
    c = 'alarm' + str(n)
    my_cron.remove_all(comment=c)
    my_cron.write()

    readAlarms()

    # next remove all alarms from crontab keeping the data structure
    removeAllAlarms()

    # then put all alarms back into crontab with new numbers
    i = 0
    for a in alarms:
        s = a.find('# alarm')
        if s > 0:
            j = a[:s]
            c = 'alarm' + str(i)
            job = my_cron.new(command='/usr/bin/mpc play', comment=c)
            i += 1
            # get crontab times
            t = a.find('/')
            t1 = a[:t]
            l1 = t1.split(" ")
            t2 = []
            j = 0
            for l in l1:
                if l != '':
                    if l.find("-") > 0:
                        t2.append(l)
                    else:
                        t2.append(l)
                    j += 1
            job.setall(t2[0], t2[1], t2[2], t2[3], t2[4])
            my_cron.write()

    readAlarms()

    return

def setAlarm(h, m, dow):
    global alarms
    global currentVolume

    c = 'alarm' + str(len(alarms))
    cmd = '/usr/bin/mpc play; '
    # need to escape % because it is a special character in crontab
    cmd += "/usr/bin/amixer set Digital " + str(currentVolume) + "\%"
    job = my_cron.new(command=cmd, comment=c)
    if int(m) == 0:
        m = '*'
    job.setall(m, h, '*', '*', dow)
    my_cron.write()

    alarms = []
    readAlarms()
    return


def init():
    global alarms

    readAlarms()

    # putting initPlaylist here is a hack to hard code source as songs
    # it takes a while to load, so uncomment if needed
    # initPlaylist(defaultPlaylist)

    readSongPlayerConfig()

    print("volume = [" + str(currentVolume) + "]")
    cmd = "amixer set Digital " + str(currentVolume) + "%"
    subprocess.call(cmd, shell=True)

    if currentSong == "":
        cmd = "mpc play " + limitMPCoutput
    else:
        cmd = 'mpc searchplay title "' + currentSong + '"' + limitMPCoutput

    subprocess.call(cmd, shell=True)

    return

def printMenu():
    print (" ")
    print ("Alarm Commands:")
    print ("   >        play music")
    print ("   +/-      set volume for alarm")
    print ("   l        list alarms by name")
    print ("   r=n      remove alarm named n")
    print ("   R        Remove all alarms")
    print ("   s=h:m:x  set alarm at hour:minute")
    print ("            if x = 0..7 then that day of week")
    print ("            if x = 1-5 then those days of the week")
    print ("   S=n      ??? Set source, where n is one of r=internet radio, s=song, f=fm radio") 
    print ("   o        Shut raspberry pi off")
    print ("   x        Exit")
    print ("   Return   Press Enter or Return key to exit")

#########################
printMsg("Starting alarm")

try:

    ans = True
    init()

    while ans:
        printMenu()

        # command order was by type, but changed to alphabetic because it
        # is easier to find the command
        ans = input(">")
        if ans != "" and ans[0] == ">":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # play song number n
                s = ans[2:]
                print ("play song number " + s)
                cmd = "mpc play " + s  + limitMPCoutput
                subprocess.call(cmd, shell=True)
            else:
                # play
                print("play")
                cmd = "mpc play" + limitMPCoutput
                subprocess.call(cmd, shell=True)
        elif ans == "+":
            # volume up
            print ("volume up")
            currentVolume += 5
            if currentVolume > 100:
                currentVolume = 100
            cmd = "amixer set Digital " + str(currentVolume) + "%"
            subprocess.call(cmd, shell=True)
        elif ans == "-":
            # volume down
            print ("volume down")
            currentVolume -= 5
            if currentVolume < 0:
                currentVolume = 0
            cmd = "amixer set Digital " + str(currentVolume) + "%"
            subprocess.call(cmd, shell=True)
        elif ans == "l":
            listAlarms()
        elif ans == "o":
            # shutoff raspberry pi and radio
            sys.exit()
        elif ans != "" and ans[0] == "r":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # remove alarm n
                n = int(ans[2:])
                print ("Remove alarm " + str(n))
                if (n >= 0) and (n < len(alarms)):
                    removeAlarm(n)
        elif ans == "R":
            # Remove all alarms
            print("Remove all alarms")
            removeAllAlarms()
            alarms = []
        elif ans != "" and ans[0] == "s":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # Set alarm
                print ("Set alarm")
                t = ans[2:]
                l = t.split(':')
                if len(l) < 3:
                    print ("h:m:dow is required")
                else:
                    print ("Set alarm")
                    setAlarm(l[0], l[1], l[2])
            else:
                print("h:m:dow is required")
        elif ans == "x":
            # exit and leave music playing
            sys.exit()
        elif ans == "":
            # exit and stop music
            sys.exit()
        else:
            print("Unrecognized command: " + ans)

    sys.exit()

except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt
    printMsg("keyboard exception occurred")

except Exception as ex:
    printMsg("ERROR: an unhandled exception occurred: " + str(ex))

finally:
    printMsg("alarm terminated")
    if ans == "x":
        fileLog.close()
    elif ans == "o":
        subprocess.call("mpc stop ", shell=True)
        printMsg("... Shutting down raspberry pi")
        fileLog.close()
        subprocess.call("sudo shutdown -h 0", shell=True)
    else:
        subprocess.call("mpc stop ", shell=True)
        fileLog.close()

