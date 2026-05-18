// src/apis/controlApi.js
import axios from 'axios'

export class ControlApi {
  constructor() {
    this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
    
    this.axiosInstance = axios.create({
      baseURL: this.baseURL,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  // Command senden
  async sendCommand(command) {
    const response = await this.axiosInstance.post('/api/v1/control/command', { 
      command: command 
    })
    return response.data
  }

  // Bewegung mit Geschwindigkeit
  async moveWithVelocity(direction, duration = 1.0) {
    const command = `${direction} ${duration}`
    const response = await this.axiosInstance.post('/api/v1/control/command', { 
      command: command 
    })
    return response.data
  }

  // Stop-Command
  /*async stop() {
    const response = await this.axiosInstance.post('/api/v1/control/command', { 
      command: 'stop' })
    return response.data
  }*/

  async stop() {
    const response = await this.axiosInstance.post('/api/v1/control/stop', { 
      command: 'stop' })
    return response.data
  }

  // Health abrufen
  async getHealth() {
    const response = await this.axiosInstance.get('/api/v1/control/health')
    return response.data
  }

  // Foto aufnehmen
  async takePhoto() {
    const response = await this.axiosInstance.get('/api/v1/control/photo')
    return response.data
  }

  // STT: text -> intent -> execute
  async executeSttText(text) {
    const response = await this.axiosInstance.post('/api/v1/stt/execute', { text })
    return response.data
  }

  async getSttLiveStatus() {
    const response = await this.axiosInstance.get('/api/v1/stt/live/status')
    return response.data
  }

  async startSttLive(payload = {}) {
    const response = await this.axiosInstance.post('/api/v1/stt/live/start', payload)
    return response.data
  }

  async stopSttLive() {
    const response = await this.axiosInstance.post('/api/v1/stt/live/stop')
    return response.data
  }

  // TTS: speak a text (robot speaker)
  async sayText(text, lang = 'de-DE') {
    const response = await this.axiosInstance.post('/api/v1/tts/say', { text, lang })
    return response.data
  }

  // Navigation zu Koordinaten
  async navigateTo(x, y, yaw = 0.0) {
    const response = await this.axiosInstance.post('/api/v1/control/navigate', {
      x: parseFloat(x),
      y: parseFloat(y),
      yaw_deg: parseFloat(yaw)
    })
    return response.data
  }

  // Docking-Status abrufen
  async getDockStatus() {
    const response = await this.axiosInstance.get('/api/v1/control/dock_status')
    return response.data
  }
}
