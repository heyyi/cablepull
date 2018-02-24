echo "nameserver 10.106.16.22" >> /etc/resolv.conf
git clone https://github.com/axboe/fio 
grep Red /etc/*relase
RedFlag = $?
if [ $RedFlag == 0 ]
then 
   yum install gcc
   yum install libaio*
fi
grep SUSE /etc/*release
SLESFlag = $?
if [ $SLESFlag == 0 ]
then
   zypper install gcc
   zypper install libaio*
fi

cd fio
./configure
make 
make install
