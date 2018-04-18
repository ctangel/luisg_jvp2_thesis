import os

os.system("gcc run/encrypt.c run/ibc.c -o run/encrypt -lpbc -lgmp -lcrypto")
os.system("gcc run/decrypt.c run/ibc.c -o run/decrypt -lpbc -lgmp -lcrypto")
