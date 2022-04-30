#!/usr/bin/env bash

echo "Re-indexing Wallabag database."
echo -n "Starting at: "
date
echo
sudo -u manticore indexer -c /etc/manticoresearch/manticore.conf --all --rotate

echo
echo -n "Finished at: "
date
echo "Done."
exit 0

