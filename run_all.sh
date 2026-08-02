#!/bin/bash
source venv/bin/activate

(cd sensor_temperature && python3 main.py) &
PID1=$!
(cd vb02_python_sdk && python3 main.py) &
PID2=$!

trap "kill $PID1 $PID2" SIGINT SIGTERM
wait $PID1 $PID2
