# Firmware Reference Scaffold

This directory is a host-authored reference for the future per-leg embedded implementation.
It is not validated on real hardware in this repo session.
It should be treated as a behavioral contract and state-machine reference, not as deployable firmware.

## Purpose

The host-side bridge now exists and can open the board serial port.
What does not exist yet is a matching embedded implementation of the framed serial protocol.
This directory makes that embedded contract concrete enough to implement later on the actual board.

## Files

- `protocol.h`: compact C-friendly protocol constants and payload layouts
- `reference_firmware.py`: executable reference state machine for enable, command, watchdog, and telemetry semantics

## Intended embedded responsibilities

- accept framed serial commands from the Jetson
- reject malformed frames with CRC or length errors
- require explicit enable before active outputs
- enter safe-stop on timeout or explicit safe-stop request
- track the last applied host command sequence
- package telemetry back to the host

## Not validated yet

- actual MCU pin mapping
- actual timer allocation for two steppers and one servo
- actual IMU bus implementation
- actual board fault detection wiring
- actual firmware transport timing on the Ender 3 v4.2.2 board

## Safe defaults

Until real firmware exists, assume all board-side defaults should be fail-safe:

- outputs disabled at boot
- watchdog armed by default once the transport starts
- malformed traffic ignored and logged in coarse counters only
- safe-stop preferred over holding stale outputs
