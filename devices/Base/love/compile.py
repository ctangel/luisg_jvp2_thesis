import os

os.system("gcc encrypt.c ibc.c -o encrypt -lpbc -lgmp -lcrypto")
os.system("gcc decrypt.c ibc.c -o decrypt -lpbc -lgmp -lcrypto")
