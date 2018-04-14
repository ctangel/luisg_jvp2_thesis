/* decrypt.c
 *
 * Decrypt provided encrypted message
 *
 * Author: Luis Gonzalez-Yante
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pbc/pbc.h>
#include "ibc.h"

#define MAX_LENGTH 10000
int main(int argc, char* argv[]) {
  pairing_t pairing;
  char param[1024];
  char str[MAX_LENGTH];
  char id[MAX_LENGTH];  // device id
  char gid[MAX_LENGTH]; // global id
  char temp[MAX_LENGTH];
  char *enc;
  size_t count = fread(param, 1, 1024, stdin);

  if (!count) pbc_die("input error\n");

  // Check Arguments
  if (argc != 2) {
    printf("Argument not provided");
    exit(EXIT_FAILURE);
  }
  // Initialize a Pairing
  pairing_init_set_buf(pairing, param, count);

  element_t P, Ppub, sQid, r, gQid;

  element_init_G2(P, pairing);
  element_init_G2(Ppub, pairing);
  element_init_G1(sQid, pairing);
  element_init_G1(gQid, pairing);
  element_init_Zr(r, pairing);

  // Read in Paring Information
  FILE *fp;
  fp = fopen("denc.pub", "rb");
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
  fp = fopen("global.pub", "r");
  while (fgets(str, MAX_LENGTH,fp) != NULL) {
    strcpy(gid, str);
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
  fp = fopen("gqid.pub", "r");
  while (fgets(str, MAX_LENGTH,fp) != NULL) {
    int h = element_set_str(gQid, (const char*) str, 10);
  }
  fclose(fp);
  
  // Decryption of messages
  unsigned char output[n];
  if (strcmp(argv[1], id) == 0) {
    decrypt((unsigned char*)enc, n, &r, &P, &sQid, &pairing, output);
   
  } else if (strcmp(argv[1], gid) == 0) {
    decrypt((unsigned char*)enc, n, &r, &P, &gQid, &pairing, output);
  } else {
    printf("Incorrect ID Prodvided");
    exit(EXIT_FAILURE);
  } 

  fp = fopen("dec.pub", "wb");
  fwrite(output, strlen((const char*)output), 1, fp);
  fclose(fp);
  
  free(enc);
  return 0;
}
