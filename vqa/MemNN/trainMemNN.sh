#!/bin/bash

mlp_units=$1 #ex. 1024
mlp_layers=$2 #ex. 3
activation='relu'
epochs=50
memory_dim=100
batch_size=128
hops=$3 #ex. 1
lr=0.0002
dropout=0.3

log_path=$(printf 'accuracy/memNN.mlp_%s_%s.hops_%s.memdim_%i.lr_2e-4.relu.dropout_%f.log' "$mlp_layers" "$mlp_units" "$hops" "$memory_dim" "$dropout")
#echo $log

python src/trainMemNN.py \
    --mlp-hidden-units $mlp_units \
    --mlp-hidden-layers $mlp_layers \
    --mlp-activation $activation \
    --emb-dimension $memory_dim \
    --num-epochs $epochs \
    --batch-size $batch_size \
    --hops $hops \
    --learning-rate $lr \
    --dropout $dropout \
    --dev-accuracy-path $log_path
