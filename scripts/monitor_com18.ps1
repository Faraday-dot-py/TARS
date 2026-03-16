param(
    [string]$PortName = 'COM18',
    [int]$BaudRate = 115200,
    [int]$ReadTimeoutMs = 500,
    [int]$ReconnectDelayMs = 1000
)

while ($true) {
    $port = $null
    try {
        $port = New-Object System.IO.Ports.SerialPort $PortName,$BaudRate,None,8,one
        $port.ReadTimeout = $ReadTimeoutMs
        $port.DtrEnable = $false
        $port.RtsEnable = $false
        $port.Open()
        Write-Host "Connected to $PortName at $BaudRate baud"

        while ($port.IsOpen) {
            try {
                $line = $port.ReadLine()
                if ($line -ne $null) {
                    Write-Host $line
                }
            }
            catch [System.TimeoutException] {
            }
        }
    }
    catch {
        Write-Host "Waiting for $PortName..."
    }
    finally {
        if ($port -ne $null) {
            try {
                if ($port.IsOpen) {
                    $port.Close()
                }
            }
            catch {
            }
            $port.Dispose()
        }
    }

    Start-Sleep -Milliseconds $ReconnectDelayMs
}
