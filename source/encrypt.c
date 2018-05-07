/* encrypt.c
 *
 * Encryptes a supplied message
 *
 * Author: Luis Gonzalez-Yante
 *
 */
#include <stdio.h>
#include <string.h>
#include <pbc/pbc.h>
#include "ibc.h"

#define MAX_LENGTH 10000
int main(int argc, char *argv[]) {
  pairing_t pairing;
  char param[1024];
  char str[MAX_LENGTH];
  size_t count = fread(param, 1, 1024, stdin);
  element_t P, Ppub, sQid, r;
  char* target;
  char* m;
  if (!count) pbc_die("input error\n");

  // Initialize a Pairing
  pairing_init_set_buf(pairing, param, count);
  element_init_G2(P, pairing);
  element_init_G2(Ppub, pairing);
  element_init_G1(sQid, pairing);
  element_init_Zr(r, pairing);

   if( argc > 3 ) {
      printf("Too many arguments supplied.\n");
   }
   else if (argc != 3) {
      printf("Two argument expected.\n");
   } else {
     target = argv[2];
     m = argv[1];
   }

  // Read in Public Key
  FILE *fp;
  fp = fopen("ppub.pub", "r");
  while (fgets(str, MAX_LENGTH,fp) != NULL) {
    int h = element_set_str(Ppub, (const char*) str, 10);
  }
  fclose(fp);

  // Encryption Message
  unsigned char enc[(get_block_size((const unsigned char*)m) * 16)+1];
  encrypt((const unsigned char*)m, &Ppub, &pairing, (unsigned char*)target, enc);


  for (int i = 0; i < (get_block_size((const unsigned char*)m) *16); i++) {
    printf("%02x",(int)enc[i]);
  }
  return 0;
}
