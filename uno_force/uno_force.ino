// uno_force.ino
// Read a CALT DYLY-103 (S-type, 2 mV/V, 5 kg) load cell through an HX711 24-bit
// ADC module and stream the readings over USB serial. The Python side just opens
// the COM port and parses one row per line (same pattern as the QT Py + MLX90393
// stream on the other USB port).
//
// Wiring (must match these pins):
//   HX711 VCC -> Arduino 3.3V        (5V also OK; gives slightly better SNR)
//   HX711 GND -> Arduino GND
//   HX711 DT  -> Arduino digital pin D3
//   HX711 SCK -> Arduino digital pin D2
//
// Library: install "HX711 Arduino Library" by Bogdan Necula via
// Arduino IDE -> Tools -> Manage Libraries... -> search "HX711".
//
// Serial output:
//   On boot:
//     # UNO_force ready: HX711 DT=D3 SCK=D2 baud=115200
//     t_ms,raw,scaled_N
//   Then one CSV row per sample, ~20 Hz:
//     12345,8932100,0.0000
//   `raw`       = 24-bit signed reading straight from HX711 (no offset, no scale)
//   `scaled_N`  = (raw - TARE_OFFSET) / CALIBRATION_FACTOR  in Newtons.
//                 Both values are 0 / 1 until the calibration script writes the
//                 real numbers back here. Use `raw` for calibration, `scaled_N`
//                 for everyday use after calibration.

#include "HX711.h"

const int HX711_DT  = 3;
const int HX711_SCK = 2;

// ---- Calibration (rewrite these two lines after running force_calibration.py)
const long  TARE_OFFSET        = 77955;       // raw reading at zero force (no load)
const float CALIBRATION_FACTOR = 89508.9179;  // (raw - TARE_OFFSET) per Newton

// 20 Hz output. HX711's default sample rate is 10 SPS; lower-than-period reads
// are silently skipped via is_ready(), so it is safe to ask faster than 10 Hz.
const unsigned long SAMPLE_PERIOD_MS = 50;

HX711 scale;

void setup() {
  Serial.begin(115200);
  while (!Serial) { /* wait for USB CDC */ }

  scale.begin(HX711_DT, HX711_SCK);

  // Wait for the HX711 to report ready, with a visible timeout so a bad wire
  // does not silently hang the board.
  unsigned long t0 = millis();
  while (!scale.is_ready()) {
    if (millis() - t0 > 2000) {
      Serial.println("# ERROR: HX711 not responding. Check DT=D3, SCK=D2, "
                     "VCC=3.3V, GND wires.");
      t0 = millis();   // re-arm and keep complaining every 2 s
    }
    delay(10);
  }

  Serial.print("# UNO_force ready: HX711 DT=D");
  Serial.print(HX711_DT);
  Serial.print(" SCK=D");
  Serial.print(HX711_SCK);
  Serial.println(" baud=115200");
  Serial.println("t_ms,raw,scaled_N");
}

void loop() {
  static unsigned long last_ms = 0;
  unsigned long now = millis();
  if (now - last_ms < SAMPLE_PERIOD_MS) return;

  if (!scale.is_ready()) return;        // HX711 still sampling, try next loop

  long raw = scale.read();
  float scaled_N = (raw - TARE_OFFSET) / CALIBRATION_FACTOR;
  last_ms = now;

  Serial.print(now);
  Serial.print(",");
  Serial.print(raw);
  Serial.print(",");
  Serial.println(scaled_N, 4);
}
