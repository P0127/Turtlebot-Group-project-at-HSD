<template>
  <q-page class="control-page">

    <div class="panel-grid">

      <!-- STATUS -->
      <q-card class="panel status-panel">
        <q-card-section>
          <div class="panel-header">
            Status
            <q-badge :color="robotStore.health.status === 'ok' ? 'green' : 'red'"
              :label="robotStore.health.status.toUpperCase()" />
          </div>

          <div class="status-row">
  <span>Verbindung</span>
  <span
    :class="isConnected ? 'ok' : 'not-ok'"
  >
    {{ isConnected ? 'Verbunden' : 'Nicht verbunden' }}
  </span>
</div>

<div class="status-row">
  <span>Akku</span>

  <div class="battery-wrapper">
    <q-icon
      :name="batteryIcon"
      :color="batteryColor"
      size="20px"
    />
    <span>
      {{
        batteryLabel
          ? batteryLabel
          : '-'
      }}
    </span>
  </div>
</div>

          <div class="photo-box">
            <img :src="robotImage" alt="Roboter 1" />
          </div>
          <div class="dock-description">
            <p>
              Klicken Sie auf „Undock“, um den Turtle Bot von der Ladestation zu lösen. Er stoppt den Ladevorgang, fährt zurück und ist anschließend bereit, neue Kommandos entgegenzunehmen und mit Ihnen zu interagieren.
            </p>
            <p>
              Mit „Dock“ senden Sie den Roboter zurück zur Ladestation. Dort richtet er sich automatisch aus und beginnt selbstständig mit dem Laden.
           </p>
</div>
          <div class="docking-row">
            <q-btn
    icon="logout"
    label="Undock"
    unelevated
    class="undock-btn"
    @click="() => handleRobotCommand(robotStore.undockRobot)"
  />
  <q-btn
    icon="ev_station"
    label="Dock"
    unelevated
    class="dock-btn"
    @click="() => handleRobotCommand(robotStore.dockRobot)"
  />
</div>

        </q-card-section>
      </q-card>

      <!-- CONTROL -->
      <q-card class="panel">
        <q-card-section>
          <div class="panel-header">Turtle steuern</div>

          <div class="slider-block">
            <label>Vorwärtsgeschwindigkeit</label>
            <q-slider v-model="robotStore.linearSpeed" :min="0" :max="1" :step="0.05" label class="apple-slider"
              @update:model-value="robotStore.setLinearSpeed" />
          </div>

          <div class="slider-block">
            <label>Drehgeschwindigkeit (Links/Rechts)</label>
            <q-slider v-model="robotStore.angularSpeed" :min="-1" :max="1" :step="0.05" label class="apple-slider"
              @update:model-value="robotStore.setAngularSpeed" />
          </div>

          <div class="control-pad">
  <q-btn
    icon="arrow_upward"
    round
    unelevated
    class="move-btn"
    @click="() => handleRobotCommand(robotStore.moveForward)"
  />

  <div class="row-center">
    <q-btn
      icon="arrow_back"
      round
      unelevated
      class="move-btn"
      @click="() => handleRobotCommand(robotStore.turnLeft)"
    />

    <q-btn
      icon="stop"
      round
      unelevated
      class="stop-btn"
      @click="() => handleRobotCommand(robotStore.stopRobot)"
    />

    <q-btn
      icon="arrow_forward"
      round
      unelevated
      class="move-btn"
      @click="() => handleRobotCommand(robotStore.turnRight)"
    />
  </div>

  <q-btn
    icon="arrow_downward"
    round
    unelevated
    disable
    class="move-btn"
    @click="() => handleRobotCommand(robotStore.moveBackward)"
  />
</div>

            <q-card class="panel">
              <q-card-section>
                <div class="panel-header">Turtle Mission - Zielkoordinaten eingeben: </div>

                <div class="row q-col-gutter-sm">
                  <div class="col-6">
                    <q-input
                      v-model.number="posX"
                      label="X (Meter)"
                      type="number"
                      step="1"
                      filled
                      dense
                      class="nav-input"
                />
                  </div>
                  <div class="col-6">
                    <q-input
                      v-model.number="posY"
                      label="Y (Meter)"
                      type="number"
                      step="1"
                      filled
                      dense
                      class="nav-input"
                      />
                  </div>
                </div>

                <q-btn
  icon="near_me"
  label="FAHRE ZU ZIEL"
  unelevated
  class="nav-btn full-width q-mt-md"
  @click="() => handleRobotCommand(() => 
  robotStore.goToCoordinates(posX, posY)
)"
/>
              </q-card-section>
            </q-card>
          </q-card-section>
        </q-card>

    
    <!-- SPRACHSTEUERUNG -->

<q-card class="panel">
  <q-card-section>

    <div class="panel-header">
      Sprachsteuerung - Turtle Chat
      <q-badge
        class="q-ml-sm"
        :color="speechStore.liveSttRunning ? (speechStore.liveSttPhase === 'awake' ? 'orange' : 'green') : 'grey'"
        :label="speechStore.liveSttRunning ? (speechStore.liveSttPhase === 'awake' ? 'Wake Word erkannt' : 'Zuhört') : 'Inaktiv'"
      />
    </div>

    <div class="apple-chat-wrapper">

      <!-- CHAT -->
      <div class="apple-chat-scroll" ref="chatScrollRef">
        <div
          v-for="msg in chatMessages"
          :key="msg.id"
          :class="['apple-chat-bubble', msg.sender]"
        >
          {{ msg.text }}
        </div>
      </div>

 <!-- INPUT -->
<div class="apple-chat-input">
  <q-input
  v-model="chatInput"
  :disable="isSending"
  type="textarea"
  autogrow
  :maxlength="500"
  :max-height="120"
  dense
  borderless
  placeholder="Schreiben Sie eine Nachricht"
  class="apple-chat-textfield"
  @keyup.enter.exact="sendChatMessage"
/>

  <q-btn
    round
    unelevated
    icon="arrow_upward"
    :loading="isSending"
    :disable="isSending"
    class="apple-send-btn"
    @click="sendChatMessage"
  />
</div>

      <!-- BERICHT -->
      <div class="apple-chat-footer">
        <q-btn
        dense
          :icon="speechStore.liveSttRunning ? 'mic_off' : 'mic'"
          :label="speechStore.liveSttRunning ? 'Sprachsteuerung stoppen' : 'Sprachsteuerung starten'"
          unelevated
          class="report-btn"
          :color="speechStore.liveSttRunning ? 'negative' : 'primary'"
          :loading="speechStore.liveSttBusy"
          @click="toggleLiveStt"
        />
        <q-btn
        dense
          icon="description"
          label="Bericht erzeugen"
          unelevated
          class="report-btn"
          @click="exportSpeechMarkdown"
        />
      </div>

    </div>

  </q-card-section>
</q-card>

      <!-- VISUAL -->
      <q-card class="panel">
        <q-card-section>
          <div class="panel-header">Foto machen - Turtle, take a photo!

          </div>

              <div class="photo-description">
                <p>
                  Der Turtle Bot Communicator – unsere moderne, ROS2-basierte Software – 
                  steuert die integrierte Kamera des Turtle Bots und ermöglicht 
                  die Aufnahme von Umgebungsbildern in Echtzeit. Sobald die Aufnahme ausgelöst wird, erfasst der Roboter ein aktuelles Bild seiner Umgebung und überträgt es unmittelbar an das Control Panel.

               </p>

              <p>
                Bitte klicken Sie auf den Button „Foto machen“, um aktuelle Bilddaten 
                der Umgebung zu initiieren, die vom Turtle Bot erfasst und unmittelbar an das Control Panel übertragen werden.
              </p>

              </div>

          <div class="visual-gallery-wrapper">
            <!-- Große Visualisierung -->

            <div class="visual-box large-visual">

<!-- LOADING -->
<div v-if="isPhotoLoading">
  <q-spinner-camera size="50px" color="primary" />
  <div class="q-mt-md text-primary" style="font-weight: 600;">
    Foto wird aufgenommen...
  </div>
</div>

<!-- ERROR -->
<div v-else-if="photoError" class="photo-error-overlay">
  <q-icon name="report_problem" size="48px" color="negative" />
  <div class="error-text">{{ photoError }}</div>
  <q-btn
    flat
    dense
    label="Erneut versuchen"
    color="primary"
    @click="takePhoto"
  />
</div>

<!-- FOTO -->
<div v-else-if="robotStore.photos.length > 0" class="photo-gallery-single">
  <img :src="robotStore.photos[0]" alt="Letztes Roboter Foto" />
</div>

<!-- KEIN FOTO -->
<div v-else style="text-align:center; color: #007aff;">
  Keine Fotos vorhanden
</div>

</div>

            <!-- Scrollbare Galerie rechts -->
            <div class="photo-gallery-scroll">
              <div v-for="(photo, index) in robotStore.photos.slice(0, 4)" :key="index" class="gallery-item">
                <img :src="photo || 'https://via.placeholder.com/100?text=Foto'" />
              </div>
              <div v-for="n in 4 - robotStore.photos.length" :key="'placeholder-' + n" class="gallery-item">
                <img src="https://via.placeholder.com/100?text=Foto" />
              </div>
            </div>
          </div>


          <!-- Buttons unter der Visualisierung -->
          <div style="margin-top: 12px; display: flex; gap: 12px;">
            <q-btn icon="photo_camera" label="FOTO MACHEN" unelevated class="voice-btn" @click="takePhoto" />
            <q-btn icon="download" label="FOTO HERUNTERLADEN" unelevated class="voice-btn" color="secondary"
              @click="downloadLastPhoto" :disable="robotStore.photos.length === 0" />
          </div>
        </q-card-section>
      </q-card>

    </div> <!-- panel-grid -->

      <!-- FOOTER -->
      <footer class="apple-footer">
  <div class="footer-left">
    <span class="footer-text">
      Hochschule Düsseldorf | Turtle Bot - Take Control 
    </span>

    <a
      class="footer-link"
      href="https://www.turtlebot.com"
      target="_blank"
      rel="noopener noreferrer"
    >
      Über Turtle
    </a>
  </div>

  <div class="footer-logo">
    <img src="src/assets/roboter2.png" alt="Turtle Bot Logo" />
  </div>
</footer>
    <!-- FOOTER ENDE -->

  </q-page>
</template>


<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { useRobotStore } from 'src/stores/robot-store'
import { useSpeechStore } from 'src/stores/speech-store'
import robot1 from 'src/assets/roboter1.png'
import { useQuasar } from 'quasar'

const $q = useQuasar()
const robotStore = useRobotStore()
const speechStore = useSpeechStore()

const robotImage = robot1

const isSending = ref(false)

// ============================
// CHAT STATE (aus Backend / Speech Store)
// ============================
const chatMessages = computed(() => speechStore.messages)

const chatInput = ref('')
const chatScrollRef = ref(null)

const isConnected = computed(() => {
  return robotStore.health.status === 'ok'
})


// ============================
// VERBINDUNGS-STATUS - CHAT
// ============================

let lastConnectionState = null
let initialMessageSent = false

watch(
  () => robotStore.health.status,
  (newStatus) => {

    if (newStatus === 'unknown') return

    const isNowConnected = newStatus === 'ok'

    // 🔥 Nur EINE Initialnachricht erlauben
    if (!initialMessageSent) {
      initialMessageSent = true
      lastConnectionState = isNowConnected

      speechStore.messages = [
        {
          id: Date.now(),
          sender: 'robot',
          text: isNowConnected
            ? 'Ich, Turtle Bot, bin bereit.'
            : 'Ich, Turtle Bot, warte auf die Verbindung.'
        }
      ]

      return
    }

    // Danach nur bei echter Änderung
    if (lastConnectionState === isNowConnected) return

    lastConnectionState = isNowConnected

    speechStore.messages.push({
      id: Date.now(),
      sender: 'robot',
      text: isNowConnected
        ? 'Ich, Turtle Bot, bin bereit.'
        : 'Ich, Turtle Bot, warte auf die Verbindung.'
    })
  }
)

const batteryLevel = computed(() => robotStore.health.battery)
const batteryLabel = computed(() => {
  if (batteryLevel.value === null || batteryLevel.value === undefined) return null
  const n = Number(batteryLevel.value)
  if (!Number.isFinite(n)) return null
  return `${n.toFixed(2)}%`
})

const batteryIcon = computed(() => {
  if (batteryLevel.value === null) return 'battery_unknown'
  if (batteryLevel.value > 80) return 'battery_full'
  if (batteryLevel.value > 50) return 'battery_5_bar'
  if (batteryLevel.value > 30) return 'battery_3_bar'
  if (batteryLevel.value > 10) return 'battery_2_bar'
  return 'battery_alert'
})

const batteryColor = computed(() => {
  if (batteryLevel.value === null) return 'grey'
  if (batteryLevel.value > 30) return 'green'
  if (batteryLevel.value > 15) return 'orange'
  return 'red'
})

// ============================
// SEND TEXT (Frontend → Backend)
// ============================

async function sendChatMessage () {
  const text = chatInput.value.trim()
  if (!text || isSending.value) return

  // SOFORT leeren
  chatInput.value = ''

  isSending.value = true

  try {
    await speechStore.sendUserText(text)
  } catch (error) {
    console.error("Chat error:", error)
  } finally {
    isSending.value = false
  }
}


// ============================
// AUTO SCROLL
// ============================

watch(chatMessages, async () => {
  await nextTick()
  if (chatScrollRef.value) {
    chatScrollRef.value.scrollTo({
      top: chatScrollRef.value.scrollHeight,
      behavior: 'smooth'
    })
  }
})

function exportSpeechMarkdown () {
  if (!chatMessages.value.length) return

  const header = `# Sprach- & Chatprotokoll – Turtle Bot

**Datum:** ${new Date().toLocaleString()}

---

`

  const body = chatMessages.value
    .map(msg => {
      const label = msg.sender === 'user' ? 'Ich' : 'Turtle Bot'
      return `**${label}:** ${msg.text}`
    })
    .join('\n\n')

  const markdown = header + body

  const blob = new Blob([markdown], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)

  const a = document.createElement('a')
  a.href = url
  a.download = `turtlebot_chat_${Date.now()}.md`
  a.click()

  URL.revokeObjectURL(url)
}

// --------------------
// ROBOT Funktionen
// --------------------

// Polling starten beim Mount
// Verbindung mit speechStore für WebSocket
// speechStore.connect() öffnet einen WebSocket zum Backend
// In User-Text das User-Text über WebSocket an das Backend
onMounted(() => {
  robotStore.startPolling(3000)
  speechStore.connect()
  speechStore.refreshLiveSttStatus()
})

// Polling stoppen beim Unmount
onUnmounted(() => {
  robotStore.stopPolling()
  speechStore.disconnect()
})

//goToCoordinates
const posX = ref(0)
const posY = ref(0)

// Foto aufnehmen & speichern
const photoError = ref('')
const isPhotoLoading = ref(false)

async function takePhoto() {
  photoError.value = ''
  isPhotoLoading.value = true
try{
  await robotStore.takePhoto()
  isPhotoLoading.value = false

  $q.notify({
      type: 'positive',
      message: 'Befehl gesendet',
      timeout: 1500,
      position: 'bottom',
      group: false,
      transitionShow: '', 
      transitionHide: ''
    })
}catch{
  photoError.value = "Fehler beim Aufnehmen des Fotos"
}finally {
    isPhotoLoading.value = false 
  }
}

// Letztes Foto herunterladen
function downloadLastPhoto() {
  if (robotStore.photos.length === 0) return

  const photoBase64 = robotStore.photos[0]
  const mimeMatch = typeof photoBase64 === 'string'
    ? /^data:(image\/[a-zA-Z0-9.+-]+);base64,/.exec(photoBase64)
    : null
  const mime = mimeMatch?.[1] || 'image/png'
  const ext = mime === 'image/jpeg' ? 'jpg' : (mime === 'image/png' ? 'png' : 'img')

  const link = document.createElement('a')
  link.href = photoBase64
  link.download = `roboter_foto_${Date.now()}.${ext}`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

}

async function handleRobotCommand(commandFn) {
  try {
    await commandFn()
    $q.notify({
      type: 'positive',
      message: 'Befehl gesendet',
      timeout: 1000,
      position: 'bottom',
      group: false,
      transitionShow: '', 
      transitionHide: ''  
    })

    // Test-Fehler erzwingen
    //throw new Error("Test Fehler")

  } catch (error) {
  console.log("CATCH:", error)

  $q.notify({
  type: 'negative',
  message: 'Backend nicht erreichbar',
  icon: 'error',
  timeout: 5000,
  position: 'top-right',
  actions: [
    { label: 'Erneut versuchen', color: 'white', handler: () => commandFn() }
  ]
})
}
}

async function toggleLiveStt () {
  try {
    if (speechStore.liveSttRunning) {
      await speechStore.stopLiveStt()
      $q.notify({ type: 'warning', message: 'Sprachsteuerung wird gestoppt', timeout: 1200 })
    } else {
      await speechStore.startLiveStt()
      $q.notify({ type: 'positive', message: 'Sprachsteuerung gestartet', timeout: 1200 })
    }
    await speechStore.refreshLiveSttStatus()
  } catch (error) {
    console.error('toggleLiveStt error:', error)
    $q.notify({ type: 'negative', message: 'Sprachsteuerung konnte nicht geändert werden', timeout: 2500 })
  }
}

// This makes the function visible to the browser console
//SPAM Test
/*// Chaos Script: Attempt to spam the backend 50 times
let count = 0;
const spamInterval = setInterval(() => {
  // We use the window hook we created
  window.chatInput.value = 'links'; 
  window.sendChatMessage(); 
  
  count++;
  if (count >= 50) {
    clearInterval(spamInterval);
    console.log("Spam test complete! Check your terminal: it should only show 1 or 2 executions.");
  }
}, 50); 

onMounted(() => {
  window.robotStore = robotStore;
  window.sendChatMessage = sendChatMessage;
  window.chatInput = chatInput;
});*/






</script>
