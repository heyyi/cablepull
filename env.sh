echo "nameserver 10.106.16.22" >> /etc/resolv.conf
git clone https://github.com/axboe/fio 
zypper install gcc
zypper install libaio*
cd fio
./configure
make 
make install
