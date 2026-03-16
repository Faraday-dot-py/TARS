# Preparing a microSD Card for Ender Board Firmware Flashing

This tutorial is for the case where Windows only offers `exFAT` and `NTFS` when formatting the card, but the board firmware update path expects `FAT32`.

## Why this happens

Windows often refuses to offer `FAT32` in the normal format dialog for larger SD cards.
That is a Windows tooling limitation, not proof that the card cannot be used.

For many Creality-style board update paths, the practical workaround is:

- use a small `FAT32` partition on the card
- put only the firmware file on that partition
- boot the board with that card inserted

## Safety warning

The steps below can erase the SD card.
Double-check the selected disk number before running any command.
If the card contains anything important, back it up first.

## Recommended approach

Use a small `FAT32` partition, ideally 1 GB to 4 GB, dedicated to firmware flashing.
That avoids the Windows large-card `FAT32` limitation while still giving the bootloader a compatible filesystem.

## Option 1: Use Windows Disk Management if FAT32 appears

1. Insert the microSD card.
2. Open `Disk Management`.
3. Find the removable card carefully by size.
4. Delete existing volumes on that card only if you are sure it is the correct device.
5. Create a new simple volume.
6. If `FAT32` is available, choose it.
7. Make the volume small if needed, such as 1024 MB to 4096 MB.
8. Assign a drive letter.
9. Copy only the firmware file onto the card.

If `FAT32` is not available there either, use Option 2.

## Option 2: Use `diskpart` to create a small FAT32 partition

Open an elevated Windows PowerShell or Command Prompt and run:

```text
 diskpart
```

Then run these commands carefully:

```text
list disk
select disk <SD_CARD_NUMBER>
clean
create partition primary size=2048
format fs=fat32 quick
assign
exit
```

What these do:

- `list disk`: shows disks so you can identify the SD card by size
- `select disk <SD_CARD_NUMBER>`: selects the SD card
- `clean`: erases the partition table on that disk
- `create partition primary size=2048`: creates a 2 GB partition
- `format fs=fat32 quick`: formats that partition as FAT32
- `assign`: gives it a drive letter

A 2 GB partition is usually enough for firmware flashing.
If you want a different size, change `2048` to another value in MB.

## Copying the firmware file

After the card is formatted and mounted with a drive letter:

1. Copy the generated firmware binary to the card.
2. Rename it exactly to the name expected by the bootloader.

For the current project notes, use:

```text
firmware.bin
```

Only put that file on the card for the first test if possible.

## Current firmware build output

From the current repo work, the intended output path is:

```text
/home/faraday/TARS/firmware/ender_v4_2_2/build/tars_led_test.bin
```

If copying from WSL to a mounted Windows card, the pattern is:

```bash
cp /home/faraday/TARS/firmware/ender_v4_2_2/build/tars_led_test.bin /mnt/<drive>/firmware.bin && sync
```

Replace `<drive>` with the actual mounted drive letter, for example `e`.

Example:

```bash
cp /home/faraday/TARS/firmware/ender_v4_2_2/build/tars_led_test.bin /mnt/e/firmware.bin && sync
```

## Flash attempt procedure

1. Power the board off.
2. Insert the microSD card.
3. Power the board on.
4. Wait 10 to 30 seconds.
5. Power off again.
6. Remove the card and inspect it on the computer.

## How to tell whether the bootloader likely accepted the file

Common signs:

- `firmware.bin` is gone
- `firmware.bin` is renamed
- a new file appears with a processed name

If `firmware.bin` is still present and unchanged, the update likely did not run.

## If flashing still does not appear to work

The likely next suspects are:

- wrong bootloader filename expectation
- wrong flash offset assumption in the build
- wrong board LED pin assumption, making a successful flash look invisible
- bootloader expecting a different image layout

In that case, the next best test is not more guessing with the SD card.
The next best test is to add a serial protocol verifier so we can ask the board directly whether it is running our firmware.

## Practical recommendation

For this project, keep one small microSD card or one small FAT32 partition dedicated only to firmware updates.
That keeps the flashing workflow repeatable and avoids the Windows formatting problem each time.
