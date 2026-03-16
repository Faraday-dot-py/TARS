/*
 * Example custom hook for a Marlin-based bring-up image.
 *
 * This is not wired into upstream yet. It exists to show the kind of tiny runtime
 * customization we want after selecting the exact Marlin version and hook point.
 */

#include "MarlinCore.h"
#include "gcode/queue.h"

static void tars_emit_banner_once() {
  SERIAL_ECHOLNPGM("TARS_MARLIN_BANNER GD32F303RET6");
}

/*
 * Candidate integration points to evaluate in the chosen Marlin tree:
 * - setup()
 * - a board-init completion path
 * - an early serial-ready point in MarlinCore
 */
