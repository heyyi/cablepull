#!/usr/local/bin/python3
#  -*- coding:utf-8 -*-
#
#   Author  :   He, YI
#   E-mail  :   yi.he@dell.com
#   Date    :   24/12/17
#   Desc    :   create file system on specific array's LUNs and start IO
#   Update  :   11/01/18

import subprocess
import platform
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def judge_multipath():
    '''
    find out the multipath software in the 
    '''

    multipath_type = -1
    pp_flag = subprocess.call(["which", "powermt"])
    mpio_flag = subprocess.call(["which", "multipath"])
    if pp_flag == 0:
        multipath_type = 1
        query_cmd = "powermt display dev=all | grep power"
        dev_prefix = "/dev/"
    elif mpio_flag == 0:
        multipath_type = 0
        query_cmd = "multipath -ll|grep mpath"
        dev_prefix = "/dev/mapper/"

    return (multipath_type, dev_prefix, query_cmd)




def filterUsedLun(L_lun):
    pv_cmd = "pvscan | grep 'mpath\|power'"
    df_cmd = "df -k | grep mpath"

#    (multipath_type, dev_prefix, query_cmd) = judge_multipath()

    p = subprocess.Popen(pv_cmd, shell=True, stdout=subprocess.PIPE)
    output, err = p.communicate()
    for line in output.splitlines():
        temp_dev = str(line.split()[1],"utf-8").strip()
        L_lun = list(filter(lambda x: x != temp_dev, L_lun))


    p = subprocess.Popen(df_cmd, shell=True, stdout=subprocess.PIPE)
    output, err = p.communicate()
    for line in output.splitlines():
        temp_dev = str(line.split()[0],"utf-8").strip()
        L_lun = list(filter(lambda x: x != temp_dev, L_lun))

    linux_dis = platform.linux_distribution()
    if linux_dis[0].find("SUSE") != -1:
        fence_cmd = "systemctl status sbd | grep slot"
        p = subprocess.Popen(fence_cmd, shell=True, stdout=subprocess.PIPE)
        output, err = p.communicate()
        for line in output.splitlines():
            temp_dev = str(line.split()[3],"utf-8").strip()
            L_lun = list(filter(lambda x: x != temp_dev, L_lun))



    return L_lun

def list_lun():
    '''
    list all the luns and label them with array id, filter out the luns in use
    '''
    L_lun = list()
    L_Avlun = list()
    #remove_list = []
    (multipath_type, dev_prefix, query_cmd) = judge_multipath()

    logger.debug("the multipath is:", multipath_type)
    p = subprocess.Popen(query_cmd, shell=True, stdout=subprocess.PIPE)
    output, err = p.communicate()
    for line in output.splitlines():
        # temp_dev = str((line.split())[0],"utf-8")
        temp_dev = str(line.split()[0], "utf-8")
        L_lun.append(dev_prefix+temp_dev)

    L_AvLun = filterUsedLun(L_lun)
    D_lun = labelbyId(L_AvLun)
    return D_lun

def labelbyId(L_lun):

    D_lun = dict()
    for tempdev in L_lun:
        #temp_list = list()
        sg_inq_cmd = "sg_inq " + tempdev
        p = subprocess.Popen(sg_inq_cmd, shell=True, stdout=subprocess.PIPE)
        output, err = p.communicate()
        for line in output.splitlines():
            line = str(line, "utf-8")
            # temp_dev = str((line.split())[0],"utf-8")
            if "Vendor identification" in line:
                s_vendor = line.split(":")[1]
            if "Product identification" in line:
                s_product = line.split(":")[1]
            if "Unit serial number" in line:
                s_unitSN = line.split(":")[1]
                if "XtremApp" in s_product:
                    s_ArraySN = "FNM" + s_unitSN[3:]
                else:
                    s_ArraySN = s_unitSN[0:7]

                #        if s_ArraySN in S_lun.keys():
                # if tempdev not in S_lun[s_ArraySN][1]:
                #             D_lun = S_lun[s_ArraySN][1]
                #             D_lun.append(tempdev)
                #             S_lun[s_ArraySN][1] = D_lun
                #        else:
                #            D_lun.append(tempdev)
                #            S_lun[s_ArraySN][1] = D_lun
        s_array = s_vendor + s_product + s_ArraySN
        if s_array in D_lun.keys():
            D_lun[s_array].append(tempdev)
        else:
            D_lun[s_array] = [tempdev]

    return D_lun


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
            logger.info("the support file system is :" + str(rhel6_fs))
            ls_fs = rhel6_fs
    elif linux_dis[0].find("SUSE") != -1:
        if linux_dis[1].startswith('12'):
            logger.info("the support file system is :" + str(sles12_fs))
            ls_fs = sles12_fs
        elif linux_dis[1].startswith('11'):
            logger.info("the support file system is :" + str(sles11_fs))
            ls_fs = sles11_fs
    else:
        logger.info("the support file system is :" + str(default_fs))
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
    with open('./mounted_file', "w+") as fp:
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
                fp.write("/zoner/" + mnt_dev + "\n")
            else:
                logger.info(cmd + ":" + "failed")

    return L_dir

def prepare_iozone(L_lun):
    with open('./iozone_list', "w+") as fp:
        fp.seek(0)
        fp.truncate()
        for dev in L_lun:
            mnt_dev = (dev.split('/'))[-1]
            fp.write(mnt_dev + "\n")
        
        

def prepare_fio(L_dir):
#    global fio_exist
#    if fio_exist == 0:
        with open("fio.ini", "w") as fp:
            fp.seek(0)
            fp.truncate()
            fp.write("[global]\n")
            fp.write("rate_iops=200\n")
            fp.write("size=1g\n")
            fp.write("runtime=999999999\n")
            fp.write("time_based=1\n")
            fp.write("direct=1\n")
            fp.write("ioengine=libaio\n")
            #fp.write("iodepth=32\n")
            fp.write("bsrange=4k-64k\n")
            fp.write("verify=md5\n")
            fp.write("rw=randrw\n")
            fp.write("rwmixread=83\n")
            fp.write("percentage_random=80\n")
            fp.write("group_reporting=1\n")
            for index, dir in enumerate(L_dir):
                logger.info(dir)
                fp.write('[' + str(index) + '_' + (dir.split('/'))[-1] + ']' + "\n")
                fp.write('directory=' + dir + "\n")
            #    fp.write("rw=rw\n")


def prepare_vdbenchraw(L_AvLun):
    with open("devs.vdb", "w") as fp:
        fp.seek(0)
        fp.truncate()
        for index, temp_dev in enumerate(L_AvLun):
            logger.info(temp_dev)
            fp.write("sd=sd%d,lun=%s,openflags=o_direct\n" % (index+1, temp_dev) )

            #    fp.write("rw=rw\n")

def startIO():
    fio_cmd = "screen fio fio.ini --output=fio.log"
 #   proc = subprocess.Popen(fio_cmd, shell=True)


 #p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
 #      output, err = p.communicate()
 #      p_status = p.wait()
 #      logger.debug(cmd + "output : ", output)
 #      if p_status == 0:
 #         logger.info(cmd + ":" + "successful")
 #      else:
 #         logger.info(cmd + ":" + "failed")

def FilterByArrayId(D_lun):
    print("Please choose which array's LUNs to make filesystem:")
    i = 0
    L_array = list()
    for arrayId in D_lun.keys():
        print(str(i+1) + "." + arrayId )
        i = i + 1
        L_array.append(arrayId)

    s_choice = input('input your choice:')
    while int(s_choice) not in range(i+1):
        s_choice = input('input your choice with right digit:')
    L_lun = D_lun[L_array[int(s_choice)-1]]
    return L_lun








# def find(name, path):
#    for root, dirs, files in os.walk(path):
#        if name in files:
#            return os.path.join(root, name)
def main():
    L_Avlun = []
    fio_exist = subprocess.call(["which", "fio"])
    if fio_exist != 0:
        logger.info("fio is not installed! ")
        exit()
    D_lun = list_lun()
    L_AvLun = FilterByArrayId(D_lun)
    print(L_AvLun)
    #prepare_vdbenchraw(L_AvLun)

    # L_lun = list_lun_byArrayId()



    format_lun(L_AvLun)
    L_dir = mount_lun(L_AvLun)
    prepare_iozone(L_AvLun)
    prepare_fio(L_dir)
#    start_fio(L_dir)


main()
