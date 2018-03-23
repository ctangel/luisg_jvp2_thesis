/* setup.c
 *
 * Created public and secret key. Should only be ran once
 *
 * Author: Luis Gonzalez-Yante
 *
 */
#include <stdio.h>
#include <string.h>
#include <pbc/pbc.h>
#include "ibc.h"

//./ibe luisg@princeton.edu < ../other/pbc-0.5.14/param/a.param

int main(int argc, char *argv[]) {
  pairing_t pairing;
  char param[1024];
  size_t count = fread(param, 1, 1024, stdin);
  if (!count) pbc_die("input error\n");

  // Initialize a Pairing
  pairing_init_set_buf(pairing, param, count);

  element_t P, Ppub, s;

  element_init_G2(P, pairing);
  element_init_G2(Ppub, pairing);
  element_init_Zr(s, pairing);

  // Setup
  setup(&P, &s, &Ppub);

  // Write information to files
  FILE * fp;
  fp = fopen("../system/s.pub","w");
  element_out_str(fp, 10, s);
  fclose(fp);
  fp = fopen("../system/p.pub","w");
  unsigned char p[element_length_in_bytes(P)];
  element_out_str(fp, 10, P);
  fclose(fp);
  fp = fopen("../system/ppub.pub","w");
  element_out_str(fp, 10, Ppub);
  fclose(fp);

  return 0;
}
