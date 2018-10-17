#!/usr/bin/env python2
from __future__ import print_function
import sys, os
import time
import subprocess
import copy

RAWGITURL="https://raw.githubusercontent.com/tdene/Magic/master/"

# "installation" script:
# wget -O - https://raw.githubusercontent.com/tdene/Magic/master/magic.py > magic.py && chmod u+x magic.py && ./magic.py

INFILE=None
OUTFILE=None
NOUPDATE=None
STRETCH=None
FLIP=None
ANALYZE=None
IRSIM=None
NOWELL=None
NOSTRCON=None
JUSTTHIS=None
TS=str(int(time.time()))+'.451' #personal flair

VDD=None
GND=None

_MINDIFCON=10

SCRIPTDIR=os.path.dirname(os.path.realpath(sys.argv[0]))
HOMEDIR=None

def _flatlist(l):
    ret=[]
    for k in l:
        for a in k:
            ret.append(a)
    return ret

def _intsplit(l):
    def eint(x):
        try:
            return int(x)
        except: 
            return x
    return [eint(x) for x in l.split(' ')]

def _npswap(s):
    if s in ['polysilicon','nwell','polycontact']:
        return s
    if s=='nsubstratencontact':
        return 'psubstratepcontact'
    if s=='psubstratepcontact':
        return 'nsubstratencontact'
    if s[0]=='n':
        return 'p'+s[1:]
    if s[0]=='p':
        return 'n'+s[1:]
    return s

def _topbottom(dic):
    top=None; bot=None;
    for a in dic:
        if a in ['labels','header','nwell']:
            continue
        for b in dic[a]:
            for c in b:
                if top==None or top<c[1]:
                    top=c[1]
                if bot==None or bot>c[1]:
                    bot=c[1]
    return (top,bot)

z2n = lambda x: (2*x-1)

def _stretch(dic,line,dr,dl,le,lcont=[]):
    f=lambda dr,dl: -1*z2n(dl)*z2n(dr)
    for a in dic:
        if a in ['header']:
            continue
        for b in dic[a]:
            if a=='labels':
                b=b[0]
            if z2n(dr)*(line-b[dr][1])<=0 and z2n(dr)*(line-b[1-dr][1])>0:
                contflag=a in ['ndcontact','pdcontact']
                contflag=contflag and (NOSTRCON or (dl and b[1][1]-b[0][1]<=_MINDIFCON))
                shiftflag=a in ['metal1','metal2','m2contact','polycontact','labels']
                shiftflag=shiftflag or contflag
                if shiftflag:
                    b[1-dr][1]+=f(dr,dl)
                b[dr][1]+=f(dr,dl)
                if a in ['ndcontact','pdcontact'] and contflag and not dl:
                    xy=[b[0][1],b[0][1]-f(dr,dl)]
                    (x,y)=(min(xy),max(xy))
                    flag=True
                    for i in lcont:
                        if (x,y)[1-dr]==i[dr][1] and b[0][0]==i[0][0]:
                            i[dr][1]=(x,y)[dr]
                            flag=False
                    if flag:
                        x=[[b[0][0],min(xy)],[b[1][0],max(xy)]]
                        lcont.append(x)
                        dic[a[0]+'diffusion'].append(x)
            elif (z2n(dr)*(line-b[1-dr][1])<=0):
                b[1-dr][1]+=f(dr,dl)
                b[dr][1]+=f(dr,dl)

def processArgs():
    global NOUPDATE, NOWELL, NOSTRCON, STRETCH, FLIP, INFILE, OUTFILE, ANALYZE, IRSIM, JUSTTHIS, reqinputs
    reqinputs=0
    for a in range(len(sys.argv)):
        b=sys.argv[a]

        if a==0:
            continue
        if a==1 and b in ['-h','-help','h','help']:
            print('Usage: magic.py [OPTIONS] <src> <dest>')
            print('OPTIONS:')
            print('--noupdate\t\tDo not attempt to update script to most current version.')
            print('-flip\t\t\tSwaps the design\'s PMOS/NMOS logic.')
            print('-nowell\t\t\tRemoves all n-wells (-flip will not work if multiple n-wells are present)\n')
            print('-stretch <n/p> <initial size:final size> <p/n> <initial size:final size>')
            print('\t\t\tAtempts to stretch all transistors in the circuit by the given integer ratio.')
            print('\t\t\tRequires user to specify both n and p stretch ratios, even if one of them is 1:1.')
            print('\t\t\tSample usage: ./magic.py -stretch n 10:20 p 2:1 src.mag dest.mag\n')
            print('-nostretchcontact\tOptional argument to be used with the -stretch script.')
            print('\t\t\tKeeps diffusion contacts the same size, and does not stretch them.')
            print('\t\t\tNot really supported; this argument has a high chance of producing errors.\n')
            print('-analyze\t\tRuns analyze.sh on all subdirectories.\n')
            print('\t\t\t-justThis\tOnly runs analyze.sh on the input file.\n')
            print('-irsim\t\t\tPerforms and prints an IRSIM analysis.')
            print('-help\t\t\tPrints this page.')
            sys.exit(0)
        if b=='--noupdate':
            NOUPDATE=True

        if b=='-analyze':
            ANALYZE=True
        if b=='-justThis' and ANALYZE:
            JUSTTHIS=True
            if not reqinputs:
                reqinputs=1

        if b=='-irsim':
            IRSIM=True
            if not reqinputs:
            	reqinputs=1

        if b=='-flip':
            FLIP=True
            reqinputs=2
        if b=='-nowell':
            NOWELL=True

        if b=='-stretch':
            try:
                assert sys.argv[a+1] in ['p','n']
                assert sys.argv[a+3] in ['p','n']
                STRETCH={
                 sys.argv[a+1]:[int(x) for x in sys.argv[a+2].split(':')],
                 sys.argv[a+3]:[int(x) for x in sys.argv[a+4].split(':')]
                }
            except:
                print('Malformed -stretch arguments')
                sys.exit(1)
            reqinputs=2
        if b=='-nostretchcontact':
            NOSTRCON=True

        if reqinputs==2 and a>len(sys.argv)-3:
            tmp=None
            x=2-(len(sys.argv)-a)
            if((os.path.isfile(b) or x)):
                tmp=b
            elif(os.path.isfile(b+'.mag') or x):
                tmp=b+'.mag'
            if(x):
                tmp=b
            if('.' not in b and x):
                tmp=b+'.mag'
            if not tmp:
                print('The last two arguments must be valid file names.')
                sys.exit(1)
            if x:
                OUTFILE=os.path.abspath(tmp)
            else:
                INFILE=os.path.abspath(tmp)
        if reqinputs==1 and a>len(sys.argv)-2:
            tmp=b
            if(not os.path.isfile(tmp)):
                tmp=b+'.mag'
                if(not os.path.isfile(tmp)):
                    print('The last argument must be a valid file name.')
                    sys.exit(1)
            INFILE=os.path.abspath(tmp)

def findHome():
    global HOMEDIR
    # Helper
    getSubdirs=lambda d: [x for x in os.listdir(d) if os.path.isdir(os.path.join(d,x))]
    # Check if a dir is "HOMEDIR"
    def isHome(d):
        # Get all subdirectories
        dirs=getSubdirs(d)
        # Get all subdirectories of subdirectories
        for x in getSubdirs(os.path.join(d,dirs[0])):
            # If one of them is 'magic' or 'sue', we're golden
            if x in ['magic','lvs','sue']:
                return True
        return False

    # Check SCRIPTDIR
    if isHome(SCRIPTDIR):
        HOMEDIR=SCRIPTDIR
        return

    # Check cwd
    if isHome(os.getcwd()):
        HOMEDIR=os.getcwd()
        return

    # Check one folder down from SCRIPTDIR
    for x in getSubdirs(SCRIPTDIR):
        x=os.path.join(SCRIPTDIR,x)
        if isHome(x):
            HOMEDIR=x
            return

    # Check one folder down from cwd
    for x in getSubdirs(os.getcwd()):
        x=os.path.join(os.getcwd(),x)
        if isHome(x):
            HOMEDIR=x
            return

    # Check one folder up from cwd
    x=os.path.abspath(os.path.join(os.getcwd(),'..'))
    if isHome(x):
        HOMEDIR=x
        return

    # Check two folders up from cwd
    x=os.path.abspath(os.path.join(os.getcwd(),'..'))
    if isHome(x):
        HOMEDIR=x
        return

    # Give up
    print('Folder structure not recognized. Scripts that rely on multiple tools will fail.')
    HOMEDIR=os.getcwd()


def update():
    flag=False
    server=None; cliver=None;

    try:
        server=subprocess.Popen(["wget","-qO","-",RAWGITURL+"version.txt"],stdout=subprocess.PIPE).communicate()[0]
    except:
        print("\"Distribution server\" is offline.")
        return
    try:
        with open(os.path.expanduser('~/.teo'),'r') as f:
            cliver=f.read()
    except:
        print("Cannot find local version number.\n")
        cliver=1
    if server and cliver and server!=cliver:
        print("Updating script.\n")
        subprocess.call(["wget",RAWGITURL+"magic.py","-O",os.path.join(SCRIPTDIR,"magic.py")])
        subprocess.call(["chmod","u+x","magic.py"])
        subprocess.call(["wget",RAWGITURL+"analyze.sh","-O",os.path.join(SCRIPTDIR,"analyze.sh")])
        subprocess.call(["chmod","u+x","analyze.sh"])
        subprocess.call(["wget",RAWGITURL+"correct","-O",os.path.join(SCRIPTDIR,"correct")])
        subprocess.call(["wget",RAWGITURL+"version.txt","-O",os.path.expanduser("~/.teo")])
        print("Restarting script.\n")
        os.execl(sys.executable,sys.executable,*sys.argv)
        sys.exit(0)

def readMagic(f,dic):
    global VDD, GND
    with open(f,'r') as f:
        cur=None
        for n,l in enumerate(f):
            l=l.replace('\n','').replace('\r','')
            if n<3:
                if n==0:
                    dic['header']=[]
                if n==2:
                    l='timestamp '+str(TS)
                dic['header'].append(l)
                continue
            if l=='<< end >>':
                break
            if l=='<< nwell >>' and NOWELL:
                cur=None; continue;
            if l[:2]=='<<':
                cur=l[3:-3]
                dic[cur]=[]
            if l[:4]=='rect':
                cord=_intsplit(l[5:])
                if cur:
                    dic[cur].append([cord[:2],cord[2:]])
            if l[:6]=='rlabel':
                cord=_intsplit(l[7:])
                dic[cur].append([[cord[1:3],cord[3:5]],[cord[0],cord[5],cord[6]]])
                if 'vdd' in cord[6].lower():
                    VDD=cord[6]
                if 'gnd' in cord[6].lower():
                    GND=cord[6]
    return dic

def writeMagic(f,dic):
    with open(f,'w') as f:
        head=dic.pop('header')
        lbls=dic.pop('labels')
        for a in head:
            print(a,file=f)
        for a in dic:
            print('<< '+a+' >>',file=f)
            for b in dic[a]:
                print('rect',*_flatlist(b),file=f,sep=' ')
        print('<< labels >>',file=f)
        for a in lbls:
            print('rlabel',a[1][0],*_flatlist(a[0]),file=f,sep=' ',end=' ')
            print(*a[1][1:],file=f,sep=' ')
        print('<< end >>',file=f)
    global INFILE; INFILE=OUTFILE;

def flip():
    dic={}
    readMagic(INFILE,dic)
    dicret={}
    for a in dic:
        if a=='header':
            dicret[a]=dic[a]
            continue
# Assumes single, rectangular, nwell
        if a=='nwell':
            (top,bot)=_topbottom(dic)
            b=dic[a][0]
            tmp=b[0][1]
            b[0][1]=(bot+top)-b[1][1]
            b[1][1]=tmp
        for b in dic[a]:
            if a=='labels':
                if b[1][1] in [1,5]:
                    b[1][1]=6-b[1][1]
                if b[1][2]==VDD:
                    b[1][2]=GND
                elif b[1][2]==GND:
                    b[1][2]=VDD
                b=b[0]
            sys.stdout.flush()
            tmp=b[0][1]
            b[0][1]=-b[1][1]
            b[1][1]=-tmp
            dicret[_npswap(a)]=dic[a]
    writeMagic(OUTFILE,dicret)

def stretch():
    def findLine(a,dr):
        def restrict(x):
            for i in dic['restrictedArea']:
                if z2n(dr)*(x-i[dr][1])<=0 and z2n(dr)*(x-i[1-dr][1])>0:
                    return True
            return False

        ret=a[dr][1]
        while restrict(ret):
            ret-=z2n(dr)

        if z2n(dr)*(ret-a[not dr][1])<0:
            print("Transistor stretching failed. Best attempt returned.")
        return ret

    dic={}
    readMagic(INFILE,dic)
    lcont=[]
    tlens={'n':{},'p':{}}
    for idx,a in enumerate(dic['ntransistor']):
        tlens['n'][idx]=a[1][1]-a[0][1]
    for idx,a in enumerate(dic['ptransistor']):
        tlens['p'][idx]=a[1][1]-a[0][1]
    niter=sorted(tlens['n'].iteritems(),key=lambda (k,v): v)
    piter=sorted(tlens['p'].iteritems(),key=lambda (k,v): v)

    dic['restrictedArea']=[]

    for idx,le in niter:
        dl=STRETCH['n'][1]<STRETCH['n'][0]
        a=dic['ntransistor'][idx]
        while(a[1][1]-a[0][1]!=le*STRETCH['n'][1]/STRETCH['n'][0]):
            line=findLine(a,False)
            _stretch(dic,line,False,dl,lcont)
        dic['restrictedArea'].append(copy.deepcopy(a))
    for idx,le in piter:
        dl=STRETCH['p'][1]<STRETCH['p'][0]
        a=dic['ptransistor'][idx]
        while(a[1][1]-a[0][1]!=le*STRETCH['p'][1]/STRETCH['p'][0]):
            line=findLine(a,True)
            _stretch(dic,line,True,dl,lcont)
        dic['restrictedArea'].append(copy.deepcopy(a))
    del dic['restrictedArea']
    writeMagic(OUTFILE,dic)

def analyze():
    os.chdir(SCRIPTDIR)
    subdirs=[x for x in os.listdir(SCRIPTDIR)
                    if os.path.isdir(os.path.join(SCRIPTDIR,x))]
    if JUSTTHIS:
        if OUTFILE:
            subdirs=[os.path.basename(OUTFILE)]
        elif INFILE:
            subdirs=[os.path.basename(INFILE)]
        else:
            print('This error should be unreachable')
            sys.exit(1)
        if subdirs[0][-4:]=='.mag':
            subdirs[0]=subdirs[0][:-4]
    for x in subdirs:
        if x not in ['output','calibre']:
            subprocess.call([os.path.join(SCRIPTDIR,'analyze.sh'),x])

def irsim():
    # Copy the global INFILE
    inf=INFILE

    # If we get a mag file input
    if inf[-4:]=='.mag':
        # Save cwd
        tmp=os.getcwd()
        # Navigate to the file's folder
        os.chdir(os.path.dirname(inf))
        # Check if there is a .sim file
        if not os.path.isfile(inf[:-4]+'.sim'):
            # Make a .sim file if necessary
            subprocess.call(['ext4mag',inf])
        # Change input to the .sim file
        inf=inf[:-4]+'.sim'
        # Reset everything
        os.chdir(tmp)

    # Get list of inputs/outputs
    inouts=set()
    with open(inf,'r') as f:
        for l in f:
    # Assume that all inputs/outputs will be connected to FETs
            if l[0] in ['p','n']:
                l=_intsplit(l)
                for x in l:
                    if isinstance(x,str):
                    # Weed out virtual nets
                        if x[-1]!='#' and x not in ['p','n']:
                            inouts.add(x)
    # Remove Vdd / GND
    toRemove=[]
    for x in inouts:
        if x.lower() in ['vdd','gnd']:
            toRemove.append(x)
    for x in toRemove:
        inouts.remove(x)

    # Ask the user to distinguish ins from outs
    # We can probably do this automatically, based on the transistors
    # On the to-do list
    print('\nThe .sim file contains the following inputs/outputs:')
    print(*inouts,sep=' ')
    while(True):
        outs=raw_input('Please tell me which of them are actually outputs. Separate with spaces.\n')
        outs=_intsplit(outs)
        for x in outs:
            if x not in inouts:
                print('You had typos. Here is the list again.')
                print(*inouts,sep=' ')
                continue
        break

    # Split off inputs
    ins=[]
    for x in inouts:
        if x not in outs:
            ins.append(x)

    with open('.tmp.cmd','w') as f:
        print('stepsize 50',file=f)
        print('analyzer',*inouts,sep=' ',file=f)
        print('vector','ins',*ins,sep=' ',file=f)
        for x in range(2**len(ins)):
            b=bin(x)[2:]
            b='0'*(len(ins)-len(b))+b
            print('setvector','ins',b,sep=' ',file=f)
            print('s',file=f)
        print('simtime left [simtime begin]',file=f)
        print('simtime right [simtime end]',file=f)
        simfile=os.path.basename(inf[:-4])+'_sim.ps'
        simfile=os.path.join(HOMEDIR,'output',simfile)
        print('print','file',simfile,sep=' ',file=f)
        print('exit',end='',file=f)

    # Call irsim
    subprocess.call(['irsim','/classes/ecen4303F18/scmos30.prm',inf,'-.tmp.cmd'])

    # Clean up .tmp.cmd
    subprocess.call(['rm','.tmp.cmd'])

if __name__ == '__main__':
    processArgs()
    findHome()
    if not NOUPDATE:
        update()
    if FLIP:
        flip()
    if STRETCH:
        stretch()
    if ANALYZE:
        analyze()
    if IRSIM:
        irsim()
