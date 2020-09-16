.open "sys/main.dol"
 ; Free cam, credit goes to marius851000
 .org 0x8034fde4
   li r3, 1 ; 0434fde4 38600001
   blr      ; 0434fde8 4e800020
 .org 0x803249b0
   nop      ; 043249b0 60000000
.close