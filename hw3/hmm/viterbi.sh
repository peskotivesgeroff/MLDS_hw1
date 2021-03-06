#!/bin/bash

if [ $# -ne 2 ]; then
    echo "Usage:viterbi.sh <output name> <weight>"
	echo "ex: viterbi.sh predictions/myoutput.csv 0.9"
	exit 1;
fi

data_dir='../data'
pred_dir=predictions
log_dir=log


THEANO_FLAGS=device=cpu python2 -u viterbi.py --weight $2 \
    $data_dir/3lyr_4096nrn_1188in_prob_fixed $data_dir/hmm.mdl \
    $data_dir/48_39.map $1
