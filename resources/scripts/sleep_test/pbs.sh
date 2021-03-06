#!/bin/sh

#PBS -l select=1:ncpus=1:mem=100MB
#PBS -l walltime=00:08:00

#PBS -m be
#PBS -M l.mason@imperial.ac.uk

echo "\$PBS_JOBID = $PBS_JOBID"
echo "\$TMPDIR = $TMPDIR"
echo "\$PBS_O_WORKDIR = $PBS_O_WORKDIR"
echo "\$WORK = $WORK"

for i in {1..20}; do
  date >> $TMPDIR/tmpdir_file.txt
  date >> $PBS_O_WORKDIR/pbs_o_workdir_file.txt
  date >> $WORK/work_file.txt
  sleep 20
done

#pbsdsh2 cp -rf $TMPDIR/\* $WORK/
