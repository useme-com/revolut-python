#!/bin/sh
PRVKEY=prvkey.pem
PUBKEY=pubkey.pem
openssl genrsa -out $PRVKEY 1024 && \
openssl req -new -x509 -key $PRVKEY -out $PUBKEY -days 1825 && \
echo -e "\n\nPrivate key file: $PRVKEY" && \
echo " Public key file: $PUBKEY" && \
echo -e "\n\nPaste the following code into 'X509 public key' field within Revolut API settings:" && \
cat $PUBKEY
