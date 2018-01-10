[root @ e2e - 4 - 10040 IOScript]  # cat MassiveIO.py
# !/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   He, YI
#   E-mail  :   yi.he@dell.com
#   Date    :   24/12/17
#   Desc    :   create file system on specific array's LUNs and start IO
#

import subprocess
import platform
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

L_lun = []


def judge_multipath():
    '''
    find out the multipath software in the 
    '''
    pp_flag = subprocess.call(["which", "powermt"])
    mpio_flag = subprocess.call(["which", "multipath"])
    if pp_flag == 0:
        multipath_type = 1
    elif mpio_flag == 0:
        multipath_type = 0
    else:
        multipath_type = -1
    return multipath_type


def list_lun():
    '''
    find out the LUNs from specific array by array id and filter out the luns in use
    '''
    L_lun = []
    remove_list = []
    array_id = input('Please enter your array_id:')
    multipath_type = judge_multipath()
    if multipath_type == 0:
        query_cmd = "multipath -ll|grep mpath|grep " + str(array_id)
        pv_cmd = "pvscan | grep mpath"
        df_cmd = "df -k | grep mpath"
        dev_prefix = "/dev/mapper/"
    elif multipath_type == 1:
        query_cmd = "powermt display dev=all | grep power"
        pv_cmd = "pvscan | grep power"
        df_cmd = "df -k | grep power"
        dev_prefix = "/dev/"

    logger.debug("the multipath is:", multipath_type)
    p = subprocess.Popen(query_cmd, shell=True, stdout=subprocess.PIPE)

    output, err = p.communicate()
    for line in output.splitlines():
        # temp_dev = str((line.split())[0],"utf-8")
        temp_dev = str(line.split()[0])
        L_lun.append(dev_prefix + temp_dev)

    p = subprocess.Popen(pv_cmd, shell=True, stdout=subprocess.PIPE)

    output, err = p.communicate()
    for line in output.splitlines():
        temp_dev = str(line.split()[1])
        L_lun = filter(lambda x: x != temp_dev, L_lun)

    p = subprocess.Popen(df_cmd, shell=True, stdout=subprocess.PIPE)

    output, err = p.communicate()
    for line in output.splitlines():
        # temp_dev = str((line.split())[0],"utf-8")
        L_lun = filter(lambda x: x != temp_dev, L_lun)

    return L_lun


def format_lun(L_lun):
    '''
    Make the file system on the listed LUNs
    '''
    rhel7_fs = sles12_fs = ("ext2", "ext3", "ext4", "xfs", "btrfs")
    rhel6_fs = ("ext2", "ext3", "ext4", "xfs")
    sles11_fs = ("ext2", "ext3", "xfs", "btrfs", "ReiserFS")
    default_fs = ("ext2", "ext3")
    linux_dis = platform.linux_distribution()
    logger.info("the current linux distribution is " + linux_dis[0] + " " + linux_dis[1])
    if linux_dis[0].find("Red") != -1:
        if linux_dis[1].startswith('7'):
            logger.info("the support file system is :" + str(rhel7_fs))
            ls_fs = rhel7_fs
        elif linux_dis[1].startswith('6'):
            logger.info("the support file system is :" + rhel6_fs)
            ls_fs = rhel6_fs
    elif linux_dis[0].find("SLES") != -1:
        if linux_dis[1].startswith('12'):
            logger.info("the support file system is :" + sles12_fs)
            ls_fs = sles12_fs
        elif linux_dis[1].startswith('11'):
            logger.info("the support file system is :" + sles11_fs)
            ls_fs = sles11_fs
    else:
        logger.info("the support file system is :" + default_fs)
        ls_fs = default_fs
    n_fs = len(ls_fs)
    for index, key in enumerate(L_lun):
        i_type = index % n_fs
        if ls_fs[i_type] == "xfs" or ls_fs[i_type] == "btrfs":
            mkfs_opt = "-f"
        else:
            mkfs_opt = ""
        cmd = 'mkfs.' + ls_fs[i_type] + " " + mkfs_opt + " " + key
        # print(cmd)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        output, err = p.communicate()
        p_status = p.wait()
        logger.debug(cmd + "output : ", output)
        if p_status == 0:
            logger.info(cmd + ":" + "successful")
        else:
            logger.info(cmd + ":" + "failed")

    return 0


def mount_lun(L_lun):
    with open('./mounted_file', "r+") as fp:
        fp.seek(0)
        fp.truncate()
        L_dir = []
        for dev in L_lun:
            mnt_dev = (dev.split('/'))[-1]
            cmd = 'mkdir -p ' + '/zoner/' + mnt_dev
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
            output, err = p.communicate()
            p_status = p.wait()
            logger.debug(cmd + "output : ", output)
            if p_status == 0:
                logger.info(cmd + ":" + "successful")
            else:
                logger.info(cmd + ":" + "failed")

            cmd = 'mount ' + dev + ' ' + '/zoner/' + mnt_dev
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
            output, err = p.communicate()
            p_status = p.wait()
            logger.debug(cmd + "output : ", output)
            if p_status == 0:
                logger.info(cmd + ":" + "successful")
                L_dir.append("/zoner/" + mnt_dev)
                fp.write("/zoner/" + mnt_dev)
            else:
                logger.info(cmd + ":" + "failed")

    return L_dir


def start_IO(L_dir):
    global fio_exist
    if fio_exist == 0:
        with open("fio.ini", "w") as fp:
            fp.seek(0)
            fp.truncate()
            fp.write("[global]\n")
            fp.write("rate_iops=200\n")
            fp.write("size=1g\n")
            fp.write("runtime=999999999\n")
            fp.write("time_based=1\n")
            fp.write("direct=1\n")
            fp.write("buffered=0\n")
            fp.write("ioengine=libaio\n")
            fp.write("iodepth=32\n")
            fp.write("bsrange=4k-64k\n")
            fp.write("verify=md5\n")
            for index, dir in enumerate(L_dir):
                logger.info(dir)
                fp.write('[' + str(index) + '_' + (dir.split('/'))[-1] + ']' + "\n")
                fp.write('directory=' + dir + "\n")
                fp.write("rw=rw\n")
            fio_cmd = "fio fio.ini"
            proc = subprocess.Popen(fio_cmd, shell=True)


# p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
#       output, err = p.communicate()
#       p_status = p.wait()
#       logger.debug(cmd + "output : ", output)
#       if p_status == 0:
#          logger.info(cmd + ":" + "successful")
#       else:
#          logger.info(cmd + ":" + "failed")



# def find(name, path):
#    for root, dirs, files in os.walk(path):
#        if name in files:
#            return os.path.join(root, name)

fio_exist = subprocess.call(["which", "fio"])
if fio_exist != 0:
    logger.info("fio is not installed! ")
    exit()

L_lun = list_lun()
# format_lun(L_lun)
L_dir = mount_lun(L_lun)
start_IO(L_dir)

