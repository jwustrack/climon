#!/bin/sh

cat <<EOF | sqlite3 $1
DROP TABLE climon_stats;
DELETE FROM climon WHERE humidity > 100 or humidity < 0;
EOF
