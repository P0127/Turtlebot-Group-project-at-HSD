## Turtle Bot – Take Control
### Webbasierte Mensch-Roboter-Interaktion für den TurtleBot

### Projektübersicht
Die Weboberfläche des Projekts „Turtle Bot – Take Control“ bildet die Schnittstelle zwischen Mensch und Roboter. Im Rahmen des Projekts wurde eine Webseite zur Steuerung des Roboters entwickelt. Über diese Oberfläche können Bewegungsbefehle wie Vorwärts- und Rückwärtsfahren, Drehen sowie Stoppen ausgeführt werden.

Darüber hinaus ermöglicht der „Turtle Chat“ die Ausführung von Sprach- und Textbefehlen. Zusätzlich wurde die Funktion „Turtle, Take a Photo!“ integriert, mit der der Roboter über seine eingebaute Kamera Bilder seiner Umgebung aufnehmen und unmittelbar an die Weboberfläche übertragen kann.
Die Anwendung kommuniziert mit einem Backend, das die empfangenen Steuerbefehle in ROS2-Kommandos übersetzt und ausführt.

## Architekturüberblick
+ Frontend
+ Vue.js 3
+ Quasar Framework
+ Pinia (State Management)
+ REST API Kommunikation
+ WebSocket-Verbindung für Echtzeit-Sprachinteraktion

## Schritt 1: Repo beitreten
cd Desktop/take-control/web-ui/quasar-project


## Schritt 2: Entwicklungsserver starten 

npx quasar dev


## Aktueller Systemstatus

## Funktionierende Komponenten

+ Bewegungssteuerung
+ Vorwärts-, Rückwärtsfahren, Drehen und Stoppen über Buttons und Geschwindigkeits-Slider 
+ Dock / Undock
+ Steuerung der Ladefunktion über REST-Endpunkte.
+ Statuspanel (Live-Status)
+ Verbindungsstatus (Verbunden / Nicht verbunden)
+ Akkustand mit Farbindikator (rot, orange, grün)
+ Polling über REST-API (alle 3 Sekunden)
+ Turtle Chat (Text- & Sprachinteraktion) 
+ Textbefehle über Chat-Oberfläche
+ Sprachbefehle via WebSocket
+ Echtzeit-Intent-Erkennung im Backend
+ Chat-Verlauf als Markdown exportierbar („Bericht erzeugen“)
+ Foto-Funktion – „Turtle, take a photo!“
+ Aufnahme über integrierte Kamera
+ REST-Request an Backend
+ Rückgabe als Base64-PNG
+ Anzeige im Frontend
+ Download als PNG möglich
+ Frontend–Backend-Kommunikation
+ REST für Status, Steuerung und Foto
+ WebSockets für Echtzeit-Sprach- und Chat-Interaktion
+ Backend (FastAPI + ROS 2) läuft stabil im Docker-Container

## Vermenschlichung der Interaktion mit dem Roboter

### Was ist Turtle Chat?
Turtle Chat ist ein Beispiel für ein interaktives System, das Kommunikation mit einem Roboter simuliert, die Befehle annimmt und auf Fragen reagiert.

**Wie Vermenschlichung hier auftritt:**
+ Nutzer sprechen mit der Turtle in natürlicher Sprache, statt über technische Befehle.
+ Die Turtle „antwortet“ mit Bewegungen und Text (Ich, Turtle Bot, bin bereit.; Ich, Turtle Bot, führe das folgende Intent aus…), die menschliche Reaktionen imitieren.
+ Per Chat und Interaktion entsteht der Eindruck eines „Gesprächspartners“.


### Sprachsteuerung - Turtle Chat erstellt 
### Der funktioniert folgenderweise: 
+ Der Frontend-Chat ist an den speech-store angebunden, in dem alle Nachrichten als Objekte {id, sender, text} gespeichert werden.
+ Die initiale Nachricht „Ich, Turtle Bot, bin bereit.“ wird beim Start im Store gespeichert und im Chat angezeigt.
+ Wenn der User eine Nachricht eingibt, wird diese zuerst im Store als sender: 'user' gespeichert.
+ Gleichzeitig wird die User-Nachricht über den WebSocket an das Backend gesendet.
+ Das Backend empfängt die Nachricht und führt Speech-Interpretation (Vosk) und Intent-Erkennung durch.
+ Vom Backend erkannte gesprochene Texte werden als JSON mit type: 'speech' zurück an den Store geschickt.
+ Diese speech-Nachrichten werden im Store als sender: 'user' gespeichert, sodass sie im Chat als „Ich“ erscheinen.
Vom Backend erkannte Intents werden als JSON mit type: 'intent' zurückgesendet.
+ Diese intent-Nachrichten werden im Store als sender: 'robot' gespeichert, mit Text "Ich, Turtle Bot, führe das folgende Intent aus: INTENTNAME".
+ Das Frontend reagiert auf Store-Updates, zeigt alle Nachrichten chronologisch im Chat an und scrollt automatisch nach unten.
+ Alle Nachrichten bleiben im Store, sind JSON-kompatibel, können exportiert oder für Backend-Persistenz weiterverwendet werden.


## Setup - Install the dependencies

1. (macOS): Homebrew installieren 

Im Terminal eingeben: 
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. Für das Projekt sollte man Node.js installieren: 

Node.js installieren:
```bash
brew install node
```

Version prüfen:
```bash
node -v
```

3. Quasar CLI global installieren:
```bash
npm install -g @quasar/cli
```

Installation prüfen:
```bash
quasar -v
```

4. Abhängigkeiten installieren
Mit npm:
```bash
npm install
```

5. Ordner auf dem Desktop erstellen und beitreten: 
```bash
cd Desktop/ordnername 
```

6. Repository klonen:
```bash
git clone https://github.com/username/turtlebot-communicator.git
```

7. Entwicklungsserver starten 

```bash
npx quasar dev
```

Jetzt sollte die Webseite im Browser automatisch sich öffnen. 
Die Anwendung läuft standardmäßig unter: http://localhost:9000

Damit wurde nur das Frontend gestartet, Backend nicht. Die korrekte 
Anleitung für den Start des Backend finden Sie bei der Backend Repository 
unter 

## Features im Detail

### Frontend-Anbindung
Im Frontend existiert ein Pinia Store (robot-store.js), der die REST-API nutzt.
Aufgaben des Stores:
+ Aufruf der REST-Endpunkte via axios oder fetch
+ Bereitstellung von Aktionen wie: moveForward(); turnLeft(); stopRobot(). 
+ Speichern des aktuellen Befehls
+ Abfrage des Backend-Status über getHealth() - Polling


### Statuspanel
+ Verbindungserkennung (Verbunden / Nicht verbunden)
+ Akkustand (numerisch + visuelle Darstellung in Batterieform)
+ Die Farbe der Batterie spiegelt den Stand der Akku des Roboters wieder 
(rot - kein Akku, gelb - problematisch, aber noch geht, grün - Akkuzustand ist in Ordnung)
+ REST-Api GET Request für den Akku an Backend (getHealth) mit dem Polling 
+ Polling-Intervall: 3000 ms (jede 3 Sekunden)
+ Dock/Undock Buttons (POST über REST an das Backend) 

## Turtle steuern
+ Geschwindigkeit über Slider 
+ Bewegungsbefehle via REST (POST übe Rest)
+ Navigation zu Zielkoordinaten "Turtle Mission" - der Nutzer kann die Koordinaten in Ziffern eintippe sowie mit dem Spinner auf- oder abwerten. 

## Turtle Chat
+ Text- und Sprachinteraktion (entippen sowie die Vosk-Sprachinteraktion starten)
+ Nutzer sprechen mit der Turtle in natürlicher Sprache, statt über technische Befehle.
+ Echtzeit-Feedback via WebSockets 
+ Die Turtle „antwortet“ mit Bewegungen und Text (Ich, Turtle Bot, bin bereit.; Ich, Turtle Bot, führe das folgende Intent aus…), die menschliche Reaktionen imitieren.

### Vermenschlichung der Interaktion
Die Anwendung verfolgt bewusst einen anthropomorphen Ansatz:
+ Natürliche Sprache statt technischer Syntax
+ Roboter antwortet in Ich-Form
+ Chat-Struktur simuliert Dialog
+ Bewegungen werden als „Reaktionen“ interpretiert

**Ziel:**
Steigerung der Benutzerfreundlichkeit und intuitiven Interaktion.

### Technischer Ablauf
+ Nachricht wird im Pinia speech-store gespeichert
+ User-Nachricht wird via WebSocket an das Backend gesendet
+ Backend führt aus:
+ Speech-to-Text (Vosk)
+ Intent-Erkennung
+ Backend sendet JSON zurück: type: speech type: intent
+ Store aktualisiert Chat automatisch
+ UI scrollt automatisch nach unten

**Alle Nachrichten:**
+ JSON-kompatibel
+ exportierbar als Markdown („Bericht erzeugen“)
+ für Persistenz geeignet

**Fehlerfall:** 
„Ich könnte das leider nicht verstehen.“

## Foto-Funktion
+ Aufnahme von Umgebungsbildern in Echtzeit von TurtleBot 
+ REST-Request zur Bildaufnahme
+ Base64 PNG Rückgabe
+ Clientseitige Speicherung, Foto-Storage 
+ Download als PNG mit dem Button "Foto herunterladen"

## UI-Interaktionsfluss
+ User klickt Button oder bewegt Slider
+ Store ruft Aktion auf
+ REST-Request wird gesendet
+ Backend verarbeitet
+ Antwort wird gespeichert und angezeigt

## Designprinzipien
+ Material Design
+ ISO 9241 (Selbstbeschreibung, Erwartungskonformität)
+ Panel-basierte modulare Struktur
+ Klare funktionale Segmentierung
+ Responsives Layout

## Erweiterbarkeit
Modulare Architektur durch Trennung von:
+ UI-Komponenten
+ Stores
+ API-Schicht. 

Neue Panels oder Features können ergänzt werden, ohne bestehende Module stark zu verändern.

## Lizenz
Dieses Projekt ist für akademische Zwecke entwickelt worden.
Lizenzierung nach Absprache.

## Authors and acknowledgment
**Erstellt von:**
Anna iefymenko, Karin Purginova. 

## Project status
In Entwicklung – Kernfunktionen sind implementiert und funktionsfähig.
