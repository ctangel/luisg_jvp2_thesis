/* drone.c
 *
 * Example of how a message sender will function
 *
 * Author: Luis Gonzalez-Yante
 *
 */
#include <stdio.h>
#include <string.h>
#include <pbc/pbc.h>
#include "ibc.h"

#define MAX_LENGTH 10000
int main() {
  pairing_t pairing;
  char param[1024];
  const unsigned char m[] = "luis is here dis bish hello there I do not know how to tell you that you do not have to be the person telling me to be with you";
  char str[MAX_LENGTH];
  char id[MAX_LENGTH];
  size_t count = fread(param, 1, 1024, stdin);
  char* target = "base_A"; 
  element_t P, Ppub, sQid, r;

  if (!count) pbc_die("input error\n");
  
  // Initialize a Pairing
  pairing_init_set_buf(pairing, param, count);
  element_init_G2(P, pairing);
  element_init_G2(Ppub, pairing);
  element_init_G1(sQid, pairing);
  element_init_Zr(r, pairing);

  // Read in Public Key
  FILE *fp;
  fp = fopen("ppub.pub", "r");
  while (fgets(str, MAX_LENGTH,fp) != NULL) {
    int h = element_set_str(Ppub, (const char*) str, 10);
  }
  fclose(fp);

  // Encryption Message
  unsigned char enc[(get_block_size(m) * 16)+1]; 
  encrypt(m, &Ppub, &pairing, (unsigned char*)target, enc);
  
  // Write Encrypted Message to File
  FILE * fpp;
  fpp = fopen("enc.pub","wb");
  fwrite(enc, ((get_block_size(m) * 16)+1),1,fpp);
  fclose(fpp);

  return 0;
}
