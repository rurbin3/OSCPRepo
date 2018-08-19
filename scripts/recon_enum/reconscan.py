#!/usr/bin/env python

###############################################################################################################
## [Title]: reconscan.py -- a recon/enumeration script
## [Author]: Mike Czumak (T_v3rn1x) -- @SecuritySift
## [Updates]: Reward1
##-------------------------------------------------------------------------------------------------------------
## [Details]:
## This script is intended to be executed remotely against a list of IPs to enumerate discovered services such
## as smb, smtp, snmp, ftp and other.
##
## This script really likes when you put a targets.txt file containing targets (one per line) at
## /root/scripts/recon_enum/results/exam/targets.txt
##
## The script will run nmap (very fast min rate) against all ports, pass open ports to Nmap, and then run an nmap scan
## against all ports.
##-------------------------------------------------------------------------------------------------------------
## [Run]:
## Execute setup.sh in the scripts folder
## /root/scripts/recon_enum/./reconscan.py
## or
## python /root/scripts/recon_enum/reconscan.py
##-------------------------------------------------------------------------------------------------------------
## [Warning]:
## This script comes as-is with no promise of functionality or accuracy.  I strictly wrote it for personal use
## I have no plans to maintain updates, I did not write it to be efficient and in some cases you may find the
## functions may not produce the desired results so use at your own risk/discretion. I wrote this script to
## target machines in a lab environment so please only use it against systems for which you have permission!!
##-------------------------------------------------------------------------------------------------------------
## [Modification, Distribution, and Attribution]:
## You are free to modify and/or distribute this script as you wish.  I only ask that you maintain original
## author attribution and not attempt to sell it or incorporate it into any commercial offering (as if it's
## worth anything anyway :)
##-------------------------------------------------------------------------------------------------------------
## [TODO]
## Expand: "Alive" script. Identify alive hosts using 'advanced' techniques.
##      Pre-Exploitation Enumeration > Active > Internal Infrastructure Mapping > Identify Alive IPs
## Expand: RDPenum with rdp-sec-check
## Running each script individually does not ensure their output directory paths exist...QoL feature...
## Fix DNSRecon
## Expand: DirbustEverything
##       : more tools! DirBuster, Dirsearch
##       : Photon, nice crawler. Can ensure things are not missed (currently using Cewl to crawl and wordlist)
## Expand: option to follow redirects in gobuster or default to follow? redirect comes at the cost of time (long time)
##       : But benefit of having less 301 / false negatives
##       : Initial testing: times are same. -r scan has more false negatives. Looks like best option will be
##       : no redirect scan, grab (Status: 301) pages and gobust just on those
## Expand FTP/TFTP: Utilize anonymous and credentialed DotDotPwn scan
## Expand SMTPrecon:
##       : currently only scans 25. need: 25,110,143,465,587,993,995 (IMAP/POP/Exchange)
##       : Change to ip_address, port. Pass specific ports only, currently hardcoded 25,465,587
##       : Ruler for exchange (possibly)
## Expand SMBRecon:
##       : hydra or crackmapexec for spray/brute
##       : add nullinux for fun
## Expand dirTrav:
##     Need to debug all cases (page?= vulns and windows)
## Option to run reconscan with an IP range to pass to aliverecon
## Expand ReconScan:
##      POST SCAN COMPLETION:
##           Parse outputs and run through searchsploit and getsploit
##           If windows: give additional commands to run
##                (if Windows AND SMB: github/enternal_check) #not mandatory because of additional dependencies
##                                                            #unless they are already in Kali...
## Expand ReconScan:
##      Other tools to consider: WHOIS, TheHarvester, Metagoofil, DNSRecon, Sublist3r
##      Other tools to consider: WafW00f, WAFNinja, XSS Scanner, Arachni, Spaghetti
##      Other tools to consider: WPscan, WPscanner, WPSeku, Droopescan, SSLScan, SSLyze A2SV
##      Separate CMSscannerrecon
##      Apple File System. NSE scripts: brute, ls, path-vuln, servierinfo, showmount
##      Create "AutoADPwn": Invoke several modules, AD recon, bloodhound, Empire/Deathstar
##      PHPFilter scan (LFI/source/etc)
## Need scripts for:
##       LDAP, rsh, vnc
## web page screenshots
##
## [THOUGHTS]
## Organizing everything by IP address would probably be a lot better, but it seems like a lot of work to go through everything to make that change...
## Split http nmap scripts
##
## [NOTES]
## vulners.nse requires -sV flag
###############################################################################################################

import subprocess
import multiprocessing
from multiprocessing import Process, Queue
import os
import time
import errno
import shutil

#PRIVATE VARS
userAgent = "'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'" #This will replace the default nmap http agent string
FAST_NMAP_MIN_RATE = "10000"
SLOW_NMAP_MIN_RATE = "1000"

def multProc(targetin, scanip, port):
    jobs = []
    p = multiprocessing.Process(target=targetin, args=(scanip,port))
    jobs.append(p)
    p.start()
    return

def dnsEnum(ip_address, port):
    print "INFO: Detected DNS on %s:%s" % (ip_address, port)
    if port.strip() == "53":
       SCRIPT = "./dnsrecon.py %s" % (ip_address)# execute the python script
       subprocess.check_output(['./dnsrecon.py',ip_address])
       #subprocess.call(SCRIPT, shell=True)
    return

def ftpEnum(ip_address, port):
    #EDIT WITH USERNAME/PASSWORD LISTS
    print "INFO: Detected ftp on %s:%s" % (ip_address, port)
    #FTPRECON in subdirectory in case ssh/telnet/mysql are present, hydra will have
    #separate hydra.restore files
    SCRIPT = "ftp/./ftprecon.py %s %s" % (ip_address, port)
    subprocess.check_output(['ftp/./ftprecon.py',ip_address,port])
    #subprocess.call(SCRIPT, shell=True)
    return

def fingerEnum(ip_address, port):
   print "INFO: Detected Finger on %s:%s" % (ip_address, port)
   FINGERSCAN = "nmap -n -sV -Pn -vv -p %s --script finger,vulners -oA /root/scripts/recon_enum/results/exam/finger/%s_finger.xml %s" % (port, ip_address, ip_address)
   subprocess.check_output(['nmap','-n','-sV','-Pn','-vv','-p',port,'--script','finger,vulners','-oA','/root/scripts/recon_enum/results/exam/finger/%s_%s_finger' % (ip_address,port),ip_address])
   #subprocess.call(FINGERSCAN, shell=True)
   return

def httpEnum(ip_address, port):
    path = "/root/scripts/recon_enum/results/exam/dirb/%s" % (port)
    mkdir_p(path)
    print "INFO: Detected http on %s:%s" % (ip_address, port)
    print "INFO: Performing nmap web script scan for %s:%s" % (ip_address, port)
    subprocess.check_output(['./webRecon.py','http://%s:%s' % (ip_address, port)])
    print "INFO: webRecon scan completed for %s:%s" % (ip_address, port)
    print "INFO: dirbust scan started on %s:%s" % (ip_address, port)
    subprocess.check_output(['./dirbustEVERYTHING.py','-p',1,'-i',4,'http://%s:%s' % (ip_address,port),ip_address])
    print "INFO: dirbust scan completed for %s:%s" % (ip_address, port)
    return

def httpsEnum(ip_address, port):
    path = "/root/scripts/recon_enum/results/exam/dirb/%s" % (port)
    mkdir_p(path)
    print "INFO: Detected https on %s:%s" % (ip_address, port)
    print "INFO: Performing nmap web script scan for %s:%s" % (ip_address, port)
    subprocess.check_output(['./webRecon.py','https://%s:%s' % (ip_address, port)])
    print "INFO: webRecon scan completed for %s:%s" % (ip_address, port)
    print "INFO: dirbust scan started on %s:%s" % (ip_address, port)
    subprocess.check_output(['./dirbustEVERYTHING.py','-p',1,'-i',4,'https://%s:%s' % (ip_address,port),ip_address])
    print "INFO: dirbust scan completed for %s:%s" % (ip_address, port)
    return

def mssqlEnum(ip_address, port):
    #EDIT WITH USERNAME/PASSWORD LISTS
	#MYSQLRECON in subdirectory in case multiple Hydra.restore files. default, nmap performs brute.
    print "INFO: Detected MS-SQL on %s:%s" % (ip_address, port)
    subprocess.check_output(['mssql/./mssqlrecon.py',ip_address,port])
    return

def mysqlEnum(ip_address, port):
    #EDIT WITH USERNAME/PASSWORD LISTS
	#MYSQLRECON in subdirectory in case ftp/ssh/telnet are present, hydra will have
    print "INFO: Detected MySQL on %s:%s" % (ip_address, port)
    subprocess.check_output(['mysql/./mysqlrecon.py',ip_address,port])
    return

def nfsEnum(ip_address, port):
    print "INFO: Detected NFS on %s:%s" % (ip_address, port)
    subprocess.check_output(['./nfsRecon.py',ip_address,port])
    return

def msrpc(ip_address, port):
    print "INFO: Detected MSRPC on %s:%s" % (ip_address, port)
    #Impacket RPC packages
    subprocess.check_output(['./msrpcrecon.py',ip_address,port])
    return

#port 111 #apt-get install, nfs-common
#Running
#rpc-grind: Fingerprints target RPC port to extract service, rpc number, and version
#rpcinfo: Connects to portmapper and fetches a list of all registered programs

#Not Running
#rpcap-brute: Brute against WinPcap Remote Capture
#rpcap-info: Retrieve interface information through rpcap service
def rpcbindEnum(ip_address, port):
    print "INFO: Detected RPCBind on %s:%s" % (ip_address, port)
    subprocess.check_output(['nmap','-n','-sV','-Pn','-vv','-p',port,'--script','rpc-grind,rpcinfo','-oA',"/root/scripts/recon_enum/results/exam/rpc/%s_%s_rpc" % (ip_address,port),ip_address])
    RPCINFOSCAN1 = "rpcinfo %s > /root/scripts/recon_enum/results/exam/rpc/%s_rpcinfo.txt && echo -e '\n' >> /root/scripts/recon_enum/results/exam/rpc/%s_rpcinfo.txt" % (ip_address, ip_address, ip_address)
    subprocess.check_output(RPCINFOSCAN1, shell=True)
    RPCINFOSCAN2 = "rpcinfo -p %s > /root/scripts/recon_enum/results/exam/rpc/%s_rpcinfo.txt && echo -e '\n' >> /root/scripts/recon_enum/results/exam/rpc/%s_rpcinfo.txt" % (ip_address, ip_address, ip_address)
    subprocess.check_output(RPCINFOSCAN2, shell=True)
    RPCINFOSCAN3 = "rpcinfo -m %s > /root/scripts/recon_enum/results/exam/rpc/%s_rpcinfo.txt && echo -e '\n' >> /root/scripts/recon_enum/results/exam/rpc/%s_rpcinfo.txt" % (ip_address, ip_address, ip_address)
    subprocess.check_output(RPCINFOSCAN3, shell=True)
    return

def rdpEnum(ip_address, port):
    #EDIT WITH USERNAME/PASSWORD LISTS
	#RDPRECON in subdir in case multiple hydra.restore files
    print "INFO: Detected RDP on %s:%s" % (ip_address, port)
    subprocess.check_output(['rdp/./rdprecon.py',ip_address,port])
    return

def rloginEnum(ip_address, port):
    #Typically only 513, so we'll check
    if port.strip() == "513":
        print "INFO: RLogin detected on %s:%s" % (ip_address, port)
        try:
            results = subprocess.check_output(['hydra','-L','/root/lists/userlist.txt','-P','/root/lists/quick_password_spray.txt','-f','-o','/root/scripts/recon_enum/results/exam/%s_rloginhydra' % (ip_address),'-u',ip_address,'rlogin']).split("\n")
            for res in results:
                if "login:" in res:
                    print "[*] Valid rlogin credentials found: " + res
        except subprocess.CalledProcessError as hydrerr:
            if hydrerr.returncode == 255:
                print "Hydra broke early with status 255, it must have found something! Check rloginhydra for output."
                print "Note you may need to download rsh-client."
            elif hydrerr.returncode != 0:
                print "Hydra broke:"
                print hydrerr.returncode
                print hydrerr.output
            else:
                print "INFO: No valid rlogin credentials found"
    else:
        print "Other rlogin services (exec/shell) detected. Recon manually: %s:%s" % (ip_address, port)
    return

def sshEnum(ip_address, port):
    #EDIT WITH USERNAME/PASSWORD LISTS
    print "INFO: Detected SSH on %s:%s" % (ip_address, port)
    #SCRIPT = "./sshrecon.py %s %s" % (ip_address, port)
    subprocess.check_output(['./sshrecon.py',ip_address,port])
    #subprocess.call(SCRIPT, shell=True)
    return

def snmpEnum(ip_address, port):
    print "INFO: Detected snmp on %s:%s" % (ip_address, port)
    subprocess.check_output(['./snmprecon.py',ip_address])
    #SCRIPT = "./snmprecon.py %s" % (ip_address)
    #subprocess.call(SCRIPT, shell=True)
    return

def smtpEnum(ip_address, port):
    print "INFO: Detected smtp on %s:%s" % (ip_address, port)
    if port.strip() == "25":
       #SCRIPT = "./smtprecon.py %s" % (ip_address)
       subprocess.check_output(['./smtprecon.py',ip_address])
       #subprocess.call(SCRIPT, shell=True)
    else:
       print "WARNING: SMTP detected on non-standard port, smtprecon skipped (must run manually)"
    return

def smbEnum(ip_address, port):
    print "INFO: Detected SMB on %s:%s" % (ip_address, port)
    if port.strip() == "139":
       #SCRIPT = "./smbrecon.py %s %s" % (ip_address, port)
       subprocess.check_output(['./smbrecon.py',ip_address,port])
       #subprocess.call(SCRIPT, shell=True)
    if port.strip() == "445":
       #SCRIPT = "./smbrecon.py %s %s" % (ip_address, port)
       #subprocess.call(SCRIPT, shell=True)
       subprocess.check_output(['./smbrecon.py',ip_address,port])
    if port.strip() == "137":
       #SCRIPT = "./smbrecon.py %s %s" % (ip_address, port)
       #subprocess.call(SCRIPT, shell=True)
       subprocess.check_output(['./smbrecon.py',ip_address,port])
    return

def telnetEnum(ip_address, port):
    #EDIT WITH USERNAME/PASSWORD LISTS
    #TELNETRECON in subdirectory in case ftp/ssh/mysql are present, hydra will have
    #separate hydra.restore files
    print "INFO: Detected Telnet on %s:%s" % (ip_address, port)
    #SCRIPT = "telnet/./telnetrecon.py %s %s" % (ip_address, port)
    subprocess.check_output(['telnet/./telnetrecon.py',ip_address,port])
    #subprocess.call(SCRIPT, shell=True)
    return

def tftpEnum(ip_address, port):
   print "INFO: Detected TFTP on %s:%s" % (ip_address, port)
   #TFTPSCAN = "nmap -n -sV -Pn -vv -p %s --script=tftp-enum,vulners -oA /root/scripts/recon_enum/results/exam/tftp/%s_tftp.xml %s" % (port, ip_address, ip_address)
   subprocess.check_output(['nmap','-n','-sV','-Pn','-vv','-p',port,'--script','tftp-enum,vulners','-oA',"/root/scripts/recon_enum/results/exam/tftp/%s_%s_tftp" % (ip_address,port),ip_address])
   #subprocess.call(TFTPSCAN, shell=True)
   return

def nmapFullSlowScan(ip_address):
   ip_address = ip_address.strip()
   print "INFO: Running full TCP/UDP nmap scans for %s" % (ip_address)
   print "INFO: Full UDP takes a LONG time"
   #TCPSCAN = "nmap -n -vv --stats-every 30s -Pn -sT -T 3 -p- --max-retries 1 --min-rate 1000 -oA '/root/scripts/recon_enum/results/exam/nmap/%s_FULL.nmap' -oX '/root/scripts/recon_enum/results/exam/nmap/%s_FULL_nmap_scan_import.xml' %s"  % (ip_address, ip_address, ip_address)
   #UDPSCAN = "nmap -n -vv --stats-every 30s -Pn -sU -T 3 -p- --max-retries 1 --min-rate 1000 -oA '/root/scripts/recon_enum/results/exam/nmap/%sU_FULL' %s" % (ip_address, ip_address)
   #tcplines = subprocess.check_output(TCPSCAN, shell=True).split("\n")
   tcplines = subprocess.check_output(['nmap','-n','-vv','--stats-every','30s','-Pn','-sT','-T','3','-p-','--max-retries','1','--min-rate',SLOW_NMAP_MIN_RATE,'-oA',"/root/scripts/recon_enum/results/exam/nmap/%s_FULL" % ip_address,ip_address]).split("\n")
   for line in tcplines:
      line = line.strip()
      if ("tcp" in line) and ("open" in line) and not ("Discovered" in line):
         while "  " in line:
            line = line.replace("  ", " ");
         linesplit= line.split(" ")
         service = linesplit[2] # grab the service name
         port = line.split(" ")[0] # grab the port/proto
         port = port.split("/")[0]
         print ("INFO: Full Nmap for %s found TCP: %s on %s") % (ip_address, service, port)
   udplines = subprocess.check_output(['nmap','-n','-vv','--stats-every','30s','-Pn','-sU','-T','3','-p-','--max-retries','1','--min-rate',SLOW_NMAP_MIN_RATE,'-oA',"/root/scripts/recon_enum/results/exam/nmap/%sU_FULL" % ip_address,ip_address]).split("\n")
   #udplines = subprocess.check_output(UDPSCAN, shell=True).split("\n")
   for line in udplines:
      line = line.strip()
      if ("udp" in line) and ("open" in line) and not ("Discovered" in line):
         while "  " in line:
            line = line.replace("  ", " ");
         linesplit= line.split(" ")
         service = linesplit[2] # grab the service name
         port = line.split(" ")[0] # grab the port/proto
         port = port.split("/")[0]
         print ("INFO: Full Nmap for %s found UDP: %s on %s") % (ip_address, service, port)
   print "INFO: TCP/UDP Nmap scans completed for %s" % (ip_address)
   return

#Be sure to change the interface if needed
#-mT/-mU TCP/UDP respectively, full range of ports. -L timeout 3 seconds (7 default), 300 packets per second (default)
# -n                    Do not do name service lookup
# -vv                   be very verbose
# --stats-every 30s     Give stats every 30 seconds
# -Pn                   Treat hosts as online (skip host discovery)
# -sT                   Full TCP connect, no syn machine guns
# -T4                   Timing 4, faster scan
# -p-                   Scan every port
# --max-retires 1       Only retry a port once
# --min-rate            Send packets at a minimum rate of defined
# -oA                   Give output in all three output formats
#
def nmapFullFastScan(ip_address):
   ip_address = ip_address.strip()
   print "INFO: Running general TCP/UDP nmap scans for " + ip_address
   #TCPSCAN = "nmap -n -vv --stats-every 30s -Pn -sT -T 4 -p- --max-retries 1 --min-rate 2000 -oA '/root/scripts/recon_enum/results/exam/nmap/%s_INITIAL' %s"  % (ip_address, ip_address)
   #UDPSCAN = "nmap -n -vv --stats-every 30s -Pn -sU -T 4 -p- --max-retries 1 --min-rate 2000 -oA '/root/scripts/recon_enum/results/exam/nmap/%sU_INITIAL' %s" % (ip_address, ip_address)
   #tcplines = subprocess.check_output(TCPSCAN, shell=True).split("\n")
   tcplines = subprocess.check_output(['nmap','-n','-vv','--stats-every','30s','-Pn','-sT','-T','4','-p-','--max-retries','1','--min-rate',FAST_NMAP_MIN_RATE,'-oA',"/root/scripts/recon_enum/results/exam/nmap/%s_INITIAL" % ip_address,ip_address]).split("\n")
   tcpPorts = []
   udpPorts = []
   for line in tcplines:
      line = line.strip()
      if ("tcp" in line) and ("open" in line) and not ("Discovered" in line):
         while "  " in line:
            line = line.replace("  ", " ");
         linesplit= line.split(" ")
         service = linesplit[2] # grab the service name
         port = line.split(" ")[0] # grab the port/proto
         port = port.split("/")[0]
         tcpPorts.append(port)
         print ("INFO: Quick Nmap for %s found TCP: %s on %s") % (ip_address, service, port)
   for port in tcpPorts: #the last element in the list is blank
      if port != "":
         multProc(nmapVersionTCPAndPass, ip_address, port)
   #udplines = subprocess.check_output(UDPSCAN, shell=True).split("\n")
   udplines = subprocess.check_output(['nmap','-n','-vv','--stats-every','30s','-Pn','-sU','-T','4','-p-','--max-retries','1','--min-rate',FAST_NMAP_MIN_RATE,'-oA',"/root/scripts/recon_enum/results/exam/nmap/%sU_INITIAL" % ip_address,ip_address]).split("\n")
   for line in udplines:
      line = line.strip()
      if ("udp" in line) and ("open" in line) and not ("Discovered" in line):
         while "  " in line:
            line = line.replace("  ", " ");
         linesplit= line.split(" ")
         service = linesplit[2] # grab the service name
         port = line.split(" ")[0] # grab the port/proto
         port = port.split("/")[0]
         udpPorts.append(port)
         print ("INFO: Quick Nmap for %s found UDP: %s on %s") % (ip_address, service, port)
   for port in udpPorts: #the last element in the list is blank
      if port != "":
         multProc(nmapVersionUDPAndPass, ip_address, port)
   print "INFO: General TCP/UDP nmap finished for %s. Tasks passed to designated scripts" % (ip_address)
   jobs = []
   q = multiprocessing.Process(target=nmapFullSlowScan, args=(scanip,)) #comma needed
   jobs.append(q)
   q.start()
   return

def nmapVersionTCPAndPass(ip_address, port):
   #need this to version ports and in case there is no recon module we'll have a scan for it. Runs default scripts.
   uniNmapTCP = "nmap -n -vv -Pn -A -sC -sT -T 4 -p %s -oA '/root/scripts/recon_enum/results/exam/nmap/%s_%s' %s"  % (port, ip_address, port, ip_address)
   #lines = subprocess.check_output(uniNmapTCP, shell=True).split("\n")
   lines = subprocess.check_output(['nmap','-n','-vv','-Pn','-A','-sC','-sT','-T','4','-p',port,'-oA',"/root/scripts/recon_enum/results/exam/nmap/%s_%s" % (ip_address,port),ip_address]).split("\n")
   print "INFO: nmap versioning for TCP %s:%s completed" % (ip_address, port)
   for line in lines:
      line = line.strip()
      if ("tcp" in line) and ("open" in line) and not ("Discovered" in line):
         while "  " in line:
            line = line.replace("  ", " ");
         linesplit= line.split(" ")
         service = linesplit[2] # grab the service name
         port = line.split(" ")[0] # grab the port/proto
         port = port.split("/")[0]
         if ("http" in service):
            multProc(httpEnum, ip_address, port)
         elif ("domain" in service):
            multProc(dnsEnum, ip_address, port)
         elif ("login" in service or "exec" in service or "shell" in service):
            multProc(rloginEnum, ip_address, port)
         elif ("finger" in service):
            multProc(fingerEnum, ip_address, port)
         elif ("ftp" in service):
            multProc(ftpEnum, ip_address, port)
         elif ("netbios-ssn" in service):
            multProc(smbEnum, ip_address,port)
         elif ("microsoft-ds" in service):
            multProc(smbEnum, ip_address, port)
         elif ("ms-sql" in service or "mssql" in service):
            multProc(mssqlEnum, ip_address, port)
         elif ("my-sql" in service or "mysql" in service):
            multProc(mysqlEnum, ip_address, port)
         elif ("nfs" in service):
            multProc(nfsEnum, ip_address, port)
         elif ("rdp" in service or "ms-wbt-server" in service):
            multProc(rdpEnum, ip_address, port)
         elif ("rpcbind" == service):
            multProc(rpcbindEnum, ip_address, port)
         elif ("ssh/http" in service or "https" in service):
            multProc(httpsEnum, ip_address, port)
         elif ("ssh" in service):
            multProc(sshEnum, ip_address, port)
         elif ("smtp" in service):
            multProc(smtpEnum, ip_address, port)
         elif ("telnet" in service):
            multProc(telnetEnum, ip_address, port)
         elif ("tftp" in service):
            multProc(tftpEnum, ip_address, port)

def nmapVersionUDPAndPass(ip_address, port):
   uniNmapUDP = "nmap -n -vv -Pn -A -sC -sU -T 4 -p %s -oA '/root/scripts/recon_enum/results/exam/nmap/%s_%sU.nmap' %s"  % (port, ip_address, port, ip_address)
   #lines = subprocess.check_output(uniNmapUDP, shell=True).split("\n")
   lines = subprocess.check_output(['nmap','-n','-vv','-Pn','-A','-sC','-sU','-T','4','-p',port,'-oA',"/root/scripts/recon_enum/results/exam/nmap/%s_%sU" % (ip_address,port),ip_address]).split("\n")
   print "INFO: nmap versioning for UDP %s:%s completed" % (ip_address, port)
   for line in lines:
      line = line.strip()
      if ("udp" in line) and ("open" in line) and not ("Discovered" in line):
         while "  " in line:
            line = line.replace("  ", " ");
         linesplit= line.split(" ")
         service = linesplit[2] # grab the service name
         port = line.split(" ")[0] # grab the port/proto
         port = port.split("/")[0]
         if ("domain" in service):
            multProc(dnsEnum, ip_address, port)
         elif ("snmp" in service):
            multProc(snmpEnum, ip_address, port)

#makedir function from https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
#Compatible with Python >2.5, but there is a more advanced function for python 3.5
def mkdir_p(path):
   try:
      os.makedirs(path)
   except OSError as exc: #Python >2.5
      if exc.errno == errno.EEXIST and os.path.isdir(path):
         pass
      else:
         raise

#Create the directories that are currently hardcoded in the script
#dotdotpwn directory for reports created automatically by dotdotpwn just in case user wants them
def createDirectories():
   scriptsToRun = "dirb","dirb/80","dirb/443","dotdotpwn","finger","ftp","http","ldap","msrpc","mssql","mysql","nfs","nikto","nmap","rdp","rpc","smb","smtp","snmp","ssh","telnet","tftp","whatweb"
   for path in scriptsToRun:
      mkdir_p("/root/scripts/recon_enum/results/exam/%s" % path)
   mkdir_p("/usr/share/dotdotpwn/Reports")

def backupExisting():
   print "INFO: Previous folders found, zipping backup"
   #tmp move targets.txt, zip files, backup, remove dirs, restore targets.txt
   movedTargets = False
   movedDotTemplate = False
   if os.path.isfile("/root/scripts/recon_enum/results/exam/targets.txt"):
      os.rename("/root/scripts/recon_enum/results/exam/targets.txt", "/root/scripts/recon_enum/results/targets.txt")
      movedTargets = True
   if os.path.isfile("/root/scripts/recon_enum/results/exam/dot_template"):
      os.rename("/root/scripts/recon_enum/results/exam/dot_template", "/root/scripts/recon_enum/results/dot_template")
      movedDotTemplate = True
   backupName = "backup_%s.tar.gz" % (time.strftime("%H:%M"))
   BACKUP = "tar czf /root/Downloads/%s /root/scripts/recon_enum/results/exam/* --remove-files" % (backupName)
   backupResults = subprocess.check_output(BACKUP, shell=True)
   if movedTargets == True:
      os.rename("/root/scripts/recon_enum/results/targets.txt", "/root/scripts/recon_enum/results/exam/targets.txt")
   if movedDotTemplate == True:
      os.rename("/root/scripts/recon_enum/results/dot_template", "/root/scripts/recon_enum/results/exam/dot_template")

#Symlink needed directories into /usr/share/wordlists
#This functionality for a distro like Kali
#Wordlists folder used for ftp and ssh recon scripts
def mksymlink():
   dirsToLink = "/root/lists","/root/lists/SecLists-master"
   dst = "/usr/share/wordlists"
   for path in dirsToLink:
      tmp = path.split("/")
      try:
         os.symlink(path, dst + "/" + tmp[-1])
      except OSError as exc:
         if exc.errno == errno.EEXIST:
            pass
         else:
            raise

# grab the discover scan results and start scanning up hosts
def printBanner():
   print "##############################################################"
   print "####                      RECON SCAN                      ####"
   print "####            A multi-process service scanner           ####"
   print "####        finger, http, mssql, mysql, nfs, nmap,        ####"
   print "####        rdp, smb, smtp, snmp, ssh, telnet, tftp       ####"
   print "##############################################################"
   print "############# Don't forget to start your TCPDUMP #############"
   print "############ Don't forget to start your RESPONDER ############"
   print "##############################################################"
   print "##### This tool relies on many others. Please ensure you #####"
   print "##### run setup.sh first and have all tools in your PATH #####"
   print "##############################################################"

#The script creates the directories that the results will be placed in
#User needs to place the targets in the results/exam/targets.txt file
if __name__=='__main__':
   printBanner()
   if os.path.isdir('/root/scripts/recon_enum/results/exam/nmap'):
      backupExisting()

   mksymlink()
   createDirectories()

   # CHANGE THIS!! grab the alive hosts from the discovery scan for enum
   # Also check Nmap user-agent string, should be set to Firefox or other
   if os.path.isfile('/root/scripts/recon_enum/results/exam/targets.txt'):
       if os.path.getsize('/root/scripts/recon_enum/results/exam/targets.txt') > 2: #0 is empty, 2 is file with \n
           try:
               f = open('/root/scripts/recon_enum/results/exam/targets.txt', 'r')
           except:
               raise
       else:
           print "ERROR: Is targets.txt blank?! Please ensure targets.txt is populated. Run aliverecon.py or something"
           exit(0)
   else:
        print "ERROR: No targets.txt detected! Please ensure targets.txt is populated. Run aliverecon.py or something"
        exit(0)

   for scanip in f:
      jobs = []
      if scanip[0] != "#":
         p = multiprocessing.Process(target=nmapFullFastScan, args=(scanip,)) #comma needed to only pass single arg
         jobs.append(p)
         p.start()
   f.close()
