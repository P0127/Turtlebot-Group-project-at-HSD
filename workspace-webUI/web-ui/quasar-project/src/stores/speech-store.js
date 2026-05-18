import { defineStore } from 'pinia'
import { ControlApi } from 'src/apis/controlApi.js'

let socket = null
let livePoll = null

export const useSpeechStore = defineStore('speech', {
  state: () => ({
    messages: [
      {
        id: 1,
        sender: 'robot',
        text: 'Ich, Turtle Bot, bin bereit.'
      }
    ],
    liveSttRunning: false,
    liveSttBusy: false,
    liveSttError: null,
    liveSttPhase: 'idle',
    lastLiveEventSeq: 0
  }),

  actions: {
    api () {
      return new ControlApi()
    },

    connect () {
      if (socket) return
      socket = null

      this.refreshLiveSttStatus()
      if (!livePoll) {
        livePoll = setInterval(() => {
          this.refreshLiveSttStatus()
        }, 1200)
      }
    },

    disconnect () {
      if (livePoll) {
        clearInterval(livePoll)
        livePoll = null
      }
    },

    async refreshLiveSttStatus () {
      try {
        const res = await this.api().getSttLiveStatus()
        this.liveSttRunning = !!res?.running
        this.liveSttError = res?.last_error || null
        this.liveSttPhase = res?.phase || 'idle'

        const seq = Number(res?.last_event_seq || 0)
        if (seq > this.lastLiveEventSeq && res?.last_event_text) {
          this.lastLiveEventSeq = seq
          this.messages.push({
            id: Date.now(),
            sender: 'robot',
            text: String(res.last_event_text)
          })
        }
        return res
      } catch (err) {
        console.error('STT status failed:', err)
        return null
      }
    },

    async startLiveStt () {
      this.liveSttBusy = true
      try {
        const res = await this.api().startSttLive({})
        this.liveSttRunning = !!res?.running
        this.liveSttError = res?.last_error || null
        this.liveSttPhase = res?.phase || 'idle'
        return res
      } finally {
        this.liveSttBusy = false
      }
    },

    async stopLiveStt () {
      this.liveSttBusy = true
      try {
        const res = await this.api().stopSttLive()
        this.liveSttRunning = !!res?.running
        this.liveSttError = res?.last_error || null
        this.liveSttPhase = res?.phase || 'idle'
        return res
      } finally {
        this.liveSttBusy = false
      }
    },

    async sendUserText (text) {
      // User-Nachricht sofort anzeigen
      this.messages.push({
        id: Date.now(),
        sender: 'user',
        text
      })

      try {
        const res = await this.api().executeSttText(text)

        /* =========================
           INTENT-SPEZIALFALL
        ========================= */
        if (res?.intent === 'get_battery_status') {

          const battery =
            res?.battery ??
            res?.data?.battery ??
            null

          const message =
            battery !== null
              ? `Der aktuelle Batteriestatus des Turtle Bots beträgt ${battery} Prozent.`
              : 'Der Batteriestatus konnte nicht ermittelt werden.'

          this.messages.push({
            id: Date.now(),
            sender: 'robot',
            text: message
          })

          return res
        }

        /* =========================
           STANDARD-LOGIK (unverändert)
        ========================= */
        const reply =
          res?.reply ||
          (res?.intent ? `Ich führe aus: ${res.intent}` : 'Verstanden.')

        this.messages.push({
          id: Date.now(),
          sender: 'robot',
          text: reply
        })

        return res

      } catch (err) {
        console.error('STT execute failed:', err)

        this.messages.push({
          id: Date.now(),
          sender: 'robot',
          text: 'Ich konnte das leider nicht verstehen.'
        })

        throw err
      }
    }
  }
})
