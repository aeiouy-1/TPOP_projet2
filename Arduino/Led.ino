const int PIN_LED = 2;       // Broche où est connectée la LED
const int INTENSITE = 255;   // Luminosité (de 0 à 255)

void setup() {
  pinMode(PIN_LED, OUTPUT);
  // Allume la LED en continu dès le démarrage
  analogWrite(PIN_LED, INTENSITE); 
}

void loop() {
  // La boucle est vide car l'état de la LED ne change pas.
  // Le signal analogWrite (PWM) est maintenu automatiquement par le matériel.
}