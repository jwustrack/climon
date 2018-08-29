#!/bin/sh

cat <<EOF | sqlite3 $1
DROP TABLE climon_stats;
DELETE FROM climon WHERE metric = 1 AND (value > 100 OR value < 0);
EOF
