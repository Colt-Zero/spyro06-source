.open "sys/main.dol"
 ; Charging turning speed, credit goes to Colt Zero(Olivine Ellva)
 .org 0x800dc53c
   bl set_charge_turn_speed
 ; Invincibility, credit goes to Colt Zero(Olivine Ellva)
 ;.org 0x800aa4c0
 ;  nop
.close