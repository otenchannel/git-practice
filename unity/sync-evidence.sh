#!/bin/sh
# data/evidence.csv を Unity の StreamingAssets にコピーする
cd "$(dirname "$0")" && cp ../data/evidence.csv KuzuhaDaiba/Assets/StreamingAssets/evidence.csv && echo synced
