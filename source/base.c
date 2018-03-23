/* base.c
 *
 * Example of how the message receiver will operate
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
  char str[MAX_LENGTH];
  char id[MAX_LENGTH];
  char temp[MAX_LENGTH];
  char *enc;
  size_t count = fread(param, 1, 1024, stdin);

  if (!count) pbc_die("input error\n");
  
  // Initialize a Pairing
  pairing_init_set_buf(pairing, param, count);

  element_t P, Ppub, sQid, r;
  
  element_init_G2(P, pairing);
  element_init_G2(Ppub, pairing);
  element_init_G1(sQid, pairing);
  element_init_Zr(r, pairing);

  // Read in Paring Information
  FILE *fp;
  fp = fopen("enc.pub", "rb");
  int c;
  int n = 0;
  do {
    c = fgetc(fp);
    if (feof(fp)) {
      break;
    }
    str[n] = (char)c;
    n++;
  } while(1);
  str[n] = '\0';
  fclose(fp);
  enc = (char*) malloc(sizeof(char) * (n));
  for (int i = 0; i < n; i++) {
    enc[i] = str[i];
  }
  enc[n] = '\0';
  
  fp = fopen("id.pub", "r");
  while (fgets(str, MAX_LENGTH,fp) != NULL) {
    strcpy(id, str); 
  }
  fclose(fp);
  fp = fopen("p.pub", "r");
  while (fgets(str, MAX_LENGTH,fp) != NULL) {
    int h = element_set_str(P, (const char*) str, 10);
  }
  fclose(fp);
  fp = fopen("ppub.pub", "r");
  while (fgets(str, MAX_LENGTH,fp) != NULL) {
    int h = element_set_str(Ppub, (const char*) str, 10);
  }
  fclose(fp);
  fp = fopen("sqid.pub", "r");
  while (fgets(str, MAX_LENGTH,fp) != NULL) {
    int h = element_set_str(sQid, (const char*) str, 10);
  }
  fclose(fp);
  
  // Decryption of messages
  unsigned char output[n];
  decrypt((unsigned char*)enc, n, &r, &P, &sQid, &pairing, output);
   
  printf("luis: %s   %lu\n", output, strlen((const char*)output));
  
  free(enc);
  return 0;
}
