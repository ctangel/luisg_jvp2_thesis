#include "ibc.h"
#include <stdio.h>
#include <string.h>
#include <pbc/pbc.h>

int main() {
  pairing_t pairing;
  char param[1024];
  const unsigned char m[] = "encrypt dis bish";
  unsigned char id[] = "base_A";
  //unsigned char id[] = "luisg@princeton.edu";
  unsigned char fid[] = "fnewaj@princeton.edu";
  unsigned char jid[] = "jvp2@princeton.edu";
  size_t count = fread(param, 1, 1024, stdin);

  AES_KEY enc_key, dec_key;

  if (!count) pbc_die("input error\n");
  
  // Initialize a Pairing
  pairing_init_set_buf(pairing, param, count);

  element_t P, Ppub, s;
  element_t sQid;
  element_t r;
  element_t rP;
  
  element_init_G2(P, pairing);
  element_init_G2(Ppub, pairing);
  element_init_G2(rP, pairing); 
  element_init_Zr(s, pairing);
  element_init_G1(sQid, pairing);
  element_init_Zr(r, pairing);

  element_t ssQid;
  element_t sssQid;
  element_init_G1(ssQid, pairing);
  element_init_G1(sssQid, pairing);
 
  // Setup
  // Gen prime q, G1, G2 and choose Random Generator P 
  setup(&P, &s, &Ppub); 

  // Extract
  // Pick a random s (pk) and set Ppub = sP
  extract(id, &pairing, &sQid, &s);
  extract(jid, &pairing, &sssQid, &s);
  extract(fid, &pairing, &ssQid, &s);
  
  // Encryption
  unsigned char enc[(get_size(m) * 16)+1]; 
  encrypt(m, &r, &Ppub, &pairing, id, enc);

  // Decryption
  unsigned char output[(sizeof(enc))];
  unsigned char output1[(sizeof(enc))];
  unsigned char op[(sizeof(enc))];
  //printf("hhh: %lu\n", sizeof(enc));
  decrypt((unsigned char*)enc, sizeof(enc), &r, &P, &ssQid, &pairing, output1);
  decrypt((unsigned char*)enc, sizeof(enc), &r, &P, &sssQid, &pairing, op);
  decrypt((unsigned char*)enc, sizeof(enc), &r, &P, &sQid, &pairing, output);
   
  printf("\n  m: %s   %lu\n", m, strlen((const char*)m));
  //printf("enc: %s\n", mm);
  printf(" fida: %s   %lu\n", output1, strlen((const char*)output1));
  printf(" luis: %s   %lu\n", output, strlen((const char*)output));
  printf("james: %s   %lu\n", op, strlen((const char*)op));

  return 0;
}
