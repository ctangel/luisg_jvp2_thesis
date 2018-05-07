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
  size_t count = fread(param, 1, 1024, stdin);

  if (!count) pbc_die("input error\n");

  // Check Arguments
  if (argc != 3) {
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
  int c;

  int len = strlen(argv[2]);
  size_t final_len = len / 2;
  unsigned char* enc = (unsigned char*)malloc((final_len+1) * sizeof(*enc));
  for (size_t i=0, j=0; j<final_len; i+=2, j++)
      enc[j] = (argv[2][i] % 32 + 9) % 25 * 16 + (argv[2][i+1] % 32 + 9) % 25;
  enc[final_len+1] = '\0';
  // https://gist.github.com/xsleonard/7341172

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
  unsigned char output[final_len];
  if (strcmp(argv[1], id) == 0) {
    decrypt((unsigned char*)enc, final_len, &r, &P, &sQid, &pairing, output);

  } else if (strcmp(argv[1], gid) == 0) {
    decrypt((unsigned char*)enc, final_len, &r, &P, &gQid, &pairing, output);
  } else {
    printf("Incorrect ID Prodvided");
    exit(EXIT_FAILURE);
  }

  printf("%s", (const char*)output);

  free(enc);
  return 0;
}
