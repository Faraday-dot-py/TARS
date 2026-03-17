MEMORY
{
  rom (rx)  : ORIGIN = 0x08007000, LENGTH = 512K - 28K
  ram (rwx) : ORIGIN = 0x20000000, LENGTH = 64K
}

_estack = ORIGIN(ram) + LENGTH(ram);

SECTIONS
{
  .isr_vector :
  {
    KEEP(*(.isr_vector))
  } > rom

  .text :
  {
    *(.text*)
    *(.rodata*)
    . = ALIGN(4);
    _etext = .;
  } > rom

  _sidata = _etext;

  .data : AT (_sidata)
  {
    . = ALIGN(4);
    _sdata = .;
    *(.data*)
    . = ALIGN(4);
    _edata = .;
  } > ram

  .bss :
  {
    . = ALIGN(4);
    _sbss = .;
    *(.bss*)
    *(COMMON)
    . = ALIGN(4);
    _ebss = .;
  } > ram
}
