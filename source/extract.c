/* extract.c
 *
 * Generates privater user key
 *
 * Author: Luis Gonzalez-Yante
 *
 */
#include <stdio.h>
#include <string.h>
#include <pbc/pbc.h>
#include "ibc.h"

#define MAX_LENGTH 10000
//./ibe luisg@princeton.edu < ../other/pbc-0.5.14/param/a.param

int main(int argc, char *argv[]) {
  if( argc != 2 && argc > 2 ) {
      printf("Too many arguments supplied.\n");
   }
   else if (argc != 2) {
      printf("One argument expected.\n");
   }

  pairing_t pairing;
  char param[1024];
  size_t count = fread(param, 1, 1024, stdin);
  char *id = argv[1];
  char str[MAX_LENGTH];
  if (!count) pbc_die("input error\n");

  // Initialize a Pairing
  pairing_init_set_buf(pairing, param, count);

  element_t P, Ppub, s, sQid;

  element_init_G2(P, pairing);
  element_init_G2(Ppub, pairing);
  element_init_Zr(s, pairing);
  element_init_G1(sQid, pairing);

  // Read in Paring Information
  FILE *fp;
  fp = fopen("../system/s.pub", "r");
  while (fgets(str, MAX_LENGTH,fp) != NULL) {
    int h = element_set_str(s, (const char*) str, 10);
  }
  fclose(fp);

  // Extract
  extract((unsigned char*)id, &pairing, &s, &sQid);

  // Write information to files
  fp = fopen("id.pub","w");
  fprintf(fp, "%s", id);
  fclose(fp);
  fp = fopen("sqid.pub","w");
  element_out_str(fp, 10, sQid);
  fclose(fp);
  return 0;
}
