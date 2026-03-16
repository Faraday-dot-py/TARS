# Windows Detection of TARS UART Scan Firmware

This note explains how to detect the current minimal custom image from Windows.

## What the current image does

If the board is running this image, it will:

- configure several likely UART peripheral and pin combinations
- continuously print `TARS_UART_SCAN GD32F303RET6`
- do nothing else

## Test baud

Test serial at `115200` for this image.

## Listen for the banner

```powershell
$port = New-Object System.IO.Ports.SerialPort COM18,115200,None,8,one
$port.ReadTimeout = 3000
$port.Open()
try {
    1..20 | ForEach-Object {
        try { $line = $port.ReadLine(); Write-Host $line } catch {}
    }
}
finally {
    $port.Close()
}
```

Success indicator:

```text
TARS_UART_SCAN GD32F303RET6
```

If nothing appears, the remaining issue is very likely the exact UART clocking or board-specific console routing rather than the flash/update path.
