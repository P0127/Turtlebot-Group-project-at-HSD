import { defineStore } from 'pinia'
import { ControlApi } from 'src/apis/controlApi.js'

export const useRobotStore = defineStore('robot', {
  state: () => ({
    currentCommand: 'stop',

    // Speed-Werte (UI → Backend)
    linearSpeed: 0.5,
    angularSpeed: 0.5,

    health: {
      status: 'unknown',
      battery: null
    },

    pollingInterval: null,
    photos: []
  }),

  actions: {
    /* =========================
       API
    ========================= */
    api() {
      return new ControlApi()
    },

    /* =========================
       BACKEND ABFRAGEN
    ========================= */
    async getHealth() {
      try {
        const response = await this.api().getHealth()
    
        // Nur setzen wenn sich wirklich etwas ändert
        if (this.health.status !== response.status) {
          this.health.status = response.status
        }
    
        if (this.health.battery !== response.battery) {
          this.health.battery = response.battery ?? null
        }
    
        return response
    
      } catch (error) {
        if (this.health.status !== 'error') {
          this.health.status = 'error'
        }
    
        console.error('Health-Check fehlgeschlagen:', error)
        throw error
      }
    },

    async updateFromBackend() {
      await this.getHealth()
    },

    /* =========================
       POLLING
    ========================= */
    startPolling(intervalMs = 3000) {
      if (this.pollingInterval) return
      this.updateFromBackend()
      this.pollingInterval = setInterval(() => {
        this.updateFromBackend()
      }, intervalMs)
    },

    stopPolling() {
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval)
        this.pollingInterval = null
      }
    },

    /* =========================
       BEFEHLE (ZENTRAL)
    ========================= */
    // async sendCommand(command) {
    //  try {
    //    const response = await this.api().sendCommand(command)
    //    this.currentCommand = command
    //   return response
    //  } catch (error) {
    //    console.error(`Befehl ${command} fehlgeschlagen:`, error)
    //    throw error
    //  }
    // },

   // async sendCommand(command) {
    //  try {
     //   const response = await this.api().sendCommand(command)
    
        // Wenn Backend logischen Fehler sendet
     //   if (response?.success === false) {
      //    throw new Error(response.message || 'Befehl fehlgeschlagen')
      //  }
    
       // this.currentCommand = command
       // return response
    
      // } catch (error) {
       // console.error(`Befehl ${command} fehlgeschlagen:`, error)
       // throw error
     // }
   // },

   async sendCommand(command) {
    try {
      const response = await this.api().sendCommand(command)
  
      // Axios-Response absichern
      const data = response?.data ?? response
  
      // Falls Backend logischen Fehler sendet
      if (data?.success === false) {
        throw new Error(data.message || 'Befehl fehlgeschlagen')
      }
  
      this.currentCommand = command
      return data
  
    } catch (error) {
  
      // Wenn Backend nicht erreichbar ist (Network Error)
      if (error?.code === 'ERR_NETWORK') {
        throw new Error('Keine Verbindung zum Backend')
      }
  
      
      if (error?.response?.status) {
        throw new Error(
          `Serverfehler (${error.response.status})`
        )
      }
  
      // Fallback
      throw error
    }
  },

    // Bewegungen
    async moveForward() { 
      const duration = 1.0
      const speed = this.linearSpeed
      await this.sendCommand(`forward ${duration} ${speed}`) 
    },
    async moveBackward() { 
      const duration = 1.0
      const speed = this.linearSpeed
      await this.sendCommand(`forward ${duration} ${-Math.abs(speed)}`) 
    },
    async turnLeft() { 
      const duration = 1.0
      const speed = Math.abs(this.angularSpeed)
      await this.sendCommand(`left ${duration} ${speed}`) 
    },
    async turnRight() { 
      const duration = 1.0
      const speed = Math.abs(this.angularSpeed)
      await this.sendCommand(`right ${duration} ${speed}`) 
    },

    async stopRobot() {
      try {
        const response = await this.api().stop()
        this.currentCommand = 'stop'
        return response
      } catch (error) {
        console.error('Stop fehlgeschlagen:', error)
        throw error
      }
    },

    async goToCoordinates(x, y) {
      try {
    
        const response = await this.api().navigateTo(x, y, 0.0)
    
        return response
    
      } catch (error) {
        console.error(`Navigation zu X=${x}, Y=${y} fehlgeschlagen:`, error)
        throw error
      }
    },
  
    

    /* =========================
       FOTO
    ========================= */
    async takePhoto() {
      try {
        const response = await this.api().takePhoto()
        if (response.photo) {
          this.photos.unshift(response.photo)
          return response.photo
        }
      } catch (error) {
        console.error('Foto aufnehmen fehlgeschlagen:', error)
        throw error
      }
    },

    async ensureDockingAvailable() {
      const status = await this.api().getDockStatus()
      if (!status?.available) {
        const reason = status?.reason || 'Docking ist nicht verfügbar'
        throw new Error(reason)
      }
      return status
    },

    /* =========================
       DOCKING
    ========================= */
    async dockRobot() {
      try {
        await this.ensureDockingAvailable()
        const response = await this.sendCommand('dock')
        this.currentCommand = 'docking'
        return response
      } catch (error) {
        console.error('Docking fehlgeschlagen:', error)
        throw error
      }
    },

    async undockRobot() {
      try {
        await this.ensureDockingAvailable()
        const response = await this.sendCommand('undock')
        this.currentCommand = 'undocking'
        return response
      } catch (error) {
        console.error('Undocking fehlgeschlagen:', error)
        throw error
      }
    },

    /* =========================
       UI STATE 
    ========================= */
    setLinearSpeed(newSpeed) {
      this.linearSpeed = newSpeed
    },

    setAngularSpeed(newSpeed) {
      this.angularSpeed = newSpeed
    }
  }
})