#!/bin/sh
# Run inside the certificate container after issue/renew. Only Nginx's group
# gains read access; the private key is never world-readable.
set -eu
chgrp -R 101 /etc/letsencrypt
find /etc/letsencrypt -type d -exec chmod g+rx {} \;
find /etc/letsencrypt/archive -type f -name '*.pem' -exec chmod g+r {} \;
