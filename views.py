from django.shortcuts import render
from django.shortcuts import HttpResponse
from lib.funcLib import searchSwitch

switch_list = [
    {"login_switch":"test", "port":"port0", "user":"user0", "password":"password0"}
]
def hello(request):
#    return HttpResponse("hello world!")
    if request.method == "POST":
        wwn = request.POST.get("wwpn", None)
        interval = request.POST.get("interval", None)
        times = request.POST.get("times", None)
#        (switch_type, login_switch, s_port) = searchSwitch(wwn)
        print(wwn, interval, times)
#        temp = {"login_switch":login_switch, "port":s_port, "user":"user0", "password":"password0"}

    return render(request,"main.html")
#    return render(request, "main.html", {"data":switch_list})

# Create your views here.



    def ConvertRevs(self, startrev, endrev, bUpdLineCount, maxtrycount=3):
        self.printVerbose("Converting revisions %d to %d" % (startrev, endrev))
        if( startrev < endrev):
            logging.info("Updating revision from %d to %d" % (startrev, endrev))
            svnloglist = svnlogiter.SVNRevLogIter(self.svnclient, startrev, endrev)
            revcount = 0
            lc_updated = 'N'
            if( bUpdLineCount == True):
                lc_updated = 'Y'
            lastrevno = 0
            output = None
            for revlog in svnloglist:
                logging.debug("Revision author:%s" % revlog.author)
                logging.debug("Revision date:%s" % revlog.date)
                revcount = revcount+1
                addedfiles, changedfiles, deletedfiles = revlog.changedFileCount()                
                if( revlog.isvalid() == True):
                    self.rows += 1
                    for change in revlog.getDiffLineCount(bUpdLineCount):
                        filename = change.filepath_unicode()
                        changetype = change.change_type()
                        linesadded = change.lc_added()
                        linesdeleted = change.lc_deleted()
                             
                        #print "%d : %s : %s : %d : %d " % (revlog.revno, filename, changetype, linesadded, linesdeleted)
                        output += "\n %s : %s : %s : %d : %d \n " % (filename, changetype, revlog.author, linesadded, linesdeleted)
                    lastrevno = revlog.revno
                    #commit after every change
                logging.debug("Number revisions converted : %d (Rev no : %d)" % (revcount, lastrevno))
                self.printVerbose("Number revisions converted : %d (Rev no : %d)" % (revcount, lastrevno))
 
            return (output)