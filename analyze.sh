#!/usr/bin/env bash
cd $1

cd magic
echo "no" | ext4mag $1.mag
cd ../sue
echo "set NETLIST(no_header) 1" > .suerc
sue $1.sue -CMD netlist -CMD exit -ICONIFY 1
cd ../calibre
printf "*calibreRulesFile: /classes/ecen4303F18/calibre/calibreLVS_scn3me_subm.rul\n">runset.calibre.calibre
printf "*calibreRunDir: .\n">>runset.calibre.calibre
printf "*calibreLayoutPaths: ../magic/%s.gds\n" $1>>runset.calibre.calibre
printf "*calibreLayoutPrimary: %s\n" $1>>runset.calibre.calibre
printf "*calibreSourcePath: ../sue/%s.sp\n" $1>>runset.calibre.calibre
printf "*calibreSourcePrimary: %s\n" $1>>runset.calibre.calibre
printf "*calibreSourceSystem: SPICE\n">>runset.calibre.calibre
printf "*calibreSpiceFile: extracted.sp\n">>runset.calibre.calibre
printf "*calibrePowerNames: vdd\n">>runset.calibre.calibre
printf "*calibreGroundNames: gnd\n">>runset.calibre.calibre
printf "*calibreIgnorePorts: 1\n">>runset.calibre.calibre
printf "*calibreERCDatabase: %s.erc.db\n" $1>>runset.calibre.calibre
printf "*calibreERCSummaryFile: %s.erc.summary\n" $1>>runset.calibre.calibre
printf "*calibreReportFile: %s.lvs.report\n" $1>>runset.calibre.calibre
printf "*calibreMaskDBFile: %s.maskdb\n" $1>>runset.calibre.calibre
printf "*cmnShowOptions: 1\n">>runset.calibre.calibre
printf "*Cmnvconnectnames: VDD GND\n">>runset.calibre.calibre
printf "*cmnVConnectNamesState: ALL\n">>runset.calibre.calibre
printf "*cmnFDILayerMapFile: /classes/ecen4303F18/calibre/layer.map\n">>runset.calibre.calibre
printf "*cmnFDIUseLayerMap: 1">>runset.calibre.calibre
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
