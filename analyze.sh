#!/usr/bin/env bash
cd $1

cd magic
echo "no" | ext4mag inv.mag
cd ../sue
echo "set NETLIST(no_header) 1" > .suerc
sue $1.sue -CMD netlist -CMD exit -ICONIFY 1
cd ../lvs
printf "*lvsRulesFile: /classes/ecen4303F18/calibre/calibreLVS_scn3me_subm.rul\n">runset.calibre.lvs
printf "*lvsRunDir: .\n">>runset.calibre.lvs
printf "*lvsLayoutPaths: ../magic/%s.gds\n" $1>>runset.calibre.lvs
printf "*lvsLayoutPrimary: %s\n" $1>>runset.calibre.lvs
printf "*lvsSourcePath: ../sue/%s.sp\n" $1>>runset.calibre.lvs
printf "*lvsSourcePrimary: %s\n" $1>>runset.calibre.lvs
printf "*lvsSourceSystem: SPICE\n">>runset.calibre.lvs
printf "*lvsSpiceFile: extracted.sp\n">>runset.calibre.lvs
printf "*lvsPowerNames: vdd\n">>runset.calibre.lvs
printf "*lvsGroundNames: gnd\n">>runset.calibre.lvs
printf "*lvsIgnorePorts: 1\n">>runset.calibre.lvs
printf "*lvsERCDatabase: %s.erc.db\n" $1>>runset.calibre.lvs
printf "*lvsERCSummaryFile: %s.erc.summary\n" $1>>runset.calibre.lvs
printf "*lvsReportFile: %s.lvs.report\n" $1>>runset.calibre.lvs
printf "*lvsMaskDBFile: %s.maskdb\n" $1>>runset.calibre.lvs
printf "*cmnShowOptions: 1\n">>runset.calibre.lvs
printf "*Cmnvconnectnames: VDD GND\n">>runset.calibre.lvs
printf "*cmnVConnectNamesState: ALL\n">>runset.calibre.lvs
printf "*cmnFDILayerMapFile: /classes/ecen4303F18/calibre/layer.map\n">>runset.calibre.lvs
printf "*cmnFDIUseLayerMap: 1">>runset.calibre.lvs
./run_calibre.sh

cd ..
if grep -Fxq -f ../correct ./lvs/$1.lvs.report
then printf "\nSimulation results CORRECT!\n"
else
	printf "\nERROR in LVS!\n"
	exit 0
fi

if [ ! -d "../output" ]
then mkdir ../output
fi

cd ../output
cp ../$1/lvs/$1.lvs.report .
echo "y" | pplot -k $1.ps -l allText -d 10 ../$1/magic/$1.cif
printf "\n"
