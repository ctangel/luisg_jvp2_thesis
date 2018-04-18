#ifndef IBC
#define IBC

#include <pbc/pbc.h>
#include <openssl/aes.h>

int get_block_size(const unsigned char* m);

void setup(element_t* generator, element_t* secret_key, element_t* public_key);

void extract(unsigned char* id, pairing_t* pairing, element_t* s, 
    element_t* sQid);

void encrypt(const unsigned char* m, element_t* Ppub, 
    pairing_t* pairing, unsigned char* id, unsigned char* output);

void decrypt(unsigned char* enc, unsigned long size, element_t* r, 
    element_t* P, element_t* sQid, pairing_t* pairing, unsigned char* output);
#endif
