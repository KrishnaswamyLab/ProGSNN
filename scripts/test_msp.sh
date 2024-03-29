#!/bin/bash

#SBATCH --job-name=test_msp
#SBATCH --time=20:00:00
#SBATCH --cpus-per-task=8
#SBATCH --partition=pi_krishnaswamy
#SBATCH --gpus=1
#SBATCH --mem=128G
#SBATCH --output=./logs/slurm/%x_%j.out
#SBATCH --error=./logs/slurm/%x_%j.err
cd ~/project/ProGSNN-2
module load miniconda
conda activate mfcn

python test_progsnn_msp.py