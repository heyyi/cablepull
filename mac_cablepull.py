#!/usr/bin/python3
#  -*- coding:utf-8 -*-
#
#   Author  :   He, YI
#   E-mail  :   yi.he@dell.com
#   Date    :   25/12/17
#   Desc    :   do cable pull test based on wwpn only
#
import sys, getopt
import paramiko
import time
import logging
import re

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# default global setting

D_SwType = {"Brocade": 1, "Cisco": 2, "Mellanox": 3, "Arista": 4}
s_switchfile = "ipswitch.ini"
s_macfile = "mac.db"
D_mac2sw = dict()
D_sw = dict()

def read_until(channel,delimiter):
    data = ''
    while delimiter not in data:
        data += str(channel.recv(1),"utf-8")
    return data

def check_format(mac):
    if re.match(r"^([a-zA-Z0-9]{2}:){5}[a-zA-Z0-9]{2}", mac):
        pass
    elif re.match(r"^([a-zA-Z0-9]{4}.){2}[a-zA-Z0-9]{4}$", mac): \
            mac = mac[0:2] + ":" + mac[2:4] + ":" + mac[5:7] + ":" + mac[7:9] \
                  + ":" + mac[10:12] + ":" + mac[12:14]
    else:
        exit("mac format is incorrect")
    mac = str(mac).upper()
    return mac


def in_record(mac):
    mac_switch_dict = dict()
    with open(s_macfile, "r") as fp:
        for line in fp.readlines():
            (mkey, switch_ip) = line.split()
            mac_switch_dict[mkey] = switch_ip
    if mac in mac_switch_dict.keys():
        return mac_switch_dict[mac]
    else:
        return ""


def readMacList(s_macfile, D_mac2_sw):
    with open(s_macfile, "r") as fp:
        for line in fp.readlines():
            logger.debug(line)
            (mkey, sw_vlan, sw_ip, sw_port) = line.split()
            D_mac2sw[mkey] = [sw_vlan, sw_ip, sw_port]
    logger.debug(D_mac2sw)
    # return D_mac2sw


def readSwitchList(s_switchfile, D_sw):
    with open(s_switchfile, "r") as fp:
        for line in fp.readlines():
            if not line.startswith("#"):
                L_line = line.split()
                sw_type = L_line[0]
                sw_model = L_line[1]
                sw_name = L_line[2]
                sw_ip = L_line[3]
                sw_sn = L_line[4]
                sw_credential = L_line[5]
                D_sw[sw_ip] = [sw_type, sw_model, sw_name, sw_sn, sw_credential]

    logger.debug(D_sw)
    # return D_sw


def findMacOnSwitch(s_mac, sw_type, sw_ip, sw_crendential):
    global D_mac2sw
    sw_port = ""
    if sw_type == "Brocade":
        show_mac_cmd = "show mac-address-table | include Te\r\n"
    elif sw_type == "Mellanox":
        show_mac_cmd = "show mac-address-table | include Eth\r\n"
    elif sw_type == "Cisco":
        show_mac_cmd = "show mac address-table | include Eth\r\n"
    elif sw_type == "Arista":
        show_mac_cmd = "show mac address-table | include Et\r\n"

    user = sw_crendential.split("/")[0]
    passwd = sw_crendential.split("/")[1]
    logger.info("--------->Searching Mac on %s switch %s"%(sw_type,sw_ip))
    if sw_type == "Brocade":
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(sw_ip, username=user, password=passwd)
        channel = ssh.invoke_shell()
#        output = channel.recv(9999)
#        channel.send("\n")
        read_until(channel,'#')
       # channel.send("terminal length 0\n")
       # out = read_until(channel, '#')
       # time.sleep(.5)
        logger.debug(show_mac_cmd)
        channel.send(show_mac_cmd)
        out = read_until(channel, '#')
        logger.debug("the result is " + out)
        L_output = out.split("\n")
        logger.debug(L_output)
        for line in L_output:
            if "Dynamic" in line:
               # print("the record:", line)
                if line.split()[0].isdigit:
                    temp_vlan = line.split()[0]
                    logger.debug("vlan is " + temp_vlan)
                    temp_mac = line.split()[1]
                    logger.debug("temp_mac is " + temp_mac)
                    temp_mac = ''.join(temp_mac.split("."))
                    temp_mac = ':'.join(temp_mac[i:i + 2] for i in range(0, 12, 2)).upper()
                    logger.debug("transferred mac is " + temp_mac)
                    temp_port = line.split()[5]
                    D_mac2sw[temp_mac] = [temp_vlan, sw_ip, temp_port]
                    if temp_mac == s_mac:
                        sw_port = "Te" + temp_port
                        logger.info("mac %s is found in switch port %s" % (temp_mac, temp_port))
        ssh.close()
    elif sw_type == "Mellanox":
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(sw_ip, username=user, password=passwd)
        stdin, stdout, stderr = ssh.exec_command(show_mac_cmd)
        channel = ssh.invoke_shell()

        out = read_until(channel, '>')
        logger.debug(out)
        # time.sleep(.5)
        # channel.send("terminal length 100\n")
        # time.sleep(.5)
        # read_until(channel,'>')
        channel.send(show_mac_cmd)
        out = read_until(channel, '>')
        logger.debug("the result is " + out)
        L_output = out.split("\n")
        for line in L_output:
            if "Dynamic" in line:
                #print("the record:", line)
                if line.split()[0].isdigit:
                    temp_vlan = line.split()[0]
                    logger.debug("vlan is " + temp_vlan)
                    temp_mac = line.split()[1].upper()
                    logger.debug("temp_mac is " + temp_mac)
                    temp_port = line.split()[3]
                    D_mac2sw[temp_mac] = [temp_vlan, sw_ip, temp_port]
                    if temp_mac == s_mac:
                        sw_port = temp_port
                        logger.info("mac %s is found in switch port %s" % (temp_mac, temp_port))

        ssh.close()
    elif sw_type == "Cisco":
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(sw_ip, username=user, password=passwd)
        stdin, stdout, stderr = ssh.exec_command(show_mac_cmd)
        exit_status = stdout.channel.recv_exit_status()
        exit_output = stdout.readlines()
        L_output = exit_output
        for line in L_output:
            if "dynamic" in line:
                logger.debug("the record:" + line)
                if line.split()[0].isdigit:
                    temp_vlan = line.split()[1]
                    logger.debug("vlan is " + temp_vlan)
                    temp_mac = line.split()[2]
                    logger.debug("temp_mac is " + temp_mac)
                    temp_mac = ''.join(temp_mac.split("."))
                    temp_mac = ':'.join(temp_mac[i:i + 2] for i in range(0, 12, 2)).upper()
                    logger.debug("mac is " + temp_mac)
                    temp_port = line.split()[7]
                    D_mac2sw[temp_mac] = [temp_vlan, sw_ip, temp_port]
                    if temp_mac == s_mac:
                        sw_port = temp_port
                        logger.info("mac %s is found in switch port %s" % (temp_mac, temp_port))
        ssh.close()
    elif sw_type == "Arista":
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(sw_ip, username=user, password=passwd)
        channel = ssh.invoke_shell()
        read_until(channel,'>')
        channel.send("terminal length 0\r\n")
        #read_until(channel, '>')
        time.sleep(2)
        channel.recv(9999)
        channel.send(show_mac_cmd)
        out = read_until(channel,'>')
        logger.info("the result is " + out )
        L_output = out.split("\n")
        for line in L_output:
            if "DYNAMIC" in line:
                print("the record:", line)
                if line.split()[0].isdigit:
                    temp_vlan = line.split()[0]
                    logger.info("vlan is " + temp_vlan)
                    temp_mac = line.split()[1]
                    logger.info("temp_mac is " + temp_mac)
                    temp_mac = ''.join(temp_mac.split("."))
                    temp_mac = ':'.join(temp_mac[i:i + 2] for i in range(0, 12, 2)).upper()
                    temp_port = line.split()[3]
                    D_mac2sw[temp_mac] = [temp_vlan, sw_ip, temp_port]
                    if temp_mac == s_mac:
                        sw_port = temp_port
        ssh.close()

    return sw_port


def searchSwitch(s_mac, D_sw):
    # sw_port = ""
    #print(D_sw)
    global s_macfile
    for temp_ip in D_sw.keys():
        (sw_type, sw_model, sw_name, sw_sn, sw_credential) = D_sw[temp_ip]
        logger.debug("SearchMacOnSwitch " + sw_type + sw_model + sw_name + temp_ip + sw_sn + sw_credential)
        sw_port = findMacOnSwitch(s_mac, sw_type, temp_ip, sw_credential)
        if sw_port != "":
            with open(s_macfile, "w+") as fp:
                fp.seek(0)
                fp.truncate()
                for key, value in D_mac2sw.items():
                    line = key + " " + " ".join(value) + "\n"
                    fp.write(line)
            return (sw_type, temp_ip, sw_credential, sw_port)

    with open(s_macfile, "w+") as fp:
        fp.seek(0)
        fp.truncate()
        for key, value in D_mac2sw.items():
            line = key + " " + " ".join(value) + "\n"
            fp.write(line)

    exit("mac not found in switch")


#    channel = ssh.invoke_shell()
#    out = channel.recv(9999)
#    channel.send("nodefind {}\n".format(wwn))
#    time.sleep(.5)
#    out = channel.recv(9999)


def cable_pull(sw_type, sw_ip, sw_port, sw_crendential, i_interval, i_times, i_timeToWait):
    user = sw_crendential.split("/")[0]
    passwd = sw_crendential.split("/")[1]
    if sw_type == "Brocade":
        brocade_cablepull(sw_ip, sw_port, user, passwd, i_interval, i_times, i_timeToWait)
    elif sw_type == "Mellanox":
        mellanox_cablepull(sw_ip, sw_port, user, passwd, i_interval, i_times, i_timeToWait)
    elif sw_type == "Cisco":
        cisco_cablepull(sw_ip, sw_port, user, passwd, i_interval, i_times, i_timeToWait)
    elif sw_type == "Arista":
        arista_cablepull(sw_ip, sw_port, user, passwd, i_interval, i_times, i_timeToWait)


def brocade_cablepull(login_switch, s_port, user, passwd, i_interval, i_times, i_timeToWait):
    if i_interval < 0:
        exit("interval must be larger than 0")
    elif i_interval == 0:
        logger.info("interval = 0 will cause issue on switch, Changing it to 1")
        i_interval = 1

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(login_switch, username=user, password=passwd)
    channel = ssh.invoke_shell()
    read_until(channel,'#')
    channel.send('config t\n')
    time.sleep(.5)
    channel.recv(9999)
    s_port = s_port[0:2] + " " + s_port[2:]
    channel.send("interface {}\n".format(s_port))
    logger.info("interface {}\n".format(s_port))
    time.sleep(.5)
    out = channel.recv(9999)
    for i in range(i_times):
        logger.info("|||||||||||||||||||||||||||||||running the " + str(
            i + 1) + " round|||||||||||||||||||||||||||||||||||||||||||")
        logger.info("shutdown " + s_port + "\n")
        channel.send('shutdown\n')
        logger.info("||  waiting for " + str(i_interval) + "  seconds")
        time.sleep(i_interval)
        out = channel.recv(9999)
        logger.info("no shutdown " + s_port + "\n")
        channel.send('no shutdown\n')
        logger.info("||  waiting for " + str(i_timeToWait) + "  seconds")
        time.sleep(i_timeToWait)
        out = channel.recv(9999)
        logger.info("|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
    ssh.close()
    return 0


def cisco_cablepull(sw_ip, s_port, user, passwd, i_interval, i_times, i_timeToWait):
    if i_interval < 0:
        exit("interval must be larger than 0")
    elif i_interval == 0:
        logger.info("interval = 0 will cause issue on switch, Changing it to 1")
        i_interval = 1
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(sw_ip, username=user, password=passwd)
    channel = ssh.invoke_shell()
    read_until(channel,'#')
    channel.send('config t\n')
    time.sleep(.5)
    channel.recv(9999)
    channel.send("interface {}\n".format(s_port))
    time.sleep(.5)
    out = channel.recv(9999)

    for i in range(i_times):
        logger.info("|||||||||||||||||||||||||||||||running the " + str(
            i + 1) + " round|||||||||||||||||||||||||||||||||||||||||||")
        logger.info("shutdown " + s_port + "\n")
        channel.send('shutdown\n')
        logger.info("||  waiting for " + str(i_interval) + "  seconds")
        time.sleep(i_interval)
        out = channel.recv(9999)
        logger.info("no shutdown " + s_port + "\n")
        channel.send('no shutdown\n')
        logger.info("||  waiting for " + str(i_timeToWait) + "  seconds")
        time.sleep(i_timeToWait)
        out = channel.recv(9999)
        logger.info("|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
    ssh.close()
    # print "sleep 300s..."
    #  time.sleep(300)
    return 0


def mellanox_cablepull(login_switch, s_port, user, passwd, i_interval, i_times, i_timeToWait):
    if i_interval < 0:
        exit("interval must be larger than 0")
    elif i_interval == 0:
        logger.info("interval = 0 will cause issue on switch, Changing it to 1")
        i_interval = 1
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(login_switch, username=user, password=passwd)
    channel = ssh.invoke_shell()
    read_until(channel,'>')
    channel.send('enable\n')
    time.sleep(.5)
    channel.send('config t\n')
    read_until(channel,'#')
    temp_port = s_port[3:]
    logger.info("interface ethernet {}\n".format(temp_port))
    channel.send("interface ethernet {}\n".format(temp_port))
    time.sleep(.5)
    out = channel.recv(9999)

    for i in range(i_times):
        logger.info("|||||||||||||||||||||||||||||||running the " + str(
            i + 1) + " round|||||||||||||||||||||||||||||||||||||||||||")
        logger.info("shutdown " + s_port + "\n")
        channel.send('shutdown\n')
        logger.info("||  waiting for " + str(i_interval) + "  seconds")
        time.sleep(i_interval)
        out = channel.recv(9999)
        logger.info("no shutdown " + s_port + "\n")
        channel.send('no shutdown\n')
        logger.info("||  waiting for " + str(i_timeToWait) + "  seconds")
        time.sleep(i_timeToWait)
        out = channel.recv(9999)
        logger.info("|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
    ssh.close()
    # print "sleep 300s..."
    #  time.sleep(300)
    return 0


def arista_cablepull(login_switch, s_port, user, passwd, i_interval, i_times, i_timeToWait):
    if i_interval < 0:
        exit("interval must be larger than 0")
    elif i_interval == 0:
        logger.info("interval = 0 will cause issue on switch, Changing it to 1")
        i_interval = 1
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
        logger.info("|||||||||||||||||||||||||||||||running the " + str(
            i + 1) + " round|||||||||||||||||||||||||||||||||||||||||||")
        logger.info("shutdown " + s_port + "\n")
        channel.send('shutdown\n')
        time.sleep(i_interval)
        out = channel.recv(9999)
        logger.info("||  waiting for " + str(i_interval) + "  seconds")
        logger.info("no shutdown " + s_port + "\n")
        channel.send('no shutdown\n')
        logger.info("||  waiting for " + str(i_timeToWait) + "  seconds")
        time.sleep(i_timeToWait)
        out = channel.recv(9999)
        logger.info("|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
    ssh.close()
    # print "sleep 300s..."
    #  time.sleep(300)
    return 0


def main(argv):
    s_mac = ''
    i_interval = 60
    i_times = 1
    s_interval = ""
    s_times = ""
    s_timeToWait = ""
    queryOnly = False
    try:
        opts, args = getopt.getopt(argv, "hqm:i:n:d:t:", ["help", "query", "mac=", "interval=", "number=", "dest=", \
                                                          "timeToWait="])
    except getopt.GetoptError:
        print("mac_cablepull.py -m <mac> -i <interval> -n <times>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('mac_cablepull.py -m <mac> -i <interval> -n <times>')
            sys.exit()
        elif opt == "-q":
            queryOnly = True
        elif opt in ("-m", "--mac"):
            s_mac = arg
            s_mac = check_format(s_mac)
        elif opt in ("-i", "--interval"):
            s_interval = arg
            i_interval = int(s_interval)
        elif opt in ("-n", "--number"):
            s_times = arg
            i_times = int(s_times)
        elif opt in ("-d", "--dest"):
            destination = arg
        elif opt in ("-t", "--timeToWait"):
            s_timeToWait = arg
            i_timeToWait = int(s_timeToWait)

    # pattern = re.compile(r'hello')
    # if re.match(r"(^[a-zA-Z0-9]{2}[:]){7,7}[a-zA-Z0-9]{2}$", s_wwpn):
    if s_mac == "":
        print("mac_calepull.py -m <mac> -i <interval> -n <times>")
        exit()

    if s_timeToWait == "":
        i_timeToWait = i_interval

    logger.info(
        "==================================runnning cable pull per below input=====================================")
    logger.info('mac:' + s_mac)
    logger.info('Interval:' + str(i_interval))
    logger.info('Number of times:' + str(i_times))

    global D_mac2sw
    global D_sw
    readMacList(s_macfile, D_mac2sw)
    readSwitchList(s_switchfile, D_sw)
    logger.debug("D_sw is:")
    logger.debug(D_sw)

    if s_mac in D_mac2sw.keys():
        logger.info(s_mac + " in  mac.db")
        sw_ip = D_mac2sw[s_mac][1]
        logger.debug(sw_ip)
        sw_crendential = D_sw[sw_ip][4]
        sw_type = D_sw[sw_ip][0]
        sw_port = findMacOnSwitch(s_mac, sw_type, sw_ip, sw_crendential)
        if sw_port:
            if queryOnly != True:
                cable_pull(sw_type, sw_ip, sw_port, sw_crendential, i_interval, i_times, i_timeToWait)
        else:
            (sw_type, switch_ip, sw_crendential, sw_port) = searchSwitch(s_mac, D_sw)
            if queryOnly != True:
                cable_pull(sw_type, sw_ip, sw_port, sw_crendential, i_interval, i_times, i_timeToWait)


    else:
        logger.info(s_mac + " no in mac.db")
        (sw_type, sw_ip, sw_crendential, sw_port) = searchSwitch(s_mac, D_sw)
        if queryOnly != True:
            cable_pull(sw_type, sw_ip, sw_port, sw_crendential, i_interval, i_times, i_timeToWait)

    logger.info('switch type: ' + sw_type)
    logger.info('switch IP: ' + sw_ip)
    logger.info('switch port: ' + sw_port)
    logger.info('switch credential: ' + sw_crendential)

'''    with open(s_macfile, "w+") as fp:
        fp.seek(0)
        fp.truncate()
        for key, value in D_mac2sw.items():
            line = key + " " + " ".join(value) + "\n"
            fp.write(line)
'''

if __name__ == "__main__":
    main(sys.argv[1:])
