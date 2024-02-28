#!/bin/bash

#SBATCH --job-name=progsnn_msp
#SBATCH --time=20:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --output=./logs/slurm/%x_%j.out
#SBATCH --error=./logs/slurm/%x_%j.err
cd ~/project/ProGSNN-1
module load miniconda
conda activate grassy

python train_progsnn_msp.py