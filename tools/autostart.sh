#!/bin/sh

root=$(cd $(dirname $0); pwd)

cat <<EOF > /etc/init.d/climon
#! /bin/sh
### BEGIN INIT INFO
# Provides:          climon
# Required-Start:    \$all
# Required-Stop:     
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: http://github.com/jwustrack/climon
### END INIT INFO

$root/climon \$1
EOF

chmod +x /etc/init.d/climon

update-rc.d climon defaults
