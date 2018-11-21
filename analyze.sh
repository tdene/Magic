#!/usr/bin/env bash
cd $1

cd magic
echo "no" | ext4mag $1.mag
cd ../sue
echo "set NETLIST(no_header) 1" > .suerc
sue $1.sue -CMD netlist -CMD exit -ICONIFY 1
cd ../calibre
printf "*calibreRulesFile: /classes/ecen4303F18/calibre/calibreLVS_scn3me_subm.rul\n">runset.calibre.lvs
printf "*calibreRunDir: .\n">>runset.calibre.lvs
printf "*calibreLayoutPaths: ../magic/%s.gds\n" $1>>runset.calibre.lvs
printf "*calibreLayoutPrimary: %s\n" $1>>runset.calibre.lvs
printf "*calibreSourcePath: ../sue/%s.sp\n" $1>>runset.calibre.lvs
printf "*calibreSourcePrimary: %s\n" $1>>runset.calibre.lvs
printf "*calibreSourceSystem: SPICE\n">>runset.calibre.lvs
printf "*calibreSpiceFile: extracted.sp\n">>runset.calibre.lvs
printf "*calibrePowerNames: vdd\n">>runset.calibre.lvs
printf "*calibreGroundNames: gnd\n">>runset.calibre.lvs
printf "*calibreIgnorePorts: 1\n">>runset.calibre.lvs
printf "*calibreERCDatabase: %s.erc.db\n" $1>>runset.calibre.lvs
printf "*calibreERCSummaryFile: %s.erc.summary\n" $1>>runset.calibre.lvs
printf "*calibreReportFile: %s.lvs.report\n" $1>>runset.calibre.lvs
printf "*calibreMaskDBFile: %s.maskdb\n" $1>>runset.calibre.lvs
printf "*cmnShowOptions: 1\n">>runset.calibre.lvs
printf "*Cmnvconnectnames: VDD GND\n">>runset.calibre.lvs
printf "*cmnVConnectNamesState: ALL\n">>runset.calibre.lvs
printf "*cmnFDILayerMapFile: /classes/ecen4303F18/calibre/layer.map\n">>runset.calibre.lvs
printf "*cmnFDIUseLayerMap: 1">>runset.calibre.lvs
./run_calibre.sh

cd ..
if [ -e ./calibre/$1.lvs.report ] && !(grep -Fq INCORRECT ./calibre/$1.lvs.report)
then printf "\nSimulation results CORRECT!\n"
else
    printf "\nERROR in LVS!\n"
    exit 0
fi

if [ ! -d "../output" ]
then mkdir ../output
fi

cd ../output
cp ../$1/calibre/$1.lvs.report .
echo "y" | pplot -k $1.ps -l allText -d 10 ../$1/magic/$1.cif
printf "\n"
