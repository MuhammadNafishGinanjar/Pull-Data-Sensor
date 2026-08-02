#!/bin/bash
source venv/bin/activate

python3 main.py &
PID1=$!
python3 machine_status.py &
PID2=$!

trap "kill $PID1 $PID2" SIGINT SIGTERM
wait $PID1 $PID2
