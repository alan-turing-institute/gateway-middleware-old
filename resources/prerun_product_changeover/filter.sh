#!/bin/sh

# print every Nth line (keep the first)
awk 'NR == 1 || NR % 30 == 0' raw.csv > output.csv
