# -*- coding:utf-8 -*-
#
#   Author  :   He, YI
#   E-mail  :   yi.he@dell.com
#   Date    :   25/12/17
#   Desc    :   do switch search on wwpn only
#
import sys, getopt
import paramiko
import time
import logging
import re

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

#default global setting
BroSearchSwitch = ["10.228.99.11", "emc/Elab0123"]
CiscoSearchSwitch = ["10.228.99.17", "emc/Emc12345"]
vsan_id = ["25"]
L_Switch_Type = {1:"brocade", 2:"cisco"}
s_switchfile = "switch.ini"

def searchSwitch(wwn):
    login_switch = ""


###search wwn on Brocade switch
#nodefind wwn to find brocade fcid
    switchip = BroSearchSwitch[0]
    user = BroSearchSwitch[1].split("/")[0]
    passwd = BroSearchSwitch[1].split("/")[1]
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(switchip, username=user, password=passwd)
    cmd = "nodefind" + " " + wwn
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    exit_output = stdout.readlines()
    s_port = ""
    switch_type = 0

    for line in exit_output:
        logger.debug(line)
        if line.find('No device found') != -1:
            switch_type = 0
            break

        else:
            switch_type = 1
            fid = exit_output[2].split(";")[0].split()[1]
            if line.find('Port Index') != -1:
                item = line.split(":")
                s_port = item[1]

# fabricshow to find brocade login switchc IP
    if switch_type == 1:
        ssh.connect(switchip, username=user, password=passwd)
        cmd = "fabricshow"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        exit_output = stdout.readlines()
        fabricShowData = exit_output
        for line in fabricShowData:
            if line.find('fffc') != -1:
                temp_switch_info = line.split()
                switch_id = (temp_switch_info[1]).strip()
                if switch_id[4:6] == fid[0:2]:
                    login_switch = temp_switch_info[3]



## search on Cisco switch
# if not on brocade switch, show fcns database to find fcid on cisco switch
    if switch_type == 0:
        switchip = CiscoSearchSwitch[0]
        user = CiscoSearchSwitch[1].split("/")[0]
        passwd = CiscoSearchSwitch[1].split("/")[1]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(switchip, username=user, password=passwd)
        cmd = "show fcns database | include " + " " + wwn
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        exit_output = stdout.readlines()
        if 0 == len(exit_output) :
            exit("error--------------->>>>>>>>>>>>>>>wwpn not found in fabric 25")

        for line in exit_output:
            logger.debug(line)
            if line.split()[0] != "":
                switch_type = 2
                fid = line.split()[0]
#show fcns database fcid 0x12345 detail vsan 5 to find the cisco login switch IP
        ssh.connect(switchip, username=user, password=passwd)
        cmd = "show fcns database fcid " + fid + " detail vsan " + vsan_id[0]
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        exit_output = stdout.readlines()
        for line in exit_output:
            logger.debug(line)
            if line.find("connected interface") != -1:
                s_port = line.split(":")[1]

            if line.find("IP address") != -1:
                login_switch = line.split(":")[1]
                login_switch = login_switch.split()[1]
                login_switch = login_switch[1:-1]
        logger.info("========================switch port info===========================================")
        logger.info("Switch type : " + L_Switch_Type[switch_type])
        logger.info("Login switch : " + login_switch, )
        logger.info("Switch port :" + s_port)


    return(switch_type, login_switch, s_port)


#    channel = ssh.invoke_shell()
#    out = channel.recv(9999)
#    channel.send("nodefind {}\n".format(wwn))
#    time.sleep(.5)
#    out = channel.recv(9999)


def searchCredential(s_ip, s_switchfile):
    with open(s_switchfile,"r") as fp:
        for line in fp.readlines():
            L_switchRecord = line.split()
            if L_switchRecord[2] == s_ip:
                sw_model = L_switchRecord[1]
                sw_ip = L_switchRecord[2]
                sw_credential = L_switchRecord[3]
    logger.info("the login switch is: " + sw_model + "(" + sw_ip + ")" + ":" + sw_credential)

    return (sw_model, sw_credential)





def brocade_cablepull(login_switch, s_port, user, passwd, i_interval, i_times):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(login_switch, username=user, password=passwd)
    channel = ssh.invoke_shell()
    out = channel.recv(9999)
    for i in range(i_times):
        logger.info("|||||||||||||||||||||||||||||||running the " + str(i+1) + " round|||||||||||||||||||||||||||||||||||||||||||")
        logger.info("shutdown " + s_port + "\n")
        channel.send("portdisable -i {}\n".format(s_port))
        time.sleep(i_interval)
        out = channel.recv(9999)
        logger.info("no shutdown " + s_port + "\n")
        channel.send("portenable -i {}\n".format(s_port))
        time.sleep(i_interval)
        out = channel.recv(9999)
        logger.info("||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")

    return 0


def cisco_cablepull(login_switch, s_port, user, passwd, i_interval, i_times):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(login_switch, username=user, password=passwd)
    channel = ssh.invoke_shell()
    out = channel.recv(9999)
    channel.send('config t\n')
    time.sleep(.5)
    out = channel.recv(9999)
    channel.send("interface {}\n".format(s_port))
    time.sleep(.5)
    out = channel.recv(9999)

    for i in range(i_times):

        logger.info("|||||||||||||||||||||||||||||||running the " + str(i+1) + " round|||||||||||||||||||||||||||||||||||||||||||")
        logger.info("shutdown " + s_port + "\n")
        channel.send('shutdown\n')
        time.sleep(i_interval)
        out = channel.recv(9999)
        logger.info("no shutdown " + s_port + "\n")
        channel.send('no shutdown\n')
        time.sleep(i_interval)
        out = channel.recv(9999)
        logger.info("|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")

    # print "sleep 300s..."
    #  time.sleep(300)
    return 0




def main(argv):
   s_wwpn = ''
   i_interval = 60
   i_times = 1
   s_interval = ""
   s_times = ""
   queryOnly = False
   try:
      opts, args = getopt.getopt(argv,"hqw:i:n:d:",["help", "query", "wwpn=", "interval=","number=", "dest="])
   except getopt.GetoptError:
      print("cablepull.py -w <wwpn> -i <interval> -n <times>")
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print('cablepull.py -w <wwpn> -i <interval> -n <times>')
         sys.exit()
      elif opt == "-q":
         queryOnly = True
      elif opt in ("-w", "--wwpn"):
         s_wwpn = arg
      elif opt in ("-i", "--interval"):
         s_interval = arg
         i_interval = int(s_interval)
      elif opt in ("-n", "--number"):
         s_times = arg
         i_times = int(s_times)
      elif opt in ("-d", "--dest"):
         destination = arg
   #pattern = re.compile(r'hello')
   #if re.match(r"(^[a-zA-Z0-9]{2}[:]){7,7}[a-zA-Z0-9]{2}$", s_wwpn):
   if s_wwpn == "":
       print("cablepull.py -w <wwpn> -i <interval> -n <times>")
       exit()
   elif re.match(r"^([a-zA-Z0-9]{2}:){7}[a-zA-Z0-9]{2}", s_wwpn):
       pass
   elif re.match(r"^[a-zA-Z0-9]{16}$", s_wwpn):
       s_wwpn = s_wwpn[0:2] + ":" + s_wwpn[2:4] + ":" +  s_wwpn[4:6]  + ":" + s_wwpn[6:8] \
           + ":" + s_wwpn[8:10] + ":" + s_wwpn[10:12] + ":" + s_wwpn[12:14] + ":" + s_wwpn[14:16]

   else:
       exit("wwpn format is incorrect")



   logger.info("==================================runnning cable pull per below input=====================================")
   logger.info('WWPN:' + s_wwpn)
   logger.info('Interval:' + str(i_interval))
   logger.info('Number of times:' + str(i_times))

   (switch_type, login_switch, s_port) = searchSwitch(s_wwpn)

   (sw_model, sw_credential) = searchCredential(login_switch, s_switchfile)
   logger.info("the port : " + s_port)

   if queryOnly == True:
       return 0




       #print(switch)
   user = sw_credential.split("/")[0]
   passwd = sw_credential.split("/")[1]


   filerecord = s_wwpn.replace(":", "") + ".txt"
   with open(filerecord, "w") as fp:
       fp.seek(0)
       fp.truncate()
       fp.write("brand : " + L_Swtich_Type[switch_type] + "\n")
       fp.write("ip : " + login_switch + "\n")
       fp.write("model : " + sw_model + "\n")
       fp.write("port : " + s_port + "\n")
       fp.write("user : " + user + "\n" )
       fp.write("password : " + passwd + "\n")


   logger.info("=====================================starting cable pull on switch===================================")
   if switch_type == 1:
      brocade_cablepull(login_switch, s_port, user, passwd,i_interval, i_times)
   elif switch_type == 2:
      cisco_cablepull(login_switch, s_port, user, passwd, i_interval, i_times)
   else:
      pass





if __name__ == "__main__":
   main(sys.argv[1:])
