#!/bin/bash

                        
if ip addr show eth0 &> /dev/null; then
    ip addr show eth0 | grep -E 'inet\b' | awk '$2 ~ /^10\.12\./ || $2 ~ /^143\./ || $2 ~ /^10\.189\./ {split($2, a, "/"); print a[1]}'
fi

if ip addr show eth1 &> /dev/null; then
    ip addr show eth1 | grep -E 'inet\b' | awk '$2 ~ /^10\.12\./ || $2 ~ /^143\./ || $2 ~ /^10\.189\./ {split($2, a, "/"); print a[1]}'
fi

if ip addr show eth2 &> /dev/null; then
    ip addr show eth2 | grep -E 'inet\b' | awk '$2 ~ /^10\.12\./ || $2 ~ /^143\./ || $2 ~ /^10\.189\./ {split($2, a, "/"); print a[1]}'
fi

