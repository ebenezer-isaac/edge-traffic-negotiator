#!/bin/bash
pkill -f "models[.]builder" 2>/dev/null
pkill -f "tmp/ac[a-z0-9]*[.]sh" 2>/dev/null
pkill -f "tmp/w[0-9]*[.]sh" 2>/dev/null
sleep 2
cp "$HOME/all_compiles.sh" /tmp/compile_run.sh
setsid nohup bash /tmp/compile_run.sh > /tmp/compile_run.log 2>&1 < /dev/null &
sleep 5
echo "--- survivors (should be only compile_run) ---"
pgrep -af "compile_run[.]sh"
echo "--- log ---"
cat /tmp/compile_run.log
