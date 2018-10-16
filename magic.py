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
NOWELL=None
NOSTRCON=None
TS=str(int(time.time()))+'.451' #personal flair

VDD=None
GND=None

_MINDIFCON=10

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
    global NOUPDATE, NOWELL, NOSTRCON, STRETCH, FLIP, INFILE, OUTFILE
    for a in range(len(sys.argv)):
        b=sys.argv[a]
        if a==0:
            continue
        if a==1 and b in ['-h','-help','h','help']:
            print('Usage: magic.py [OPTIONS] <src> <dest>')
            print('OPTIONS:')
            print('--noupdate\t\tDo not attempt to update script before running.')
            print('-flip\t\t\tSwap the design\'s PMOS/NMOS logic.')
            print('-nowell\t\t\tRemove n-well (the n-well may otherwise cause errors)\n')
            print('-stretch <n/p> <initial size:final size> <p/n> <initial size:final size>')
            print('\t\t\tAtempts to stretch all transistors in the circuit by the given integer ratio.')
            print('\t\t\tRequires user to specify both n and p stretch ratios, even if one of them is 1:1.')
            print('\t\t\tMay not work as desired.\n')
            print('-nostretchcontact\tOptional argument to be used with the -stretch script.')
            print('\t\t\tKeeps diffusion contacts the same size, and does not stretch them.')
            print('-help\t\t\tPrints this page.')
        if a>len(sys.argv)-3:
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
            if x:
                OUTFILE=tmp
            else:
                INFILE=tmp
        if b=='--noupdate':
            NOUPDATE=True
        if b=='-flip':
            FLIP=True
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
        if b=='-nostretchcontact':
            NOSTRCON=True

def update():
    flag=False
    server=None; cliver=None;

    try:
        server=subprocess.check_output(["wget","-qO","-",RAWGITURL+"version.txt"])
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
        subprocess.call(["wget",RAWGITURL+"magic.py","-O",os.path.realpath(sys.argv[0])])
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
                
if __name__ == '__main__':
    processArgs()
    if not NOUPDATE:
        update()
    if FLIP:
        flip()
    if STRETCH:
        stretch()
