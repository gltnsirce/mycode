#!/bin/python
#   script that collects network dumps when a condition is met from the logs
#   functions that the script has to perform:
#   1 - take continuous network dumps from a vmnic to a file
#   2 - rotate that file and remove it after a while
#   3 - continuosuly monitor and parse a log file and search for a string
#   4 - if the string is found, then stop the captures and send a message
############################################################################



# MODULES NEEDED

import subprocess
import sys
import re
import time
import os


# maxsize of dump files 128MB
maxsize = 134217728

# Log file to Monitor and Scan
log = '/var/log/clomd.log'


# regex generated using http://txt2re.com/index-python.php3?s=Removing%2059523f9b-04ab-6a30-a574-54ab3a773d8e%20of%20type%20CdbObjectNode%20from%20CLOMDB&6&49&1&50&35&51&12&52&2&53&11&54&8

re1='Removing'                                                          # Word Removing
re2='(\\s+)'                                                            # White Space 1
re3='([A-Z0-9]{8}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{12})'    # SQL GUID 1
re4='(\\s+)'                                                            # White Space 2
re5='((?:[a-z][a-z]+))'                                                 # Word 2
re6='(\\s+)'                                                            # White Space 3
re7='((?:[a-z][a-z]+))'                                                 # Word 3
re8='(\\s+)'                                                            # White Space 4
re9='((?:[a-z][a-z]+))'                                                 # Word 4
re10='(\\s+)'                                                           # White Space 5
re11='((?:[a-z][a-z]+))'                                                # Word 5
re12='(\\s+)'                                                           # White Space 6
re13='CLOMDB'                                                           # Word CLOMDB

# Regex Compilation that matches exactly a string like: "Removing 59523f9b-04ab-6a30-a574-54ab3a773d8e of type CdbObjectNode from CLOMDB"
# #2018-01-16T11:56:57.933Z 33787 Removing 59523f9b-04ab-6a30-a574-54ab3a773d8e of type CdbObjectNode from CLOMDB

rg = re.compile(re1+re2+re3+re4+re5+re6+re7+re8+re9+re10+re11+re12+re13,re.IGNORECASE|re.DOTALL)

# Automatically retrieves service Datastore Path

serviceDatastore="esxcli storage vmfs extent list | grep service | awk '{printf $1}'"
path =  subprocess.check_output(serviceDatastore,shell=True)


# runDump()
# Function that starts the network dump on dir0 (Rx) and dir1 (Tx)



capturedir0 = "pktcap-uw --uplink vmnic1 --dir 0 -o "+"/vmfs/volumes/"+path+"/dumps/esxdir0.pcap &"
capturedir1 = "pktcap-uw --uplink vmnic1 --dir 1 -o "+"/vmfs/volumes/"+path+"/dumps/esxdir1.pcap &"


def runDump():

    try:
        dir0 = subprocess.call(capturedir0, shell=True)
        dir1 = subprocess.call(capturedir1, shell=True)

    except OSError as e:
            print >> sys.stderr, "Run Dump Execution failed:", e



# killDump()
# Function that kills the running packet capture

def killDump():

    try:
        cmd = "kill $(lsof |grep pktcap-uw | awk '{print $1}'| sort -u)"
        killPid = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        killOut = killPid.communicate()[0]
    except OSError as e:
         print >> sys.stderr, "Kill Dump Execution failed:", e


# newCheckSize()
# Function that returns the sum size of the dump files in the dump directory

def newCheckSize():

    dumpdir = '/dumps'
    basepath = '/vmfs/volumes/'
    pathnew = basepath + path + dumpdir
    total = 0

    try:

        sizearray = []

        for pcap in os.listdir(pathnew):
            z = os.path.getsize(pathnew + '/' + pcap)
            sizearray.append(int(z))

        total = sum(sizearray)

    except OSError as e:
        print >> sys.stderr, "Check Size Execution failed:", e

    return total


# scanLog()
# Function that scans a log file and return 0 if a match is found

def scanLog():

    try:
        textfile = open(log, 'r')
        filetext = textfile.read()
        textfile.close()
        if re.findall(rg, filetext):
            return 0
        else:
            return 1

    except OSError as e:
         print >> sys.stderr, "Check Size Execution failed:", e

# logESX()
# Function that marks the ESXi logs with a message

def logESX():
    try:
        retcode = subprocess.call("esxcli system syslog mark" + " -s 'START_HERE'", shell=True)
        if retcode < 0:
            print >> sys.stderr, "Child was terminated by signal", -retcode
        else:
            print >> sys.stderr, "Child returned", retcode
    except OSError as e:
        print >> sys.stderr, "logESX Execution failed:", e

# cleanLog()
# Function that removes the Network Dump

def cleanLog():

    try:
        retcode = subprocess.call("rm" + " /vmfs/volumes/"+path+"/dumps/esxdir[0-1].pcap", shell=True)
        if retcode < 0:
            print >> sys.stderr, "Child was terminated by signal", -retcode
        else:
            print >> sys.stderr, "Child returned", retcode
    except OSError as e:
        print >> sys.stderr, "cleanLog Execution failed:", e

# vmSupport()
# Generates a vm-support log bundle

def vmSupport():

    try:
        bundle =  subprocess.call("vm-support", shell=True)
    except OSError as e:
        print >> sys.stderr, "vm-support Execution failed:", e

# createDumpDir()
# Function that creates the dump directory where dumps are saved

def createDumpDir():

    try:
        if not os.path.exists("/vmfs/volumes/"+path+"/dumps"):
            dumpdir = os.mkdir("/vmfs/volumes/"+path+"/dumps")
    except OSError as e:
            print >> sys.stderr, "createDumpDir Execution failed:", e

# main()
# This is the main program logic based on all the helper functions that will deal with the network capture


def main():

# initalize dumpdir
    createDumpDir()
# we start first the dump
    runDump()

    while True:
        curSize = newCheckSize()
        if curSize > maxsize and scanLog() == 1: # test that the size is small and that we dont have a match so we can kill the dump/clean the log and start a new dump
            killDump()      # Kills the Dump
            time.sleep(3)   # To fix a race condition where rundump was called while previous process not killed
            cleanLog()      # Deletes the Captures
            time.sleep(1)   # Wait 1 sec after deleting teh logs and starting a new dump
            runDump()       # rerun the Dump
        elif curSize > maxsize and scanLog() == 0:
            logESX()        # Mark ESXi Logs when a string is found and stops the Dump.
            print "MATCH FOUND: Going to Sleep 30s ..."
            time.sleep(30)  # sleeps for 30 seconds before killing the dump
            killDump()      # Kills the Dump after 30 seconds
            vmSupport()     # Generates a vm-support log bundle from ESXi
            exit()          # Exit the Python Scrip


    return 0




# Start program
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stderr.write('\nDetect: Interrupted\n')
        sys.exit(1)
    except Exception as err:
        print >> sys.stderr, "Main Execution Failed:", err
        sys.exit(1)
