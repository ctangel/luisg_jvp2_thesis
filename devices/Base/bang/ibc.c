/* ibc.c
 *
 * Implementation of Identity Based Cryptography as defined by Boneh and
 * Franklin. 
 *
 * Author: Luis Gonzalez-Yante
 *
 */
#include "ibc.h"
#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <pbc/pbc.h>
#include <openssl/sha.h>
#include <openssl/md5.h>
#include <openssl/aes.h>

/* * * Helper Functions * * */

/*  Converts an string ID, such as a MAC address, into hash and computes a
 *  related point on an Elliptical Curve. Stores this piont in Qid
 * */
void id_to_hash(unsigned char* id, element_t Qid) {
  int DIGEST_LENGTH = 32;
  unsigned char digest[DIGEST_LENGTH];
  memset(digest, '\0', DIGEST_LENGTH);
  MD5(id, strlen((const char*)id), digest);
  element_from_hash(Qid, digest, strlen((const char*)digest));
}


/*  Returns the number of blocks needed to encapsulate message m
 */
int get_block_size(const unsigned char* m) {
  int l = strlen((const char*)m);
  int blocks = (l / 16);
  if ((l % 16) != 0) {
    blocks = (l / 16) + 1;
  }
  return blocks;
}

/*  Copies string "to" up to the NULL character or nth characters into the
 *  string "from". if NULL is hit before the nth character, all characters
 *  between NULL and nth will be filled with a NULL character
 */
void cpy(unsigned char* to, unsigned char* from, int n) {
  int i = 0;
  while (i < n) {
    if (from[i] != '\0') {
      to[i] = from[i];
      i++;
    } else {
      break;
    }
  }
  for (int j = i; j < n; j++) {
    to[j] = '\0';
  }
}

/* Copies string "to" up to the the nth character
 */
void cpyall(unsigned char* to, unsigned char* from, int length) {
  int i = 0;
  while (i < length) {
      to[i] = from[i];
      i++;
  }
}

/* * * Main Functions * * */

/* Generates a Generator, a Master Secret Key, and a Master Public Key
 */
void setup(element_t* generator, element_t* secret_key, element_t* public_key) {
  element_random(*generator);
  element_random(*secret_key);
  element_pow_zn(*public_key, *generator, *secret_key);
}

/* Generators the private user key, sQid, of the given id
 */
void extract(unsigned char* id, pairing_t* pairing, element_t* s, element_t* sQid) {
  element_t Qid;
  element_init_G1(Qid, *pairing);
  id_to_hash(id, Qid);
  element_pow_zn(*sQid, Qid, *s);
}

/* Encrypts message m so that only user with the ID id can decrypt.
 */
void encrypt(const unsigned char* m, element_t* public_key, pairing_t* pairing, 
    unsigned char* id, unsigned char* output) {
  element_t Qid, user_public_key;
  element_init_G1(Qid, *pairing);
  element_init_GT(user_public_key, *pairing);
  unsigned char hash[SHA_DIGEST_LENGTH];
  id_to_hash(id, Qid);
  pairing_apply(user_public_key, Qid, *public_key, *pairing);
  unsigned long key_length = element_length_in_bytes(user_public_key);
  unsigned char upk_string[key_length];
  element_to_bytes(upk_string, user_public_key);
  SHA1(upk_string, key_length, hash);

  AES_KEY enc_key;
  AES_set_encrypt_key(hash, 128, &enc_key);
  int blocks = get_block_size(m);
  for (int i = 0; i < blocks; i++) {
    unsigned char from_message[17];
    unsigned char from_encryptor[17];
    cpy(from_message, (unsigned char*)m+(i*16), 16); 
    from_message[16] = '\0';
    AES_encrypt(from_message, from_encryptor, &enc_key);
    from_encryptor[16] = '\0';
    cpyall(output+(i*16), from_encryptor, 16);
  }
}

/*  Decrypts message enc using the private user key
 */
void decrypt(unsigned char* enc, unsigned long size, element_t* r, 
    element_t* P, element_t* sQid, pairing_t* pairing, unsigned char* output) {
  element_t rP, shaHashDec;
  element_init_G1(rP, *pairing);
  element_init_GT(shaHashDec, *pairing);
  unsigned char hashDec[SHA_DIGEST_LENGTH];
  AES_KEY dec_key;
  pairing_apply(shaHashDec, *sQid, *P, *pairing);
  unsigned long ele_length1 = element_length_in_bytes(shaHashDec);
  unsigned char temp4[ele_length1];
  element_to_bytes(temp4, shaHashDec);
  SHA1(temp4, ele_length1, hashDec);
  AES_set_decrypt_key(hashDec, 128, &dec_key); 
  int blocks = size / 16;
  for (int i = 0; i < blocks; i++) {
    unsigned char from_enc[17];
    unsigned char from_decryptor[17];
    cpyall(from_enc, enc+(i*16), 16); 
    from_enc[16] = '\0';
    AES_decrypt(from_enc, from_decryptor, &dec_key);
    from_decryptor[16] = '\0';
    cpyall(output+(i*16), from_decryptor, 16);
  }
  output[blocks*16] = '\0';
}
